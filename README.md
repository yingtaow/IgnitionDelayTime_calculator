# Ignition Delay Time (IDT) Simulation Tool

A Python-based tool for generating ignition delay time datasets using Cantera chemical kinetics simulation. This tool supports parallel computation and random sampling of combustion parameters for various fuel mixtures.

## Features

- **Multi-fuel Support**: Simulate ignition delay times for various fuels including nitromethane (CH3NO2), TMEDA, and other hydrocarbons
- **Parallel Computation**: Utilizes multiprocessing for efficient batch processing of simulations
- **Random Parameter Sampling**: Generate datasets with randomized equivalence ratios, temperatures, pressures, and dilution ratios
- **Three-IDT Detection**: Identifies total ignition delay (IDT_total), first-stage ignition delay (IDT_1st), and weak ignition delay (WeakIDT)
- **Flexible Configuration**: YAML-based configuration for easy parameter adjustment
- **Data Management**: Tools for extracting and merging simulation datasets

## Installation

### Prerequisites

- Python 3.7 or higher
- Cantera 3.0.0 or higher

### Install Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install cantera numpy pyyaml
```

## Usage

### 1. Configure Simulation Parameters

Edit `input_params.yaml` to set your simulation parameters:

```yaml
# Fuel mixture configuration
fuel_mixtures:
  - CH3NO2: 1.0

# Temperature range (K)
T_range: [700, 1000]

# Pressure range (Bar)
P_range: [10.0, 10.0]

# Equivalence ratio range
phi_range: [1.0, 1.0]

# Dilution ratio range
dilution_range: [3.76, 3.76]

# Number of samples to generate
n_samples: 20

# Chemical mechanism file
mechanism_file: "CH3NO2.yaml"

# Output file name
output_file: "IgnitionDelay_CH3NO2_F1.csv"
```

### 2. Run IDT Simulation

**Windows:**
```bash
run_IDT_calcu.bat
```

**Linux/Mac:**
```bash
python DataBuilder_paraV8.py
```

The script will:
- Generate random parameter combinations within specified ranges
- Run Cantera simulations in parallel
- Detect IDT_total, IDT_1st, and WeakIDT for each simulation
- Save results to the specified CSV file

### 3. Extract Data for Specific Fuel (Optional)

If your database contains multiple fuels, extract data for a specific fuel:

1. Edit `extract_setup.yaml`:
```yaml
database_file: "./merged_data.csv"
extract_fuel: "CH3NO2"
```

2. Run extraction:
```bash
# Windows
Extract.bat

# Linux/Mac
python extract.py
```

### 4. Merge Multiple CSV Files (Optional)

Combine multiple simulation result files:

```bash
# Windows
Merge.bat

