import os
import glob
import shutil
import csv
from collections import defaultdict

# This function is adapted from the original bom_parser.py
def parse_bom_file(file_path):
    """
    Parses a BOM file where parent and child are separated by spaces.
    Returns a dictionary where keys are parents and values are lists of children.
    """
    bom_data = defaultdict(list)
    try:
        # Using latin-1 encoding as it's common in these system-generated files
        with open(file_path, 'r', encoding='latin-1') as f:
            for line in f:
                # Assuming the format is "PARENT_PART CHILD_PART ..."
                parts = line.split()
                if len(parts) >= 2:
                    parent = parts[0].strip()
                    child = parts[1].strip()
                    if parent and child:
                        bom_data[parent].append(child)
    except FileNotFoundError:
        print(f"ERROR: BOM file not found at {file_path}")
    except Exception as e:
        print(f"ERROR: An error occurred while reading the BOM file: {e}")
    return bom_data

# This function is adapted from the original bom_parser.py
def load_material_data(file_path):
    """
    Loads material data from a tab-separated CSV file.
    Returns a dictionary mapping 'Material' to its details.
    """
    material_data = {}
    if not os.path.exists(file_path):
        print(f"ERROR: Material data file not found at {file_path}")
        return material_data

    try:
        # Try with utf-8 first
        encoding = 'utf-8'
        with open(file_path, 'r', newline='', encoding=encoding) as f:
            # Sniff to detect delimiter, in case it's not tab
            try:
                dialect = csv.Sniffer().sniff(f.read(1024), delimiters='\t,;')
                f.seek(0)
                reader = csv.reader(f, dialect)
            except csv.Error:
                f.seek(0)
                reader = csv.reader(f, delimiter='\t') # Fallback to tab

            headers = next(reader)
            # Normalize headers
            headers = [h.strip() for h in headers]

            # Find column indices dynamically
            col_indices = {
                'material': headers.index('Material'),
                'desc': headers.index('Material Description'),
                'mrp_type': headers.index('Typ'),
                'mrpc': headers.index('MRPC'),
                'spt': headers.index('SPT')
            }

            for row in reader:
                if len(row) > max(col_indices.values()):
                    material = row[col_indices['material']].strip()
                    if material:
                        material_data[material] = {
                            'Material Description': row[col_indices['desc']].strip(),
                            'MRP Type': row[col_indices['mrp_type']].strip(),
                            'MRPC': row[col_indices['mrpc']].strip(),
                            'SPT': row[col_indices['spt']].strip()
                        }
    except (UnicodeDecodeError, IndexError):
        # If utf-8 fails or there's an index error, try latin-1
        encoding = 'latin-1'
        with open(file_path, 'r', newline='', encoding=encoding) as f:
            try:
                dialect = csv.Sniffer().sniff(f.read(1024), delimiters='\t,;')
                f.seek(0)
                reader = csv.reader(f, dialect)
            except csv.Error:
                f.seek(0)
                reader = csv.reader(f, delimiter='\t')

            headers = next(reader)
            headers = [h.strip() for h in headers]
            
            col_indices = {
                'material': headers.index('Material'),
                'desc': headers.index('Material Description'),
                'mrp_type': headers.index('Typ'),
                'mrpc': headers.index('MRPC'),
                'spt': headers.index('SPT')
            }

            for row in reader:
                 if len(row) > max(col_indices.values()):
                    material = row[col_indices['material']].strip()
                    if material:
                        material_data[material] = {
                            'Material Description': row[col_indices['desc']].strip(),
                            'MRP Type': row[col_indices['mrp_type']].strip(),
                            'MRPC': row[col_indices['mrpc']].strip(),
                            'SPT': row[col_indices['spt']].strip()
                        }
    except Exception as e:
        print(f"ERROR: Failed to load material data using encoding {encoding}: {e}")

    return material_data


