import tkinter as tk
import csv

def parse_bom_file(file_path):
    """
    Membaca file BOM dan mengurai data untuk mendapatkan hubungan induk-anak.
    Mengembalikan dictionary di mana kunci adalah induk dan nilai adalah daftar anak.
    """
    bom_data = {}
    try:
        with open(file_path, 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    parent = parts[0].strip()
                    child = parts[1].strip()
                    if parent not in bom_data:
                        bom_data[parent] = []
                    bom_data[parent].append(child)
    except FileNotFoundError:
        print(f"Error: File tidak ditemukan di {file_path}")
    except Exception as e:
        print(f"Terjadi kesalahan saat membaca file: {e}")
    return bom_data

def print_bom_hierarchy(bom_data, part, indent=0, text_widget=None, material_data=None):
    if material_data is None:
        material_data = {}
        
    level_prefix = '.' * (indent + 1) + str(indent + 1) # Contoh: .1, ..2, ...3
    material_info = material_data.get(part, {})
    
    material_desc = material_info.get('Material Description', '')
    mrp_type = material_info.get('MRP Type', '')
    mrpc = material_info.get('MRPC', '')

    output_line = f"{level_prefix} {part} (Desc: {material_desc}, MRP Type: {mrp_type}, MRPC: {mrpc})"
    if text_widget:
        text_widget.insert(tk.END, output_line + "\n")
    else:
        print(output_line)

    if part in bom_data:
        for child in bom_data[part]:
            print_bom_hierarchy(bom_data, child, indent + 1, text_widget, material_data)

def load_material_data(file_path):
    """
    Membaca file data material dan mengurai data untuk mendapatkan informasi material.
    Mengembalikan dictionary di mana kunci adalah 'Material' dan nilai adalah dictionary 
    yang berisi 'Material Description', 'MRP Type', dan 'MRPC'.
    """
    material_data = {}
    try:
        # Mencoba membaca dengan utf-8 terlebih dahulu
        with open(file_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f, delimiter='\t')
            headers = next(reader) # Baris pertama adalah header
            print(f"Headers Material Data: {headers}") # Debugging print
            
            # Cari indeks kolom yang relevan
            try:
                material_col_idx = headers.index('Material')
                material_desc_col_idx = headers.index('Material Description')
                mrp_type_col_idx = headers.index('Typ') # Mengubah dari 'MRP Type' menjadi 'Typ'
                mrpc_col_idx = headers.index('MRPC')
                spt_col_idx = headers.index('SPT') # Menambahkan kolom SPT
            except ValueError as e:
                print(f"Error: Kolom yang dibutuhkan tidak ditemukan di file data material: {e}")
                return {}

            for row in reader:
                if len(row) > max(material_col_idx, material_desc_col_idx, mrp_type_col_idx, mrpc_col_idx, spt_col_idx):
                    material = row[material_col_idx].strip()
                    if reader.line_num <= 5: # Cetak 5 baris pertama untuk debugging
                        print(f"Row {reader.line_num}: Material={material}, Desc={row[material_desc_col_idx]}, MRP Type={row[mrp_type_col_idx]}, MRPC={row[mrpc_col_idx]}")
                    material_description = row[material_desc_col_idx].strip()
                    mrp_type = row[mrp_type_col_idx].strip()
                    mrpc = row[mrpc_col_idx].strip()
                    spt = row[spt_col_idx].strip() # Ambil data SPT
                    material_data[material] = {
                        'Material Description': material_description,
                        'MRP Type': mrp_type,
                        'MRPC': mrpc,
                        'SPT': spt # Simpan data SPT
                    }
    except FileNotFoundError:
        print(f"Error: File tidak ditemukan di {file_path}")
    except UnicodeDecodeError:
        try:
            # Jika utf-8 gagal, coba latin-1
            with open(file_path, 'r', newline='', encoding='latin-1') as f:
                reader = csv.reader(f, delimiter='\t')
                headers = next(reader)
                print(f"Headers Material Data (latin-1): {headers}") # Debugging print

                try:
                    material_col_idx = headers.index('Material')
                    material_desc_col_idx = headers.index('Material Description')
                    mrp_type_col_idx = headers.index('Typ')
                    mrpc_col_idx = headers.index('MRPC')
                    spt_col_idx = headers.index('SPT')
                except ValueError as e:
                    print(f"Error: Kolom yang dibutuhkan tidak ditemukan di file data material (latin-1): {e}")
                    return {}

                for row in reader:
                    if len(row) > max(material_col_idx, material_desc_col_idx, mrp_type_col_idx, mrpc_col_idx, spt_col_idx):
                        material = row[material_col_idx].strip()
                        if reader.line_num <= 5: # Cetak 5 baris pertama untuk debugging
                            print(f"Row {reader.line_num}: Material={material}, Desc={row[material_desc_col_idx]}, MRP Type={row[mrp_type_col_idx]}, MRPC={row[mrpc_col_idx]}")
                        material_description = row[material_desc_col_idx].strip()
                        mrp_type = row[mrp_type_col_idx].strip()
                        mrpc = row[mrpc_col_idx].strip()
                        spt = row[spt_col_idx].strip()
                        material_data[material] = {
                            'Material Description': material_description,
                            'MRP Type': mrp_type,
                            'MRPC': mrpc,
                            'SPT': spt
                        }
        except Exception as e:
            print(f"Terjadi kesalahan saat membaca file data material dengan latin-1: {e}")
            return {}
    except Exception as e:
        print(f"Terjadi kesalahan saat membaca file data material: {e}")
    return material_data

def get_bom_hierarchy_list(bom_data, part, material_data, indent=0, hierarchy_list=None):
    if hierarchy_list is None:
        hierarchy_list = []

    level_prefix = '.' * (indent + 1) + str(indent + 1)
    material_info = material_data.get(part, {})
    hierarchy_list.append((level_prefix, part, material_info)) # Simpan sebagai tuple (level, part, material_info)

    if part in bom_data:
        for child in bom_data[part]:
            get_bom_hierarchy_list(bom_data, child, material_data, indent + 1, hierarchy_list)
    return hierarchy_list