import csv
import yaml
import os

# Read configuration file
def read_config():
    with open('extract_setup.yaml', 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

# Main function
def main():
    # Read configuration
    config = read_config()
    database_file = config['database_file']
    extract_fuel = config['extract_fuel']
    
    # Get database file name (without path and extension)
    db_filename = os.path.splitext(os.path.basename(database_file))[0]
    
    # Construct output file name
    output_file = f"{db_filename}_{extract_fuel}.csv"
    
    # Extract data
    extracted_rows = []
    
    with open(database_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        
        # Read header
        header = next(reader)
        extracted_rows.append(header)
        
        # Read data rows, extract data for specified fuel
        for row in reader:
            if row[0] == extract_fuel:
                extracted_rows.append(row)
    
    # Save to new file
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerows(extracted_rows)
    
    print(f"Data extraction completed!")
    print(f"Extracted fuel: {extract_fuel}")
    print(f"Output file: {output_file}")
    print(f"Total extracted {len(extracted_rows) - 1} data records")

if __name__ == "__main__":
    main()