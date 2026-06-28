import numpy as np
import cantera as ct
import csv
import yaml
import gc
from multiprocessing import Pool, cpu_count, Lock

# Read input parameter file
def load_input_parameters(file_path='input_params.yaml'):
    with open(file_path, 'r', encoding='utf-8') as file:
        params = yaml.safe_load(file)
    return params

def optimize_idt_identification(time_history, temperature_history):
    """
    Optimize IDT identification algorithm for accurate detection of IDT_total and IDT_1st
    
    Parameters:
    time_history: Time series data
    temperature_history: Temperature series data
    
    Returns:
    Dictionary result containing IDT_total and IDT_1st
    """
    # 2. Calculate first derivative of temperature (temperature rise rate)
    dt = np.diff(time_history)
    dTdt = np.diff(temperature_history) / dt
    
    # 3. Dynamic window local maxima detection algorithm
    def detect_local_maxima(signal, time_diff):
        """Detect local maxima using dynamic window"""
        if len(signal) < 5:
            return []
            
        # Calculate second derivative of signal (used to determine window size)
        d2signal = np.diff(signal) / time_diff[1:] if len(time_diff) > 1 else np.gradient(np.gradient(signal))
        
        # Dynamically adjust window size based on curvature (between 3-7)
        window_sizes = np.clip(5 - np.abs(d2signal[:-1]) // 1000, 3, 7).astype(int)
        
        local_max_indices = []
        
        for i in range(1, len(signal) - 1):
            # Basic condition: current point is greater than adjacent points
            if signal[i] > signal[i-1] and signal[i] > signal[i+1]:
                # Get dynamic window size
                window_size = window_sizes[i] if i < len(window_sizes) else 5
                
                # Left window check
                left_start = max(0, i - window_size)
                left_end = i - 1
                left_increase = all(signal[i] > signal[j] for j in range(left_start, left_end + 1))
                
                # Right window check
                right_start = i + 1
                right_end = min(len(signal) - 1, i + window_size)
                right_decrease = all(signal[i] > signal[j] for j in range(right_start, right_end + 1))
                
                if left_increase and right_decrease:
                    local_max_indices.append(i)
        
        return local_max_indices
    
    # 4. Perform local maxima detection
    max_indices = detect_local_maxima(dTdt, dt)
    
    if not max_indices:
        return {"IDT_total": 0.0, "IDT_1st": 0.0}
    
    # Use all detected local maxima directly (no threshold filtering)
    peak_values = [dTdt[i] for i in max_indices]
    
    # 6. Sort peaks by value in descending order
    sorted_pairs = sorted(zip(peak_values, max_indices), reverse=True, key=lambda x: x[0])
    sorted_values, sorted_indices = zip(*sorted_pairs)
    
    # 7. Determine IDT_total (global maximum point) - use np.argmax to find global maximum index
    global_max_idx = np.argmax(dTdt)  # Use numpy's argmax function to find global maximum index
    idt_total_time = time_history[global_max_idx + 1]  # +1 to compensate for offset caused by diff
    
    # 8. Determine IDT_1st (highest peak before IDT_total, skip points near main ignition peak)
    idt_1st_time = 0.0
    valid_1st_candidates = []
    
    # Iterate through all detected peaks to find IDT_1st candidates that meet criteria
    for val, idx in zip(sorted_values, sorted_indices):
        candidate_time = time_history[idx + 1]
        
        # Skip points near main ignition peak to avoid misidentifying main peak fluctuations as IDT_1st
        if abs(idx - global_max_idx) < 2:
            continue
        
        # Only consider peaks before IDT_total
        if candidate_time < idt_total_time:
            valid_1st_candidates.append((val, idx, candidate_time))
    
    # If valid candidates exist, select the highest one as IDT_1st
    if valid_1st_candidates:
        idt_1st_time = valid_1st_candidates[0][2]  # valid_1st_candidates already sorted by value in descending order
    
    return {
        "IDT_total": idt_total_time * 1000,  # Convert to milliseconds
        "IDT_1st": idt_1st_time * 1000
    }

# Load parameters
input_params = load_input_parameters()

# Get configuration from parameter file
fuel_mixtures_config = input_params['fuel_mixtures']
T_thread = input_params['T_thread']
phi_range = input_params['i_parameters']['phi_range']
phi_step = input_params['i_parameters'].get('phi_step', None)  # Equivalence ratio step (optional)
dilution_range = input_params['i_parameters']['dilution_range']
dilution_step = input_params['i_parameters'].get('dilution_step', None)  # Dilution ratio step (optional)
T_range = input_params['i_parameters']['T_range']
P_range = input_params['i_parameters']['P_range']
P_step = input_params['i_parameters'].get('P_step', None)  # Pressure step (optional)
idt_range = input_params['i_parameters']['idt_range']
n_samples = input_params['n_samples']
# Use get method to safely fetch parameters with default values
oxidant = input_params.get('oxidant', 'O2:0.21,N2:0.79')  # Oxidizer defaults to air
diluent = input_params.get('diluent', None)      # Diluent defaults to None (no dilution)
mechanism_file = input_params['mechanism_file']
output_file = input_params['output_file']

# Process fuel mixture configuration (support list format)
fuel_mixture_list = []
for mixture in fuel_mixtures_config:
    if isinstance(mixture, dict):
        # Process dictionary items in the list
        for fuel_name, fuel_comp in mixture.items():
            fuel_mixture_list.append((fuel_name, {fuel_name: fuel_comp}))


# Helper function: generate random parameters based on range and step (supports discrete and continuous)
def generate_random_param(param_range, param_step):
    """
    Generate random parameters based on range and step
    
    Parameters:
    param_range: Parameter range [min, max]
    param_step: Step size, None indicates continuous distribution
    
    Returns:
    Randomly generated parameter value
    """
    if param_step is None or param_range[0] == param_range[1]:
        # Continuous distribution or fixed value
        return np.random.uniform(param_range[0], param_range[1])
    else:
        # Discrete distribution: generate all possible values based on step, then randomly select
        # Discrete distribution for normal parameters
        # Generate all possible values
        possible_values = np.arange(param_range[0], param_range[1] + param_step, param_step)
        # Randomly select a value
        return np.random.choice(possible_values)

# Function to process a single sample
def process_sample(i):
    # Call gc.collect() at the beginning to clean up potential memory leaks
    gc.collect()
    
    # Randomly select a fuel
    fuel_index = np.random.randint(0, len(fuel_mixture_list))
    fuel_mixture_name, fuel_mixture = fuel_mixture_list[fuel_index]

    # Randomly generate input parameters
    phi = generate_random_param(phi_range, phi_step)
    dilution = generate_random_param(dilution_range, dilution_step)
    T = 1 / np.random.uniform(1/T_range[1], 1/T_range[0])
    P = generate_random_param(P_range, P_step) * 100000  # change bar to pa

    try:
        # Create a Cantera solution object using the specified mechanism
        gas = ct.Solution(mechanism_file)

        # Set fuel mixture composition, considering diluent gas
        # The ratio of diluent to oxygen is dilution
        
        # Parse oxidizer composition, regardless of whether there is diluent
        oxidant_dict = {}
        for comp in oxidant.split(','):
            species, ratio = comp.split(':')
            oxidant_dict[species] = float(ratio)
        
        # Calculate total amount of all oxidizer components
        total_oxidant = sum(oxidant_dict.values())
        
        # Add check for all oxidizer components
        if total_oxidant <= 0:
            print(f"Warning: No oxidant found in the mixture. Skipping sample {i + 1}.")
            return exit(1) # No need for subsequent calculations if there is no oxidizer
        
        if diluent:
            # Create a complete mixture containing oxidizer and diluent
            # Parse diluent composition
            diluent_dict = {}
            for comp in diluent.split(','):
                species, ratio = comp.split(':')
                diluent_dict[species] = float(ratio)
            
            # Calculate oxidizer mixture with diluent
            oxidizer_with_diluent = {}
            
            # Add all oxidizer components
            for species, ratio in oxidant_dict.items():
                oxidizer_with_diluent[species] = ratio
            
            # Add diluent according to dilution ratio
            for species, ratio in diluent_dict.items():
                oxidizer_with_diluent[species] = ratio * dilution * total_oxidant
            
            # Set mixture composition
            gas.set_equivalence_ratio(phi=phi, fuel=fuel_mixture, oxidizer=oxidizer_with_diluent)
        else:
            # When there is no diluent, directly set equivalence ratio
            gas.set_equivalence_ratio(phi=phi, fuel=fuel_mixture, oxidizer=oxidant)

        # Set temperature and pressure
        gas.TP = T, P

        # Calculate mole fractions of each component (get initial composition before CT simulation)
        # Get all species names and mole fractions
        species_names = gas.species_names
        mole_fractions = gas.X
        
        # Calculate total mole fractions of fuel, oxidizer, and diluent
        fuel_molarfraction = 0.0
        oxidant_molarfraction = 0.0
        diluent_molarfraction = 0.0
        
        # Fuel species (based on keys in fuel_mixture dictionary)
        for fuel_species in fuel_mixture:
            if fuel_species in species_names:
                idx = species_names.index(fuel_species)
                fuel_molarfraction += mole_fractions[idx]
        
        # Calculate oxidizer components (parallel to fuel)
        # Determine calculation method for oxidizer components
        for species in oxidant_dict.keys():
            if species in species_names:
                idx = species_names.index(species)
                oxidant_molarfraction += mole_fractions[idx]
        
        
        # Calculate diluent components (only needed when there is diluent)
        if diluent:
            # Diluent components: species that are neither fuel nor oxidizer
            for idx, species in enumerate(species_names):  # Use idx to avoid conflict with function parameter i
                if species not in fuel_mixture and species not in oxidant_dict:
                    diluent_molarfraction += mole_fractions[idx]

        # Set the reactor network
        R1 = ct.IdealGasMoleReactor(gas)
        sim = ct.ReactorNet([R1])
        sim.preconditioner = ct.AdaptivePreconditioner()

        # Initialize arrays to store data
        time_history = []
        temperature_history = []
        print(f"Sample {i + 1} calculation begin")

        # Get minimum time step from config file
        min_dt_ms = input_params.get('min_time_step_ms', 0.05)  # Default value 0.05ms
        min_dt = min_dt_ms / 1000.0  # Convert to seconds

        # Execute simulation with sparse processing
        while sim.time < idt_range[1] / 1000:
            sim.step()  # Take a time step (Cantera automatically adjusts the step size)

            # Sparse processing: only add data when time difference from last saved point >= min_dt
            if not time_history or (sim.time - time_history[-1] >= min_dt):
                time_history.append(sim.time)
                temperature_history.append(gas.T)

        # Calculate the temperature rise for WeakIDT calculation
        temperature_rise = np.array(temperature_history) - T
        indices = np.where(temperature_rise > T_thread)[0]
        IDT_weak = time_history[indices[0]] * 1000 if len(indices) > 0 else 0.0

        # When IDT_weak > 0, call optimized IDT identification algorithm
        if IDT_weak > 0:
            idt_results = optimize_idt_identification(time_history, temperature_history)
            IDT_total = idt_results["IDT_total"]
            IDT_1st = idt_results["IDT_1st"]
        else:
            IDT_total = 0.0
            IDT_1st = 0.0

        # Display calculation results in real-time (IDT values)
        print(f"Sample {i + 1}: IDT_total = {IDT_total:.2f} ms; IDT_1st = {IDT_1st:.2f} ms; WeakIDT = {IDT_weak:.2f} ms")

        # Check if calculated IDT is within specified range
        if idt_range[0] <= IDT_total <= idt_range[1]:
            # Mole fractions of each component have been calculated before CT simulation

            result = {
                'fuels': fuel_mixture_name,
                'phi': phi,
                'dilution': dilution,
                'Temperature': T,
                'Pressure/bar': P / 100000,
                'IDT_total/ms': IDT_total,
                'IDT_1st/ms': IDT_1st,
                'WeakIDT/ms': IDT_weak,
                'fuel_molarfraction': fuel_molarfraction,
                'oxidant_molarfraction': oxidant_molarfraction,
                'diluent_molarfraction': diluent_molarfraction
            }
            # Clean up large arrays and Cantera objects to reduce memory usage
            # These objects will be automatically cleaned up after function returns, but explicit deletion releases memory earlier
            if 'temperature_history' in locals():
                del temperature_history
            if 'time_history' in locals():
                del time_history
            if 'gas' in locals():
                del gas
            if 'sim' in locals():
                del sim

            return result
        else:
            return None
    except Exception as e:
        # Catch all exceptions that Cantera might throw
        print(f"Error in sample {i + 1}: {str(e)}. Skipping this parameter set.")
        # Ensure objects are cleaned up even in case of exception
        if 'gas' in locals():
            del gas
        if 'sim' in locals():
            del sim
        # Clean up potentially large arrays
        if 'time_history' in locals():
            del time_history
        if 'temperature_history' in locals():
            del temperature_history
        return None



if __name__ == '__main__':
    # Specify the number of parallel processes
    # Reduce process count to minimize memory usage
    num_processes = max(1, min(cpu_count() // 2, 16))  # Use half of cores, max 12 processes
    print(f"Using {num_processes} parallel processes to reduce memory usage")

    # Open the CSV file and write the header
    lock = Lock()
    with open(output_file, 'w', newline='') as csvfile:
        # Update column names to match keys in result dictionary, add composition information
        column_names = ['fuels', 'phi', 'dilution', 'Temperature', 'Pressure/bar', 'IDT_total/ms', 'IDT_1st/ms', 'WeakIDT/ms',
                       'fuel_molarfraction', 'oxidant_molarfraction', 'diluent_molarfraction']
        writer = csv.DictWriter(csvfile, fieldnames=column_names)
        writer.writeheader()

        # Counter to record number of successful samples
        successful_samples = 0
        # For generating infinite sample indices
        sample_index = 0
        # Record total attempts to prevent infinite loop
        total_attempts = 0
        # Set maximum attempt limit
        max_attempts = n_samples * 10  # Assume max 10x the required number of samples
        # Early stopping threshold: terminate if no valid samples in first 100 attempts
        early_stop_threshold = 100

        # Use multiprocessing to parallelize the computation
        with Pool(processes=num_processes) as pool:
            # Continue generating samples until enough valid results collected or max attempts reached
            while successful_samples < n_samples and total_attempts < max_attempts:
                # Remove unnecessary garbage collection calls

                # Generate a batch of new sample indices
                # Reduce batch size to minimize memory pressure
                batch_size = min(25, n_samples - successful_samples)
                batch_indices = range(sample_index, sample_index + batch_size)
                sample_index += batch_size
                total_attempts += batch_size
                print(f"Attempting batch of {batch_size} samples. Total attempts: {total_attempts}/{max_attempts}")

                # Early stopping check: terminate if no valid samples in first 100 attempts
                if total_attempts >= early_stop_threshold and successful_samples == 0:
                    print(f"ERROR: No valid samples obtained in the first {early_stop_threshold} attempts. Terminating program to prevent infinite loop.")
                    csvfile.close()
                    pool.terminate()  # Terminate all processes
                    pool.join()
                    break  # Break loop to avoid infinite loop

                # Process this batch of samples
                try:
                    for result in pool.imap_unordered(process_sample, batch_indices):
                        if result is not None:
                            with lock:
                                writer.writerow(result)
                                csvfile.flush()  # Ensure data is written to the file
                            successful_samples += 1
                            print(f"Successful sample {successful_samples}/{n_samples}")

                            # Exit loop if enough samples collected
                            if successful_samples >= n_samples:
                                break
                except MemoryError:
                    print("Memory Error detected! Reducing process count and continuing...")
                    # Close current process pool
                    pool.terminate()
                    pool.join()

                    # Reduce process count and recreate process pool
                    num_processes = max(1, num_processes // 2)
                    print(f"Reducing to {num_processes} processes due to memory issues")

                    # Recreate process pool
                    pool = Pool(processes=num_processes)

                    # Reprocess current batch
                    continue
                except Exception as e:
                    print(f"Unexpected error: {e}. Continuing with remaining samples...")
                    continue

    # Check if all required samples successfully collected
    if successful_samples >= n_samples:
        print(f"Completed writing {n_samples} successful samples to result csv file")
    else:
        print(f"Warning: Reached maximum number of attempts ({max_attempts}) without collecting {n_samples} successful samples.")
        print(f"Only collected {successful_samples} samples. Please check input parameters or mechanism file.")