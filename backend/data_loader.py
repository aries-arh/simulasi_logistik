import pandas as pd
from collections import defaultdict
import csv
import os
from datetime import datetime

def parse_time_to_seconds(val):
    try:
        if pd.isna(val): return 0.0
        s = str(val).strip()
        if not s or s == '-': return 0.0
        if ':' in s:
            parts = [float(p) for p in s.split(':') if p.replace('.', '', 1).isdigit()]
            if len(parts) == 3: return parts[0] * 3600 + parts[1] * 60 + parts[2]
            if len(parts) == 2: return parts[0] * 60 + parts[1]
            if len(parts) == 1: return parts[0]
        return float(str(val).replace(',', '').strip())
    except (ValueError, TypeError): return 0.0



def load_mrp_data(mrp_file_path):
    """
    Loads Material Requirements Planning (MRP) data from a text file.
    This function is now more robust, dynamically finding column indices from the header.
    """
    mrp_data = {}
    try:
        with open(mrp_file_path, 'r', encoding='latin-1') as f:
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
    Loads the production schedule from a CSV or Excel file.
    This version is designed to handle the specific multi-line header format.
    """
    try:
        print(f"--- DEBUG: Loading schedule file: {schedule_file_path} ---")
        file_extension = os.path.splitext(schedule_file_path)[1].lower()
        
        header_rows = [2, 3]

        if file_extension == '.csv':
            df = pd.read_csv(schedule_file_path, encoding='latin-1', header=header_rows)
        elif file_extension in ['.xlsx', '.xls']:
            df = pd.read_excel(schedule_file_path, header=header_rows)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

        # --- Stage 1: Column Name Processing ---
        new_cols_tuples = []
        last_s1 = ''
        for col1, col2 in df.columns:
            s1 = str(col1).strip()
            s2 = str(col2).strip()
            if not s1.startswith('Unnamed'):
                last_s1 = s1
            elif s1.startswith('Unnamed') and last_s1:
                 s1 = last_s1
            new_cols_tuples.append((s1, s2))

        new_cols = [f"{s1}_{s2}" if not s1.startswith('Unnamed') and not s2.startswith('Unnamed') else s2 if s1.startswith('Unnamed') else s1 for s1, s2 in new_cols_tuples]
        df.columns = new_cols
        df.columns = df.columns.str.strip().str.replace('''\n''', ' ', regex=False)

        # --- Stage 2: Rename, Normalize, and De-duplicate Columns ---
        schedule_cols_to_rename = {}
        for col in df.columns:
            try:
                date_part_str = col.split('_')[-1]
                # First, try to parse the full datetime format that might appear in Excel headers
                parsed_date = pd.to_datetime(date_part_str, format='%Y-%m-%d %H:%M:%S', errors='coerce')
                
                # If parsing fails, try the shorter DD-Mon format
                if pd.isna(parsed_date):
                    parsed_date = pd.to_datetime(date_part_str, format='%d-%b', errors='coerce')

                # If a valid date was parsed, rename the column
                if pd.notna(parsed_date):
                    date_str_for_col = parsed_date.strftime('%d-%b')
                    if 'SCHEDULE' in col.upper():
                        schedule_cols_to_rename[col] = f"SCH_{date_str_for_col}"

            except (ValueError, TypeError):
                continue
        df.rename(columns=schedule_cols_to_rename, inplace=True)

        column_mapping = {
            'LINE': 'LINE', 'PART NO': 'PART NO', 'MODEL': 'MODEL', 'NO. URUT': 'NO. URUT', 'ST': 'ST',
            'Takt Time Per Model': 'TAKT_TIME', 'TAKT TIME PER MODEL (BEBAN/TOTAL BEBAN) * WAKTU KERJA/SCH': 'TAKT_TIME',
            'Takt Time ALL Model': 'TAKT_TIME', 'TAKT TIME ALL MODEL': 'TAKT_TIME', 'Takt Time': 'TAKT_TIME',
            'GROUP KERJA': 'GROUP_KERJA', 'Group Kerja': 'GROUP_KERJA', 'Jmlh Group': 'JMLH_GROUP',
            'Jml Group': 'JMLH_GROUP', 'Jml Opr Direct': 'JML_OPR_DIRECT', 'Jml Opr Dir': 'JML_OPR_DIRECT'
        }
        df.rename(columns=column_mapping, inplace=True)

        def norm_key(s: str) -> str:
            return str(s or '').lower().replace(' ', '').replace('_', '')
        flex_map = {col: 'GROUP_KERJA' for col in df.columns if 'groupkerja' in norm_key(col)}
        flex_map.update({col: 'JMLH_GROUP' for col in df.columns if 'jmlhgroup' in norm_key(col)})
        flex_map.update({col: 'JML_OPR_DIRECT' for col in df.columns if 'jmloprdirect' in norm_key(col)})
        if flex_map:
            df.rename(columns=flex_map, inplace=True)

        cols = pd.Series(df.columns)
        for dup in cols[cols.duplicated()].unique():
            cols[cols[cols == dup].index.values.tolist()] = [f"{dup}.{i}" if i != 0 else dup for i in range(sum(cols == dup))]
        df.columns = cols

        # Consolidate TAKT_TIME columns if duplicates exist
        takt_time_cols_after_dedup = [col for col in df.columns if col.startswith('TAKT_TIME')]
        
        if takt_time_cols_after_dedup:
            # Create a temporary Series to hold the consolidated TAKT_TIME
            consolidated_takt_time = pd.Series(pd.NA, index=df.index)
            
            for col in takt_time_cols_after_dedup:
                # Fill NaN values in consolidated_takt_time with values from the current TAKT_TIME column
                consolidated_takt_time = consolidated_takt_time.fillna(df[col])
            
            # Drop all original TAKT_TIME columns
            df.drop(columns=takt_time_cols_after_dedup, errors='ignore', inplace=True)
            
            # Assign the consolidated TAKT_TIME back to the DataFrame
            df['TAKT_TIME'] = consolidated_takt_time
        else:
            # If no TAKT_TIME columns were found, create an empty one
            df['TAKT_TIME'] = pd.Series(pd.NA, index=df.index)

        # Ensure TAKT_TIME is numeric and apply parse_time_to_seconds
        if 'TAKT_TIME' in df.columns:
            df['TAKT_TIME'] = df['TAKT_TIME'].apply(parse_time_to_seconds)
            df['TAKT_TIME'].fillna(0, inplace=True) # Fill any remaining NaN after parsing with 0

        # --- Stage 3: Forward-fill LINE identifier ---
        if 'LINE' in df.columns:
            df['LINE'] = df['LINE'].ffill()

        # --- Stage 4: Propagate Metadata BEFORE dropping rows ---
        # This version uses groupby().agg() to find the single canonical metadata value for each
        # line, and then uses Series.map() to broadcast that value back to all rows for that line.
        meta_cols = ['GROUP_KERJA', 'JMLH_GROUP', 'JML_OPR_DIRECT', 'TAKT_TIME']
        if 'LINE' in df.columns:
            def get_first_valid(series):
                """Finds the first non-NA and non-empty-string value in a series."""
                for v in series:
                    if pd.notna(v) and str(v).strip():
                        return v
                return pd.NA

            for col in meta_cols:
                if col in df.columns:
                    # Create a mapping from each LINE to its single valid metadata value
                    line_to_value_map = df.groupby('LINE')[col].agg(get_first_valid)
                    
                    # Apply this map to the LINE column to fill the metadata column
                    df[col] = df['LINE'].map(line_to_value_map)

        # --- Stage 5: Clean and Filter Rows ---
        if 'LINE' in df.columns:
            df['LINE'] = df['LINE'].astype(str).str.strip()
            # Now that metadata is propagated, we can safely drop rows that are not parts.
            df.dropna(subset=['PART NO'], inplace=True)
            df = df[~df['LINE'].str.startswith('TOTAL', na=False)]
            df = df[df['PART NO'].str.strip() != '']


        # --- Stage 5: Final Type Conversion and Cleanup ---
        if 'ST' in df.columns:
            df['ST'] = pd.to_numeric(df['ST'], errors='coerce').fillna(1.0) * 60
        if 'TAKT_TIME' in df.columns:
            df['TAKT_TIME'] = df['TAKT_TIME'].apply(parse_time_to_seconds)
            df['TAKT_TIME'].fillna(0, inplace=True)
        if 'NO. URUT' in df.columns:
            df['NO. URUT'] = pd.to_numeric(df['NO. URUT'], errors='coerce')
        if 'GROUP_KERJA' in df.columns:
            df['GROUP_KERJA'] = df['GROUP_KERJA'].fillna('').astype(str).str.strip()
        if 'JMLH_GROUP' in df.columns:
            df['JMLH_GROUP'] = pd.to_numeric(df['JMLH_GROUP'], errors='coerce').fillna(1).astype(int)
        if 'JML_OPR_DIRECT' in df.columns:
            df['JML_OPR_DIRECT'] = pd.to_numeric(df['JML_OPR_DIRECT'], errors='coerce').round().fillna(0).astype(int)

        # --- Stage 6: Convert SCH_ columns to numeric ---
        for col in df.columns:
            if col.startswith('SCH_'):
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        print("--- DEBUG: TAKT_TIME after all processing ---")
        print(df[['LINE', 'PART NO', 'TAKT_TIME']].head(50).to_string())

        print("--- DEBUG: TAKT_TIME after all processing ---")
        print(df[['LINE', 'PART NO', 'TAKT_TIME']].head(50).to_string())

        return df

    except Exception as e:
        import traceback
        print(f"An error occurred while loading schedule: {e}")
        traceback.print_exc()
        raise

def get_schedule_summary(schedule_df):
    """
    Get a summary of the production schedule for display purposes.
    """
    if schedule_df.empty:
        return {}
    
    schedule_columns = [col for col in schedule_df.columns if col.startswith('SCH_')]
    summary = {}
    
    for col in schedule_columns:
        if col in schedule_df.columns:
            summary[col] = {
                'total_units': int(schedule_df[col].sum()),
                'unique_models': len(schedule_df[schedule_df[col] > 0]['MODEL'].unique()),
                'unique_parts': len(schedule_df[schedule_df[col] > 0]['PART NO'].unique())
            }
    
    return summary