# Linux/Mac
python merge_data.py
```

## Configuration Guide

### input_params.yaml

| Parameter | Description | Example |
|-----------|-------------|---------|
| `fuel_mixtures` | List of fuels and their mole fractions | `- CH3NO2: 1.0` |
| `T_thread` | Minimum temperature rise threshold for WeakIDT detection (K) | `200.0` |
| `min_time_step_ms` | Minimum time step for data saving (ms) | `0.05` |
| `phi_range` | Equivalence ratio range [min, max] | `[0.5, 2.0]` |
| `phi_step` | Equivalence ratio step (optional, for discrete sampling) | `0.1` |
| `T_range` | Temperature range [min, max] (K) | `[700, 1200]` |
| `P_range` | Pressure range [min, max] (Bar) | `[1.0, 20.0]` |
| `dilution_range` | Dilution ratio range [min, max] | `[3.76, 3.76]` |
| `idt_range` | Valid IDT range for filtering [min, max] (ms) | `[0.02, 500.0]` |
| `n_samples` | Number of successful samples to generate | `100` |
| `oxidant` | Oxidizer composition | `"O2:0.21,N2:0.79"` |
| `diluent` | Diluent composition (optional) | `"N2:1.0"` |
| `mechanism_file` | Cantera mechanism file (YAML format) | `"CH3NO2.yaml"` |
| `output_file` | Output CSV file name | `"results.csv"` |

### Chemical Mechanism Files

The tool uses Cantera YAML mechanism files. Example mechanism files included:
- `CH3NO2.yaml` - Nitromethane mechanism
- `TMEDAR56.yaml` - TMEDA mechanism

You can use any Cantera-compatible mechanism file by specifying it in `input_params.yaml`.

## Output Format

The output CSV file contains the following columns:

| Column | Description | Unit |
|--------|-------------|------|
| `fuels` | Fuel name | - |
| `phi` | Equivalence ratio | - |
| `dilution` | Dilution ratio | - |
| `Temperature` | Initial temperature | K |
| `Pressure/bar` | Initial pressure | bar |
| `IDT_total/ms` | Total ignition delay time | ms |
| `IDT_1st/ms` | First-stage ignition delay time | ms |
| `WeakIDT/ms` | Weak ignition delay time | ms |
| `fuel_molarfraction` | Fuel mole fraction in mixture | - |
| `oxidant_molarfraction` | Oxidizer mole fraction in mixture | - |
| `diluent_molarfraction` | Diluent mole fraction in mixture | - |

## IDT Detection Algorithm

The tool implements an optimized IDT detection algorithm:

1. **WeakIDT**: Detected when temperature rise exceeds `T_thread` (default: 200 K)
2. **IDT_total**: Identified as the time of maximum temperature rise rate (global maximum of dT/dt)
3. **IDT_1st**: For two-stage ignition, identified as the highest peak before IDT_total, excluding the main ignition peak

The algorithm uses dynamic window local maxima detection to accurately identify ignition events.

## Project Structure

```
IDT_simu/
├── DataBuilder_paraV8.py    # Main simulation script
├── extract.py               # Data extraction script
├── merge_data.py            # CSV merging script
├── input_params.yaml        # Simulation configuration
├── extract_setup.yaml       # Extraction configuration
├── CH3NO2.yaml              # Nitromethane mechanism
├── TMEDAR56.yaml            # TMEDA mechanism
├── run_IDT_calcu.bat        # Windows batch script for simulation
├── Extract.bat              # Windows batch script for extraction
├── Merge.bat                # Windows batch script for merging
├── requirements.txt         # Python dependencies
└── README.md                # This file
```

## Version History

### Version 8 (Current)
- Added support for discrete parameter sampling with specified step sizes
- Equivalence ratio, pressure, and dilution ratio can now be sampled with custom steps

### Version 7
- Added WeakIDT detection before identifying IDT_total and IDT_1st
- Changed temperature sampling from uniform [Tmin, Tmax] to uniform [1/Tmin, 1/Tmax] for better physical distribution

### Version 6
- Initial release with parallel IDT simulation capabilities

## Troubleshooting

### Memory Issues
If you encounter memory errors:
- Reduce `n_samples` or process in smaller batches
- The script automatically reduces process count when memory errors occur
- Close other memory-intensive applications

### No Valid Samples
If the script terminates with "No valid samples obtained":
- Check that your mechanism file is valid and compatible with Cantera
- Verify parameter ranges are physically reasonable
- Ensure `T_thread` is appropriate for your fuel/conditions
- Check that `idt_range` covers expected ignition delay times

### Cantera Errors
- Ensure Cantera is properly installed: `pip install cantera`
- Verify mechanism file format is correct (YAML format for Cantera 3.0+)
- Check that all species in fuel_mixtures exist in the mechanism

## Citation

If you use this tool in your research, please cite:
A Multi-Stage Inverse Integral Method for Deriving Ignition Delay Correlation from Autoignition Experimental Measurements
Yingtao Wu*, Zhonghao Zhao, Yuxin Fang, Pengzhi Wang, Song Cheng, Chenglong Tang*, Zuohua Huang, Henry Curran
Combustion and Flame
```
IDT Simulation Tool, https://github.com/yingtaow/IDT_simu
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Contact

For questions or support, please open an issue on GitHub.
