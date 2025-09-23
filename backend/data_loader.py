
import pandas as pd
from collections import defaultdict
import csv

def load_bom(bom_file_path):
    """
    Loads the Bill of Materials (BOM) from a text file.

    This function is designed to parse a fixed-width BOM report file based on the sample provided.
    It parses parent, component, and quantity from specific positions.

    Args:
        bom_file_path (str): The absolute path to the BOM text file.

    Returns:
        defaultdict: A dictionary mapping parent parts to a list of their components with quantities.
    """
    bom_data = defaultdict(list)
    try:
        with open(bom_file_path, 'r', encoding='latin-1') as f:
            for line in f:
                if len(line) < 85: # Increased sanity check for line length
                    continue

                parent_part = line[0:16].strip()
                component_part = line[16:32].strip()

                # Correctly parse quantity from positions 78-85 (approximate)
                quantity_str = line[78:85].strip()
                if quantity_str:
                    try:
                        quantity = float(quantity_str)
                    except ValueError:
                        quantity = 1.0 # Fallback if parsing fails
                else:
                    quantity = 1.0 # Default if quantity string is empty

                if parent_part and component_part:
                    bom_data[parent_part].append({
                        "component": component_part,
                        "quantity": quantity
                    })
    except FileNotFoundError:
        print(f"Error: BOM file not found at {bom_file_path}")
    except Exception as e:
        import traceback
        print(f"An error occurred while reading the BOM file: {e}")
        traceback.print_exc()

    return bom_data

def load_mrp_data(mrp_file_path):
    """
    Loads Material Requirements Planning (MRP) data from a text file.
    This function is now more robust, dynamically finding column indices from the header.
    """
    mrp_data = {}
    try:
        with open(mrp_file_path, 'r', encoding='latin-1') as f:
            # Read header to find column indices dynamically
            header_line = next(f, None)
            if not header_line:
                return {}
            
            headers = [h.strip() for h in header_line.split('\t')]
            
            try:
                material_col_idx = headers.index('Material')
                issue_location_col_idx = headers.index('Iss. Stor, loc')
                rounding_value_col_idx = headers.index('Rounding val.')
            except ValueError as e:
                print(f"Header column not found in MRP file: {e}. Headers found: {headers}")
                return {}

            reader = csv.reader(f, delimiter='\t')
            for row in reader:
                if len(row) > max(material_col_idx, issue_location_col_idx, rounding_value_col_idx):
                    material_number = row[material_col_idx].strip()
                    issue_location = row[issue_location_col_idx].strip()
                    try:
                        rounding_value = float(row[rounding_value_col_idx].strip().replace(',', ''))
                    except (ValueError, IndexError):
                        rounding_value = 0.0

                    if material_number and material_number not in mrp_data:
                        mrp_data[material_number] = {
                            "issue_location": issue_location,
                            "rounding_value": rounding_value
                        }
    except FileNotFoundError:
        print(f"Error: MRP file not found at {mrp_file_path}")
    except Exception as e:
        import traceback
        print(f"An error occurred while reading the MRP file: {e}")
        traceback.print_exc()
        
    return mrp_data

