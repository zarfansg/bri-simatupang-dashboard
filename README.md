# BRI KC Jakarta TB Simatupang — Performance Dashboard MVP
### Dashboard Pemantauan Kinerja Bisnis Lending & Funding (Branch Code: 443)

Aplikasi dashboard analitik berbasis web untuk memantau performa portofolio bisnis **Bank BRI Kantor Cabang (KC) Jakarta TB Simatupang** dan unit kerja supervisinya berdasarkan file laporan portofolio perbankan internal.

---

## 📌 Ringkasan Eksekutif & Tujuan

Dashboard ini dirancang untuk kebutuhan manajemen cabang (*Branch Office Leader*, *Manager Bisnis*, *Relationship Manager*) guna:
1. **Memantau Posisi Portofolio:** Mengetahui baki debet pinjaman (*Lending*) dan saldo simpanan (*Funding/DPK*) per tanggal cut-off pelaporan.
2. **Segmentasi Kredit Akurat:** Mengelompokkan pinjaman secara otomatis ke dalam segmen **Small** (Komersial/SME), **Consumer** (Briguna, KPR, dsb.), dan **Micro** berdasarkan master klasifikasi resmi (`Loan Type California.xlsx`).
3. **Analisis Kualitas Aset (NPL):** Memetakan rasio NPL (*Non-Performing Loans* - Kol 3, 4, 5) per segmen pinjaman dan per unit kerja.
4. **Struktur Pendanaan (CASA vs Non-CASA):** Mengukur rasio dana murah (Giro + Tabungan) terhadap Deposito berjangka.
5. **Rekonsiliasi & Kualitas Data:** Memastikan angka yang disajikan 100% cocok (*reconciled*) dengan data mentah (*raw reports*), termasuk deteksi anomali rekening atau segmen belum teridentifikasi.

---

## 🏢 Struktur Organisasi & Pemetaan Unit Kerja

Data mencakup seluruh portofolio dalam binaan **KC Jakarta TB Simatupang (443)** dengan hirarki:

| Kode Unit | Nama Unit Kerja | Tipe Unit | Keterangan Supervisi |
|---|---|---|---|
| **443** | **KC Jakarta TB Simatupang** | Kantor Cabang (Induk) | Mengelola portofolio Kanca & Kantor Kas binaan |
| **1506** | **KCP PHE TOWER** | KCP | Kantor Cabang Pembantu tersupervisi |
| **2075** | **KCP RANCHO** | KCP | Kantor Cabang Pembantu tersupervisi |
| **1237** | KK Wisma Raharja | Kantor Kas | Berada di bawah supervisi KC 443 |
| **1410** | KK Lenteng Agung Raya | Kantor Kas | Berada di bawah supervisi KC 443 |
| **1425** | KK Margasatwa | Kantor Kas | Berada di bawah supervisi KC 443 |
| **1657** | KK Poli Media | Kantor Kas | Berada di bawah supervisi KC 443 |

### Filter Organisasi pada Dashboard:
- **Konsolidasi:** Menggabungkan seluruh data KC 443, KCP PHE Tower (1506), KCP Rancho (2075), dan Kantor Kas binaan.
- **KC Only:** Portofolio KC 443 (termasuk KK binaan yang terbukukan di Kanca).
- **KCP PHE TOWER (1506):** Khusus portofolio terbukukan di KCP PHE Tower.
- **KCP RANCHO (2075):** Khusus portofolio terbukukan di KCP Rancho.

---

## 📂 Sumber Data (*Raw Excel Workbooks*)

