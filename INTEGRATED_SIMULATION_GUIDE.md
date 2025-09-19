# Panduan Simulasi Terintegrasi Production & Logistics

## Apa itu Simulasi Terintegrasi?

Simulasi terintegrasi menggabungkan dua sistem:
1. **Production Simulation** - Simulasi jalur produksi yang membutuhkan material
2. **Logistics Simulation** - Simulasi transportasi material ke jalur produksi

## Cara Kerja Simulasi Terintegrasi

### 1. Production Simulation
- Membaca jadwal produksi dari file CSV
- Membaca BOM (Bill of Materials) dari file TXT
- Menjalankan proses produksi sesuai konfigurasi
- **Meminta material** ketika stok habis

### 2. Logistics Simulation
- Menerima permintaan material dari production
- Menggunakan MRP data untuk menentukan lokasi material
- Mengirim transport unit untuk mengirim material
- **Mengirim material** ke proses produksi

### 3. Integrasi
- Production meminta material → Logistics mengirim material
- Kedua simulasi berjalan bersamaan dan saling berinteraksi

## Langkah-langkah Menjalankan Simulasi Terintegrasi

### 1. Persiapan Data
Pastikan file-file berikut ada:
- `20250912-Schedule FA1.csv` - Jadwal produksi
- `YMATP0200B_BOM_20250911_231232.txt` - Bill of Materials
- `MRP_20250912.txt` - Material Requirements Planning

### 2. Setup Konfigurasi
Buat konfigurasi untuk:
- **Production Setup**: Proses-proses produksi, cycle time, operator
- **Logistics Setup**: Lokasi, transport unit, tugas transportasi

### 3. Jalankan Simulasi
1. Buka UI di `http://localhost:3001`
2. Pilih "Integrated Simulation"
3. Pilih Production Setup dan Logistics Setup
4. Klik "Start Integrated Simulation"
5. Monitor status real-time

## Endpoint API untuk Simulasi Terintegrasi

### Start Integrated Simulation
```
POST /simulation/start-integrated/{prod_setup_id}/{log_setup_id}
```

### Monitor Status
```
GET /production/status
GET /logistics/status
```

## Troubleshooting

### Error: "Production simulation must be running before starting logistics"
- Pastikan production simulation dimulai terlebih dahulu
- Logistics simulation membutuhkan production engine yang aktif

### Error: "Failed to load schedule or BOM data"
- Periksa path file di `main.py`
- Pastikan file CSV dan TXT ada dan dapat dibaca

### Error: "No starting processes defined"
- Pastikan ada proses produksi tanpa input_from
- Minimal satu proses harus bisa dimulai tanpa material dari proses lain

## Contoh Konfigurasi

### Production Setup
```json
{
  "processes": [
    {
      "name": "Assembly",
      "cycle_time": 60,
      "num_operators": 2,
      "ng_rate": 0.05,
      "input_from": [],
      "output_to": ["Packaging"]
    },
    {
      "name": "Packaging",
      "cycle_time": 30,
      "num_operators": 1,
      "ng_rate": 0.02,
      "input_from": ["Assembly"],
      "output_to": []
    }
  ]
}
```

### Logistics Setup
```json
{
  "locations": [
    {"name": "WAREHOUSE", "stock": {"MATERIAL_A": 1000}},
    {"name": "Assembly", "stock": {}},
    {"name": "Packaging", "stock": {}}
  ],
  "transport_units": [
    {"name": "Forklift 1", "type": "Forklift", "num_sub_units": 1, "capacity_per_sub_unit": 10}
  ],
  "tasks": [
    {
      "origin": "WAREHOUSE",
      "destination": "Assembly",
      "material": "MATERIAL_A",
      "lots_required": 1,
      "distance": 100,
      "travel_time": 30,
      "loading_time": 10,
      "unloading_time": 10,
      "transport_unit_names": ["Forklift 1"]
    }
  ]
}
```

## Monitoring Real-time

UI akan menampilkan:
- Status produksi: unit completed, scrapped, progress per proses
- Status logistik: transport unit status, completed tasks, event log
- Update otomatis setiap 2 detik

## Tips Penggunaan

1. **Mulai dengan konfigurasi sederhana** - 2-3 proses produksi, 1-2 transport unit
2. **Monitor event log** - Lihat interaksi antara production dan logistics
3. **Periksa material flow** - Pastikan material tersedia di lokasi yang benar
4. **Tune parameters** - Sesuaikan cycle time, travel time, capacity sesuai kebutuhan