def load_schedule(schedule_file_path):
    """
    Loads the production schedule from a CSV file. This function is specifically
    tailored to handle the multi-row header format of the given schedule file.
    It dynamically finds header rows and constructs a clean DataFrame.
    """
    try:
        with open(schedule_file_path, 'r', encoding='latin-1') as f:
            reader = csv.reader(f)
            lines = list(reader)

        # Find the primary header row index
        header_row_idx = -1
        for i, row in enumerate(lines):
            row_stripped = [item.strip() for item in row]
            if 'PART NO' in row_stripped and 'NO. URUT' in row_stripped:
                header_row_idx = i
                break
        
        if header_row_idx == -1:
            raise ValueError("Could not find the main header row containing 'PART NO'.")

        # Extract header lines
        main_header = [h.strip().replace('"' , '') for h in lines[header_row_idx]]
        day_header = [h.strip() for h in lines[header_row_idx + 2]]

        # Find column indices for ST and Takt Time
        st_col_idx = -1
        takt_time_col_idx = -1
        for i, h in enumerate(main_header):
            if h == 'ST':
                st_col_idx = i
            elif h.startswith('TAKT TIME PER MODEL'):
                takt_time_col_idx = i
        
        if st_col_idx == -1:
            raise ValueError("Could not find 'ST' column in the header.")
        if takt_time_col_idx == -1:
            raise ValueError("Could not find 'TAKT TIME PER MODEL' column in the header.")

        # Find schedule column indices
        sch_col_indices = {}
        for day in ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']:
            try:
                idx = day_header.index(day)
                sch_col_indices[f"SCH_{day}"] = idx
            except ValueError:
                pass

        # Data starts after all header rows
        data_start_idx = header_row_idx + 3
        
        # Process data rows
        data = []
        current_line = ''
        for row in lines[data_start_idx:]:
            if not any(row): # Skip empty rows
                continue

            if row[0]:
                current_line = row[0].strip()
            
            if len(row) <= max(st_col_idx, takt_time_col_idx) or not row[1]: # Skip rows without a part number or essential columns
                continue

            part_no = row[1].strip()
            model = row[2].strip()
            no_urut = row[8].strip()
            
            try:
                st_val = float(row[st_col_idx].strip()) * 60
            except (ValueError, IndexError):
                st_val = 60.0

            try:
                takt_time_val = float(row[takt_time_col_idx].strip()) * 60
            except (ValueError, IndexError):
                takt_time_val = 0.0

            record = {
                'LINE': current_line,
                'PART NO': part_no,
                'MODEL': model,
                'NO. URUT': no_urut,
                'ST': st_val,
                'TAKT_TIME': takt_time_val
            }

            for sch_col_name, sch_col_idx in sch_col_indices.items():
                try:
                    record[sch_col_name] = int(row[sch_col_idx].strip())
                except (ValueError, IndexError):
                    record[sch_col_name] = 0
            
            data.append(record)

        df = pd.DataFrame(data)
        
        return df

    except FileNotFoundError:
        print(f"Error: Schedule file not found at {schedule_file_path}")
        return pd.DataFrame()
    except Exception as e:
        print(f"An error occurred while reading the schedule file: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()

def get_schedule_summary(schedule_df):
    """
    Get a summary of the production schedule for display purposes.
    
    Args:
        schedule_df (pandas.DataFrame): The schedule DataFrame
        
    Returns:
        dict: Summary statistics of the schedule
    """
    if schedule_df.empty:
        return {}
    
    schedule_columns = ['SCH_Sun', 'SCH_Mon', 'SCH_Tue', 'SCH_Wed', 'SCH_Thu', 'SCH_Fri', 'SCH_Sat']
    summary = {}
    
    for col in schedule_columns:
        if col in schedule_df.columns:
            summary[col] = {
                'total_units': int(schedule_df[col].sum()),
                'unique_models': len(schedule_df[schedule_df[col] > 0]['MODEL'].unique()),
                'unique_parts': len(schedule_df[schedule_df[col] > 0]['PART NO'].unique())
            }
    
    return summary

if __name__ == '__main__':
    # Example usage for testing the data loaders
    bom_file = 'D:\\APLIKASI PYTHON\\production_simulator12\\YMATP0200B_BOM_20250911_231232.txt'
    mrp_file = 'D:\\APLIKASI PYTHON\\production_simulator12\\MRP_20250912.txt'
    schedule_file = 'D:\\APLIKASI PYTHON\\production_simulator12\\20250912-Schedule FA1.csv'

    # --- BOM Data Loading ---
    print("--- Loading BOM Data ---")
    bom = load_bom(bom_file)
    if bom:
        print(f"Loaded BOM for {len(bom)} parent parts.")
        # Find a parent that is also in the schedule to make the test relevant
        schedule_df_test = load_schedule(schedule_file)
        if not schedule_df_test.empty:
            scheduled_parts = schedule_df_test['PART NO'].dropna().unique()
            test_parent = next((part for part in scheduled_parts if part in bom), None)
            
            if test_parent:
                print(f"Example BOM for scheduled part: {test_parent}")
                for comp in bom[test_parent][:5]: # Print first 5 components
                    print(f"  - Component: {comp['component']}, Quantity: {comp['quantity']}")
            else:
                print("No scheduled parts found in the BOM data for a quick test.")
        else:
            print("Could not load schedule to find a relevant part for BOM test.")
    else:
        print("BOM data could not be loaded.")
    print("-" * 25)

    # --- MRP Data Loading ---
    print("--- Loading MRP Data ---")
    mrp = load_mrp_data(mrp_file)
    if mrp:
        print(f"Loaded MRP data for {len(mrp)} materials.")
        if bom:
            # Find a component from the test_parent to check in MRP
            test_parent_for_mrp = next((part for part in bom if bom[part]), None)
            if test_parent_for_mrp:
                components_to_check = [c['component'] for c in bom[test_parent_for_mrp]][:3]
                print(f"Checking MRP data for components of {test_parent_for_mrp}:")
                for comp_part in components_to_check:
                    if comp_part in mrp:
                        print(f"  - MRP for {comp_part}: {mrp[comp_part]}")
                    else:
                        print(f"  - MRP data not found for {comp_part}")
    else:
        print("MRP data could not be loaded.")
    print("-" * 25)

    # --- Schedule Data Loading ---
    print("--- Loading Schedule Data ---")
    schedule_df = load_schedule(schedule_file)
    if not schedule_df.empty:
        print("Schedule DataFrame shape:", schedule_df.shape)
        print("Cleaned Schedule Columns:", schedule_df.columns.tolist())
        print("First 5 rows of cleaned schedule:")
        print(schedule_df[['PART NO', 'MODEL', 'SCH_Mon', 'SCH_Tue', 'SCH_Wed']].head())
    else:
        print("Schedule DataFrame is empty.")