class BOMService:
    """
    A service to handle BOM data, providing the nearest child components for production.
    """
    def __init__(self):
        """
        Initializes the BOM service by loading the latest BOM and material data.
        """
        self.bom_data = {}
        self.material_data = {}
        
        print("INFO: Initializing BOMService...")
        self._load_latest_material_data()
        self._load_latest_bom_data()
        print("INFO: BOMService initialized.")

    def _load_latest_material_data(self):
        """
        Finds the latest material data file from the network drive,
        copies it locally, and loads it.
        """
        source_folder = "N:\\Download\\MaterialPlantDataList"
        local_filename = "material_plant_data.txt"
        
        try:
            if not os.path.isdir(source_folder):
                print(f"WARNING: Material source folder not found: {source_folder}. Trying to use local file.")
            else:
                list_of_files = glob.glob(os.path.join(source_folder, '*.txt'))
                if list_of_files:
                    latest_file = max(list_of_files, key=os.path.getmtime)
                    shutil.copy(latest_file, local_filename)
                    print(f"INFO: Copied latest material data from {latest_file}")
                else:
                    print(f"WARNING: No material data files found in {source_folder}.")

            self.material_data = load_material_data(local_filename)
            print(f"INFO: Loaded {len(self.material_data)} material data entries.")

        except Exception as e:
            print(f"ERROR: Could not load material data: {e}")
            # Try to load local file as a fallback
            if os.path.exists(local_filename):
                self.material_data = load_material_data(local_filename)
                print(f"INFO: Loaded {len(self.material_data)} material data entries from local fallback.")

    def _load_latest_bom_data(self):
        """
        Finds the latest BOM file from the network drive and loads it.
        """
        source_folder = "N:\\Download\\BOM"
        
        try:
            if not os.path.isdir(source_folder):
                 print(f"WARNING: BOM source folder not found: {source_folder}.")
                 return

            list_of_files = glob.glob(os.path.join(source_folder, '*.txt'))
            if list_of_files:
                latest_file = max(list_of_files, key=os.path.getmtime)
                print(f"INFO: Loading latest BOM data from {latest_file}")
                # Use the parsing logic from bom_parser.py
                self.bom_data = parse_bom_file(latest_file)
                print(f"INFO: Loaded BOM data for {len(self.bom_data)} parent parts.")
            else:
                print(f"WARNING: No BOM files found in {source_folder}.")

        except Exception as e:
            print(f"ERROR: Could not load BOM data: {e}")

    def get_components(self, parent_part: str, mrpc_filter: str = "*", spt_filter: str = "*"):
        """
        Gets the nearest child components for a given parent part, applying filters.
        This replaces the simple bom_data.get() call.
        The quantity is assumed to be 1 as per the new parsing logic.
        """
        if not self.bom_data:
            print("WARNING: BOM data is not loaded. Cannot get components.")
            return []

        found_children = []
        self._find_nearest_filtered_children_recursive(
            current_part=parent_part,
            mrpc_filter=mrpc_filter,
            spt_filter=spt_filter,
            found_children=found_children
        )
        
        # Format the output to match what ProductionEngineV2 expects
        # [{'component': 'CHILD1', 'quantity': 1}, ...]
        formatted_children = [{'component': child, 'quantity': 1} for child in found_children]
        
        if not formatted_children:
             # Fallback: if the "nearest child" logic returns nothing,
             # return the direct children from the BOM, if any.
             # This maintains some backward compatibility.
            direct_children = self.bom_data.get(parent_part, [])
            formatted_children = [{'component': child, 'quantity': 1} for child in direct_children]

        return formatted_children

    def _find_nearest_filtered_children_recursive(self, current_part: str, mrpc_filter: str, spt_filter: str, found_children: list):
        """
        Recursively finds the first level of children that match the filters.
        Adapted from the logic in bom_gui - r1.py.
        """
        children_of_current_part = self.bom_data.get(current_part, [])
        
        matching_children_at_this_level = []

        for child in children_of_current_part:
            material_info = self.material_data.get(child, {})
            item_mrpc = material_info.get('MRPC', '').upper()
            item_spt = material_info.get('SPT', '').upper()

            # Check MRPC filter
            mrpc_match = False
            if mrpc_filter == "*" or not mrpc_filter:
                mrpc_match = True
            else:
                mrpc_match = (mrpc_filter.upper() == item_mrpc)

            # Check SPT filter
            spt_match = False
            if spt_filter == "*" or not spt_filter:
                spt_match = True
            else:
                spt_match = (spt_filter.upper() == item_spt)

            if mrpc_match and spt_match:
                matching_children_at_this_level.append(child)

        if matching_children_at_this_level:
            # If we found matching children at this level, add them and stop recursing down this branch
            found_children.extend(matching_children_at_this_level)
        else:
            # Otherwise, recurse deeper
            for child in children_of_current_part:
                self._find_nearest_filtered_children_recursive(child, mrpc_filter, spt_filter, found_children)
