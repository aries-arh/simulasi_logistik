# 🏭 Production & Logistics Simulator - UI Documentation

## Overview
Sistem UI modern untuk Production & Logistics Simulator yang dibangun dengan React dan Bootstrap. UI ini menyediakan antarmuka yang intuitif dan responsif untuk mengelola simulasi produksi dan logistik.

## 🎨 Fitur UI

### 1. **Dashboard Utama**
- **Tampilan Modern**: Gradient background dengan glassmorphism effect
- **Kartu Interaktif**: 4 kartu utama dengan hover effects dan animasi
- **Ikon Font Awesome**: Ikon yang konsisten untuk setiap fitur
- **Responsive Design**: Optimal di desktop, tablet, dan mobile

### 2. **Komponen Utama**

#### **Dashboard Sistem**
- Real-time status monitoring
- Statistik sistem (Total Simulasi, Simulasi Aktif, dll.)
- Status Produksi dan Logistik terpisah
- Quick actions untuk akses cepat

#### **Simulasi Terintegrasi**
- Pilihan setup produksi dan logistik
- Status monitoring real-time
- Progress tracking dengan visual indicators
- Auto-refresh setiap 2 detik

#### **Simulasi Produksi**
- Progress bar animasi
- Status lini produksi per proses
- Grafik real-time dengan Chart.js
- WIP (Work-in-Progress) tracking

### 3. **Styling Modern**

#### **Color Scheme**
- Primary: Gradient biru-ungu (#667eea → #764ba2)
- Success: Gradient hijau (#56ab2f → #a8e6cf)
- Info: Gradient biru (#4facfe → #00f2fe)
- Warning: Gradient orange (#f39c12 → #e67e22)
- Danger: Gradient merah (#ff6b6b → #ee5a52)

#### **Komponen Styling**
- **Cards**: Rounded corners (15px), shadow effects, hover animations
- **Buttons**: Gradient backgrounds, rounded (25px), hover effects
- **Progress Bars**: Modern styling dengan gradient
- **Metrics**: Large numbers dengan labels yang jelas

#### **Animations**
- Hover effects pada cards dan buttons
- Loading spinners dengan 3 ukuran
- Smooth transitions (0.3s ease)
- Shimmer effect pada buttons

### 4. **Responsive Design**
- **Mobile First**: Optimized untuk mobile devices
- **Breakpoints**: 
  - xs: <576px
  - sm: ≥576px
  - md: ≥768px
  - lg: ≥992px
  - xl: ≥1200px

### 5. **User Experience**
- **Loading States**: Spinner dengan text yang informatif
- **Error Handling**: Alert cards dengan styling modern
- **Navigation**: Breadcrumb dan back buttons yang konsisten
- **Feedback**: Visual feedback untuk semua interaksi

## 🚀 Cara Menjalankan UI

### Prerequisites
- Node.js 14+ 
- npm atau yarn
- Backend API running di port 8000

### Installation
```bash
cd frontend
npm install
npm start
```

### Build untuk Production
```bash
npm run build
```

## 📁 Struktur File

```
frontend/src/
├── components/
│   ├── App.js                 # Main application component
│   ├── Dashboard.js           # System dashboard
│   ├── IntegratedSimulationView.js  # Integrated simulation
│   ├── ProductionSimulationDisplay.js  # Production display
│   ├── LoadingSpinner.js      # Reusable loading component
│   └── ...                    # Other components
├── App.css                    # Main styling
├── index.js                   # Entry point
└── public/
    └── index.html             # HTML template
```

## 🎯 Fitur Utama

### 1. **Dashboard**
- Monitoring status sistem real-time
- Statistik performa
- Quick actions

### 2. **Simulasi Produksi**
- Konfigurasi lini produksi
- Real-time monitoring
- Grafik performa
- WIP tracking

### 3. **Simulasi Logistik**
- Manajemen transport
- Inventory tracking
- Task management

### 4. **Simulasi Terintegrasi**
- Kombinasi produksi + logistik
- Cross-system monitoring
- Holistic analysis

### 5. **Manajemen Data**
- Master data management
- Scenario management
- Configuration storage

## 🔧 Customization

### Mengubah Warna
Edit file `App.css` dan ubah CSS variables:
```css
:root {
  --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  --success-gradient: linear-gradient(135deg, #56ab2f 0%, #a8e6cf 100%);
  /* ... */
}
```

### Menambah Komponen
1. Buat file di `src/components/`
2. Import di `App.js`
3. Tambahkan ke routing logic

### Styling Custom
- Gunakan class `simulation-card` untuk cards
- Gunakan class `btn-modern` untuk buttons
- Gunakan class `metric-card` untuk metrics

## 📱 Browser Support
- Chrome 80+
- Firefox 75+
- Safari 13+
- Edge 80+

## 🐛 Troubleshooting

### Common Issues
1. **API Connection Error**: Pastikan backend running di port 8000
2. **Icons tidak muncul**: Pastikan Font Awesome CDN loaded
3. **Charts tidak muncul**: Pastikan Chart.js dependencies installed

### Debug Mode
```bash
REACT_APP_DEBUG=true npm start
```

## 📈 Performance
- Lazy loading untuk komponen besar
- Memoization untuk expensive calculations
- Optimized re-renders
- Efficient API polling

## 🔒 Security
- Input validation
- XSS protection
- CSRF protection via API headers
- Secure API communication

---

**Dibuat dengan ❤️ untuk Production & Logistics Simulator**
