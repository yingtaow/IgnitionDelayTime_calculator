import os
import glob
import csv

def merge_csv_files(output_file='merged_data.csv'):
    # Get all CSV files in current directory
    csv_files = glob.glob('*.csv')
    
    if not csv_files:
        print("No CSV files found in current directory.")
        return
    
    # Sort by filename (optional)
    csv_files.sort()
    
    print(f"Found {len(csv_files)} CSV files, ready to merge...")
    print(f"Files to merge: {csv_files}")
    
    with open(output_file, 'w', newline='', encoding='utf-8') as outfile:
        writer = csv.writer(outfile)
        first_file = True
        total_rows = 0
        
        for csv_file in csv_files:
            print(f"Processing file: {csv_file}")
            
            try:
                with open(csv_file, 'r', encoding='utf-8') as infile:
                    reader = csv.reader(infile)
                    rows = list(reader)
                    
                    if not rows:
                        print(f"  File {csv_file} is empty, skipping.")
                        continue
                    
                    if first_file:
                        # Write header and data from first file
                        writer.writerow(rows[0])
                        data_rows = rows[1:]
                        first_file = False
                        header = rows[0]
                    else:
                        # Skip header from subsequent files
                        data_rows = rows[1:]
                        # Check if headers are consistent
                        if rows[0] != header:
                            print(f"  Warning: Header of file {csv_file} is inconsistent with the first file, header skipped.")
                    
                    # Write data rows
                    writer.writerows(data_rows)
                    total_rows += len(data_rows)
                    print(f"  Successfully wrote {len(data_rows)} rows of data.")
                    
            except Exception as e:
                print(f"  Error processing file {csv_file}: {str(e)}")
    
    print(f"\nMerge completed!")
    print(f"Output file: {output_file}")
    print(f"Total merged rows: {total_rows}")

if __name__ == "__main__":
    merge_csv_files()