Aplikasi membaca data mentah dari direktori:  
`D:\[1] Work\[5] BRI\California\Portfolio Cabang\`

| Nama File | Modul / Jenis Data | Deskripsi & Isi Data |
|---|---|---|
| `LW321 (1).xlsx` | **Lending (Pinjaman)** | Data detail pinjaman debitur (Baki Debet, Plafon, Kol, Loan Type, No Rekening, Nama Debitur). |
| `Loan Type California.xlsx` | **Loan Master** | Master pemetaan jenis kredit resmi BRI untuk menentukan segmen (*Small*, *Consumer*, *Micro*). |
| `DI321.xlsx` | **Funding — Giro** | Laporan rekening giro nasabah korporasi/perorangan beserta saldo akhir. |
| `CI324_MULTI_PN_202309.xlsx` | **Funding — Deposito** | Data deposito berjangka (Time Deposit) nasabah beserta suku bunga dan nominal. |
| `DI319_MULTI_PN_202309.xlsx` | **Funding — Tabungan** | Data rekening tabungan nasabah mikro/ritel dan saldo akhir. |

> **Catatan Validitas:** File `KINERJA KONSOLIDASI 29 SEPTEMBER 2026.xlsx` adalah buku referensi internal KC Pondok Gede dan **hanya dipakai sebagai acuan formula/format pelaporan**, bukan sebagai sumber angka KC TB Simatupang.

---

## 📐 Definisi Metrik & Logika Kalkulasi

### 1. Lending (Pinjaman)
- **Total Outstanding (OS):**  
  $$\text{Total OS} = \sum \text{Baki Debet}$$
- **Total Plafon Kredit:**  
  $$\text{Total Plafon} = \sum \text{Plafond}$$
- **Rasio Utilisasi Plafon:**  
  $$\text{Utilisasi} = \frac{\text{Total OS}}{\text{Total Plafon}} \times 100\%$$
- **Klasifikasi Kolektibilitas (Kolek):**
  - **Lancar:** Kolek 1
  - **Dalam Perhatian Khusus (DPK):** Kolek 2
  - **Non-Performing Loan (NPL):** Kolek 3 (Kurang Lancar), Kolek 4 (Diragukan), Kolek 5 (Macet)
- **NPL Ratio:**  
  $$\text{NPL Ratio} = \frac{\sum \text{OS (Kolek 3 + 4 + 5)}}{\text{Total OS}} \times 100\%$$
- **Segmentasi Kredit:**  
  Menggunakan penggabungan `TYPE` pinjaman dengan tabel acuan `Loan Type California.xlsx`:
  - *Small:* Kredit modal kerja/investasi komersial UKM.
  - *Consumer:* Kredit konsumtif pegawai/payroll (Briguna), KPR, KKB.
  - *Micro:* Pinjaman skala mikro (Kupedes/KUR mikro jika ada).

### 2. Funding (Simpanan / DPK)
- **Total DPK (Dana Pihak Ketiga):**  
  $$\text{Total DPK} = \text{Total Giro} + \text{Total Tabungan} + \text{Total Deposito}$$
- **CASA (Current Account & Savings Account):**  
  $$\text{Total CASA} = \text{Total Giro} + \text{Total Tabungan}$$
- **CASA Ratio (Rasio Dana Murah):**  
  $$\text{CASA Ratio} = \frac{\text{Total CASA}}{\text{Total DPK}} \times 100\%$$
- **Non-CASA (Time Deposit):**  
  $$\text{Non-CASA Ratio} = \frac{\text{Total Deposito}}{\text{Total DPK}} \times 100\%$$

---

## 🏗️ Arsitektur & Struktur Kode

Aplikasi dibangun dengan Python, Streamlit, Pandas, dan Plotly dengan arsitektur modular:

```text
d:\[1] Work\[5] BRI\dashboard\
├── data_loader.py              # Engine pembaca Excel, pembersih data, normalisasi, & caching Parquet
├── metrics.py                  # Mesin hitung KPI Lending, Funding, matriks unit kerja, dan agregasi
├── styles.py                   # Design system bertema perbankan BRI (warna resmi, card KPI, styling CSS)
├── app.py                      # Aplikasi dashboard Streamlit interaktif multi-halaman
├── test_dashboard_pipeline.py  # Test suite unittest pengujian integritas numerik & rekonsiliasi
├── run.bat                     # Windows batch launcher 1-klik untuk menjalankan dashboard
└── README.md                   # Dokumentasi teknis & panduan lengkap (file ini)
```

### Penjelasan Modul:
1. **`data_loader.py`**:
   - Deteksi header otomatis pada file Excel raw BRI (yang seringkali tidak berada di baris pertama).
   - Penggabungan data kredit dengan tabel *Loan Type Master* untuk segmen bisnis.
   - Fitur *Parquet Caching* pada folder `.cache/` untuk loading super cepat (sub-detik) setelah pembacaan pertama.
   - Fungsi formatting Rupiah pintar (format ringkas: `Rp1,2 Triliun`, `Rp588,3 Miliar`, atau format lengkap).
2. **`metrics.py`**:
   - Menghitung KPI Lending & Funding dengan handling nilai nol / missing values yang aman.
   - Pemetaan matriks performa lintas unit kerja (KC vs KCP vs KK).
3. **`styles.py`**:
   - Menerapkan palet resmi BRI: *BRI Blue* (`#00529C`), *BRI Blue Dark* (`#0A2540`), *BRI Orange* (`#F37021`).
   - Komponen visual kartu metrik responsif (*KPI Cards*) dengan indikator status.
