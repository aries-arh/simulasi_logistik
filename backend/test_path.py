import os

path = "\\\\10.107.49.3\ma\Download\MRPArea"

print(f"Mencoba mengakses: {path}")

try:
    contents = os.listdir(path)
    print("Akses berhasil!")
    if contents:
        print("Isi direktori (5 item pertama):")
        for item in contents[:5]: # Print first 5 items
            print(f"- {item}")
    else:
        print("Direktori kosong.")
except Exception as e:
    print(f"GAGAL mengakses direktori.")
    print(f"Error: {e}")
