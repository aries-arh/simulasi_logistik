# Analisis Kaitan File Production Simulator

## Ringkasan File

### 1. **20250912-Schedule FA1.csv** - Jadwal Produksi
- **Fungsi**: Menentukan apa yang akan diproduksi dan kapan
- **Struktur**: 
  - Kolom `PART NO`: Part number yang akan diproduksi (contoh: VGF4340, VGF4390, VGF4240)
  - Kolom `SCH_Mon`, `SCH_Tue`, dll: Jumlah unit yang harus diproduksi per hari
  - Kolom `MODEL`: Model produk (contoh: CLP-825B, CLP-825R)
  - Kolom `SPEC`: Spesifikasi (E, K)
  - Kolom `PEDAL`, `SCREW SET`, `KEYBOARD`: Komponen yang dibutuhkan

### 2. **YMATP0200B_BOM_20250911_231232.txt** - Bill of Materials
- **Fungsi**: Menentukan komponen apa saja yang dibutuhkan untuk membuat setiap part
- **Struktur**: 
  - Kolom 1 (0-16): Parent Part Number (produk akhir)
  - Kolom 2 (16-32): Component Part Number (komponen yang dibutuhkan)
  - Kolom 3 (32-40): Quantity (jumlah komponen yang dibutuhkan)
- **Contoh**: 
  ```
  VGF4240         V874062             0  19980101     100000000000099991231   0      1000000       PC
  ```
  Artinya: Untuk membuat VGF4240, dibutuhkan 1 unit V874062

### 3. **MRP_20250912.txt** - Material Requirements Planning
- **Fungsi**: Menentukan lokasi penyimpanan dan pengaturan material
- **Struktur**:
  - Kolom 3: Material Number (part number)
  - Kolom 18: Issue Storage Location (lokasi pengeluaran material)
  - Kolom 9: Rounding Value (nilai pembulatan)
- **Contoh**:
  ```
  8200	8200PS01	V874062	HEADPHONE HANGER SET CL       #2739	M0	EX	WL5	0.000	0.000	1.000	90		0.000	E	50					0000	02.12.2015	Z1	WL5	0.000	0.000		00	
  ```
  Artinya: Material V874062 disimpan di lokasi WL5

## Kaitan Antar File

### Alur Kerja Simulasi:

1. **Schedule → BOM**: 
   - Schedule menentukan VGF4240 harus diproduksi 30 unit
   - BOM menentukan VGF4240 membutuhkan: V874062, VCQ0160, VGF1770, VGQ6490

2. **BOM → MRP**:
   - BOM menentukan komponen yang dibutuhkan (V874062, VCQ0160, dll)
   - MRP menentukan lokasi penyimpanan komponen tersebut (WL5, dll)

3. **Simulasi Terintegrasi**:
   - Production Simulation membaca Schedule dan BOM
   - Ketika produksi membutuhkan material, sistem meminta ke Logistics
   - Logistics Simulation membaca MRP untuk mengetahui lokasi material
   - Transport unit mengambil material dari lokasi dan mengirim ke proses produksi

## Contoh Konkret

### Produksi VGF4240 (30 unit):

1. **Dari Schedule**: VGF4240 harus diproduksi 30 unit
2. **Dari BOM**: Setiap VGF4240 membutuhkan:
   - 1x V874062 (HEADPHONE HANGER SET)
   - 1x VCQ0160 (SCREW SET)
   - 1x VGF1770 (RECYCLE LABEL)
   - 1x VGQ6490 (komponen lain)
3. **Dari MRP**: 
   - V874062 tersimpan di lokasi WL5
   - VCQ0160 tersimpan di lokasi WL5
   - VGF1770 tersimpan di lokasi S05
4. **Simulasi**: 
   - Production meminta 30x V874062, 30x VCQ0160, 30x VGF1770, 30x VGQ6490
   - Logistics mengirim transport unit ke WL5 dan S05
   - Material dikirim ke proses Assembly
   - Produksi VGF4240 dimulai

## Masalah yang Ditemukan

1. **Part Number Mismatch**: 
   - Schedule menggunakan VGF4340, VGF4390, VGF4240
   - BOM memiliki VGF4240 tapi tidak ada VGF4340, VGF4390
   - Ini menyebabkan simulasi tidak bisa menemukan BOM untuk beberapa part

2. **Lokasi Storage**:
   - MRP menunjukkan lokasi seperti WL5, S05, SM01
   - Tapi setup logistics menggunakan lokasi seperti WAREHOUSE, Assembly
   - Perlu mapping antara lokasi MRP dan lokasi simulasi

## Rekomendasi Perbaikan

1. **Sinkronisasi Part Number**: Pastikan semua part di Schedule ada di BOM
2. **Mapping Lokasi**: Buat mapping antara lokasi MRP dan lokasi simulasi
3. **Validasi Data**: Tambahkan validasi untuk memastikan konsistensi data
4. **Error Handling**: Tambahkan handling untuk part yang tidak ditemukan

## Kesimpulan

File-file ini saling terkait dalam alur produksi:
- **Schedule** → Apa yang diproduksi
- **BOM** → Komponen apa yang dibutuhkan  
- **MRP** → Di mana komponen disimpan

Simulasi terintegrasi menggunakan ketiga file ini untuk mensimulasikan alur produksi yang realistis dengan transportasi material yang sesuai dengan data aktual perusahaan.