4. **`app.py`**:
   - Navigasi menu 4 Halaman:
     - 📊 **Ringkasan (Overview):** Kartu metrik utama, komposisi aset & liabilitas, dan perbandingan performa unit kerja.
     - 💳 **Pinjaman (Lending):** Breakdown segmen Small vs Consumer, profil kolektibilitas, sebaran baki debet, dan daftar debitur terbesar (*Top Borrowers*).
     - 💰 **Simpanan (Funding):** Komposisi CASA vs Deposito, sebaran per unit kerja, dan daftar deposan/pemilik rekening utama.
     - 🔍 **Kualitas Data & Rekonsiliasi:** Audit integritas record, pengecekan baki debet bernilai 0/negatif, identifikasi pinjaman yang tidak terpetakan di master, dan tabel verifikasi silang total angka.
5. **`test_dashboard_pipeline.py`**:
   - Menguji pemuatan kelima file Excel tanpa kegagalan.
   - Memvalidasi total record kredit (1.020 baris pada LW321) dan pembagian segmennya.
   - Memastikan rasio dan angka rekonsiliasi konsisten antara raw data dan dashboard.

---

## 🚀 Petunjuk Menjalankan Dashboard

### Prasyarat Sistem
- **Sistem Operasi:** Windows 10 / 11
- **Python:** Versi 3.10 atau lebih tinggi
- **Library Python yang Dibutuhkan:**
  ```powershell
  pip install streamlit pandas numpy openpyxl pyarrow plotly
  ```

### Cara Menjalankan (Pilih salah satu):

#### Opsi 1: Menggunakan Launcher Batch (Paling Praktis)
Cukup lakukan **double-click** pada file:
👉 **`run.bat`** di dalam folder `dashboard`.

#### Opsi 2: Melalui Terminal PowerShell
1. Buka PowerShell dan arahkan ke folder dashboard:
   ```powershell
   cd "d:\[1] Work\[5] BRI\dashboard"
   ```
2. Jalankan Streamlit:
   ```powershell
   python -m streamlit run app.py
   ```
3. Browser akan otomatis terbuka dan menampilkan dashboard di:  
   👉 **`http://localhost:8501`**

---

## 🧪 Menjalankan Pengujian Otomatis (*Unit Test*)

Untuk memverifikasi akurasi angka, formula perhitungan, dan filter unit kerja sebelum dipakai dalam presentasi atau rapat pimpinan:

```powershell
cd "d:\[1] Work\[5] BRI\dashboard"
python -m unittest test_dashboard_pipeline.py -v
```

---

## 🔄 Pembaruan Data Berkala (*Data Refresh*)

Jika ada pembaruan file portofolio bulanan baru di folder `California/Portfolio Cabang/`:
1. Tempatkan file Excel laporan baru dengan nama yang bersesuaian di folder `California/Portfolio Cabang/`.
2. Buka dashboard di browser.
3. Di sidebar kiri, klik tombol **"🔄 Segarkan Data (Clear Cache)"**.
4. Aplikasi akan menghapus cache Parquet lama dan memproses ulang file Excel baru secara otomatis.
