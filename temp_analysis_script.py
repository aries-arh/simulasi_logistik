import pandas as pd
import csv
from collections import defaultdict
import os

# Define file paths (using the user's provided paths)
CURRENT_SCHEDULE_FILE = "D:\\APLIKASI PYTHON\\production_simulator13\\20250915-Schedule FA1.csv"
CURRENT_MRP_FILE = "D:\\APLIKASI PYTHON\\production_simulator13\\MRP_20250915.txt"
CURRENT_BOM_FILE = "D:\\APLIKASI PYTHON\\production_simulator13\\YMATP0200B_BOM_20250914_225614.txt"

def load_schedule(schedule_file_path):
    try:
        df = pd.read_csv(schedule_file_path, header=2, encoding='latin-1')
        df = df[[' LINE ', ' PART NO ', ' MODEL ', '15-Sep', ' ST ']].copy()
        df.columns = ['LINE', 'PART NO', 'MODEL', 'SCH_Mon', 'ST']
        df.dropna(how='all', inplace=True)
        df = df[~df['LINE'].astype(str).str.contains('TOTAL', na=False)]
        
        # NEW FILTER: Remove rows where 'PART NO' is empty or NaN
        df = df.dropna(subset=['PART NO'])
        df = df[df['PART NO'].astype(str).str.strip() != '']

        df['SCH_Mon'] = pd.to_numeric(df['SCH_Mon'], errors='coerce').fillna(0)
        df['ST'] = pd.to_numeric(df['ST'], errors='coerce').fillna(60)
        return df
    except Exception as e:
        print(f"Error loading schedule: {e}")
        return pd.DataFrame()

def load_mrp_data(mrp_file_path):
    mrp_data = {}
    try:
        with open(mrp_file_path, 'r', encoding='latin-1') as f:
            headers = f.readline().strip().split('\t')
            reader = csv.reader(f, delimiter='\t')
            material_col_idx = headers.index('Material') if 'Material' in headers else 3
            issue_location_col_idx = headers.index('Iss. Stor, loc') if 'Iss. Stor, loc' in headers else 18
            rounding_value_col_idx = headers.index('Rounding val.') if 'Rounding val.' in headers else 9

            for row in reader:
                if len(row) > max(material_col_idx, issue_location_col_idx, rounding_value_col_idx):
                    material_number = row[material_col_idx].strip()
                    issue_location = row[issue_location_col_idx].strip()
                    try:
                        rounding_value = float(row[rounding_value_col_idx].strip().replace(',', ''))
                    except (ValueError, IndexError):
                        rounding_value = 0.0
                    if material_number:
                        if material_number not in mrp_data:
                            mrp_data[material_number] = {
                                "issue_location": issue_location,
                                "rounding_value": rounding_value
                            }
        return mrp_data
    except Exception as e:
        print(f"Error loading MRP data: {e}")
        return {}

def load_bom(bom_file_path):
    bom_data = defaultdict(list)
    try:
        with open(bom_file_path, 'r', encoding='latin-1') as f:
            for line_num, line in enumerate(f):
                if line_num < 1: # Skip header line if any
                    continue
                if len(line) < 80: # Basic check for line length
                    continue
                parent_part = line[0:16].strip()
                component_part = line[16:32].strip()
                quantity = 1.0
                if parent_part and component_part:
                    bom_data[parent_part].append({
                        "component": component_part,
                        "quantity": quantity
                    })
        return bom_data
    except Exception as e:
        print(f"Error loading BOM data: {e}")
        return defaultdict(list)

# --- Main analysis logic ---
print("Starting file analysis...")

schedule_df = load_schedule(CURRENT_SCHEDULE_FILE)
mrp_data = load_mrp_data(CURRENT_MRP_FILE)
bom_data = load_bom(CURRENT_BOM_FILE)

print(f"Schedule loaded: {not schedule_df.empty} (Rows: {len(schedule_df)}) ")
print(f"MRP loaded: {bool(mrp_data)} (Materials: {len(mrp_data)}) ")
print(f"BOM loaded: {bool(bom_data)} (Parent Parts: {len(bom_data)}) ")

results = []
# Take a sample of part numbers from the schedule
# Ensure schedule_df is not empty before trying to access columns
if not schedule_df.empty and 'PART NO' in schedule_df.columns:
    sample_part_nos = schedule_df['PART NO'].unique()[:5] # First 5 unique part numbers

    for part_no in sample_part_nos:
        parent_info = {
            "part_no": part_no,
            "line": schedule_df[schedule_df['PART NO'] == part_no]['LINE'].iloc[0] if not schedule_df[schedule_df['PART NO'] == part_no].empty else "N/A",
            "model": schedule_df[schedule_df['PART NO'] == part_no]['MODEL'].iloc[0] if not schedule_df[schedule_df['PART NO'] == part_no].empty else "N/A",
            "components": []
        }
        
        components_in_bom = bom_data.get(part_no, [])
        if components_in_bom:
            for comp_item in components_in_bom:
                component = comp_item["component"]
                component_info = {
                    "component_part": component,
                    "quantity_needed": comp_item["quantity"],
                    "mrp_area": "N/A"
                }
                
                mrp_info = mrp_data.get(component)
                if mrp_info:
                    component_info["mrp_area"] = mrp_info["issue_location"]
                
                parent_info["components"].append(component_info)
        else:
            parent_info["components"].append({"component_part": "No BOM found", "quantity_needed": "N/A", "mrp_area": "N/A"})
        
        results.append(parent_info)

    print("\n--- Sample of Relationships (Schedule -> BOM -> MRP) ---")
    for item in results:
        print(f"Product: {item['part_no']} (Line: {item['line']}, Model: {item['model']})")
        for comp in item['components']:
            print(f"  -> Component: {comp['component_part']} (Qty: {comp['quantity_needed']}, MRP Area: {comp['mrp_area']})")
        print("-" * 30)
else:
    print("Schedule DataFrame is empty or 'PART NO' column is missing. Cannot perform analysis.")
