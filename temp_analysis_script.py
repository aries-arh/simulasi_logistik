
import pandas as pd
import json
import sys
import os
from datetime import datetime

# Add backend to path to allow importing from data_loader
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from data_loader import load_schedule
except ImportError as e:
    print(f"Failed to import load_schedule: {e}")
    print("Please ensure you are running this script from the project root directory.")
    sys.exit(1)

def analyze_setup_mismatch():
    try:
        # 1. Read Schedule File using the project's own loader
        schedule_file = '20250912-Schedule FA1.csv'
        schedule_df = load_schedule(schedule_file)

        if schedule_df.empty:
            print("Gagal memuat jadwal menggunakan data_loader.load_schedule.")
            return

        # Determine today's schedule column (e.g., SCH_Fri)
        day_column_map = { 4: 'SCH_Fri' } # Friday is weekday 4
        today_weekday = datetime.now().weekday()
        today_column = day_column_map.get(today_weekday)

        if not today_column or today_column not in schedule_df.columns:
            print(f"Kolom jadwal untuk hari ini ('{today_column}') tidak ditemukan di file jadwal.")
            # As a fallback, let's just check for any schedule column
            sched_cols = [col for col in schedule_df.columns if col.startswith('SCH_')]
            if not sched_cols:
                print("Tidak ada kolom SCH_ (jadwal) yang ditemukan sama sekali.")
                return
            today_column = sched_cols[0]
            print(f"Menggunakan kolom jadwal pertama yang ditemukan sebagai gantinya: {today_column}")


        schedule_df[today_column] = pd.to_numeric(schedule_df[today_column], errors='coerce').fillna(0)
        
        scheduled_lines = set(
            schedule_df[schedule_df[today_column] > 0]['LINE'].dropna().astype(str).str.strip()
        )
        print(f"--- Analisis Jadwal Produksi ({today_column}) ---")
        if not scheduled_lines:
            print(f"Tidak ditemukan lini dengan jadwal > 0 untuk kolom '{today_column}'.")
        else:
            print(f"Ditemukan {len(scheduled_lines)} lini yang dijadwalkan:")
            for line in sorted(list(scheduled_lines)):
                print(f"- {line}")

        # 2. Read Production Setup File
        setup_file = 'production_setup.json'
        with open(setup_file, 'r') as f:
            setup_data = json.load(f)
        
        configured_lines = set(
            key.strip() for key in setup_data.get("setup_data", {}).get("line_processes", {}).keys()
        )
        print(f"\n--- Analisis Konfigurasi Proses Produksi ---")
        if not configured_lines:
            print("Tidak ditemukan lini yang memiliki konfigurasi proses di production_setup.json.")
        else:
            print(f"Ditemukan {len(configured_lines)} lini yang dikonfigurasi:")
            for line in sorted(list(configured_lines)):
                print(f"- {line}")

        # 3. Find and Report Mismatches
        print(f"\n--- Laporan Ketidakcocokan ---")
        
        lines_in_schedule_but_not_config = scheduled_lines - configured_lines
        if lines_in_schedule_but_not_config:
            print(f"\nCRITICAL WARNING: Ditemukan {len(lines_in_schedule_but_not_config)} lini yang ada di JADWAL tapi TIDAK ADA di KONFIGURASI.")
            print("Ini adalah penyebab masalah. Nama harus cocok persis (setelah mengabaikan spasi).")
            for line in sorted(list(lines_in_schedule_but_not_config)):
                print(f"  -> Lini terjadwal '{line}' tidak ditemukan dalam konfigurasi.")
        else:
            print("INFO: Semua lini yang dijadwalkan memiliki konfigurasi proses yang cocok (dibandingkan dengan production_setup.json).")

        lines_in_config_but_not_schedule = configured_lines - scheduled_lines
        if lines_in_config_but_not_schedule:
            print(f"\nINFO: Ditemukan {len(lines_in_config_but_not_schedule)} lini yang ada di KONFIGURASI tapi tidak memiliki jadwal hari ini.")
            # for line in sorted(list(lines_in_config_but_not_schedule)):
            #     print(f"  - '{line}'")
        
        if not lines_in_schedule_but_not_config:
            print("\nKESIMPULAN: Tidak ditemukan ketidakcocokan nama baris antara jadwal hari ini dan file production_setup.json.")
            print("Jika masalah berlanjut, kemungkinan konfigurasi produksi yang sebenarnya dimuat dari DATABASE, bukan dari file .json.")
            print("Pastikan nama baris di UI manajemen skenario cocok dengan nama baris di file jadwal Anda.")

    except Exception as e:
        print(f"Terjadi kesalahan saat analisis: {e}")

if __name__ == "__main__":
    analyze_setup_mismatch()
