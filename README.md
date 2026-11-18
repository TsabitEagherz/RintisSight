# RintisSight

Prototipe web pendamping UMKM berbasis Flask. Fitur: landing page, asesmen ide, dashboard analitik enam grafik, pencatatan dan impor/ekspor CSV, simulator BEP, konsultan Gemini dengan fallback demo, serta pratinjau label produk.

## Menjalankan di Windows PowerShell

Jalankan dari folder proyek:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

Buka `http://127.0.0.1:5000` di browser. Jika PowerShell menolak aktivasi environment, jalankan perintah berikut untuk terminal saat ini, lalu ulangi aktivasi:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Mengaktifkan Gemini

1. Buat atau salin API key di [Google AI Studio](https://aistudio.google.com/app/apikey).
2. Di terminal PowerShell yang sama, atur key dan jalankan aplikasi:

   ```powershell
   $env:GEMINI_API_KEY = "tempel-api-key-di-sini"
   python app.py
   ```

3. Buka menu **Konsultan AI**. Tanpa key atau bila API tidak tersedia, konsultan memakai jawaban demo.

Kode memakai model `gemini-3.8-flash` secara default. Model dapat diganti lewat variabel `GEMINI_MODEL`. API key tidak disimpan di source code atau database. `$env:` berlaku hanya untuk terminal yang sedang terbuka; jangan pernah unggah atau bagikan key. SDK Gemini yang digunakan adalah paket resmi `google-genai`.

Untuk penggunaan yang lebih aman di luar komputer lokal, tetapkan `FLASK_SECRET_KEY` dengan nilai acak panjang sebelum menjalankan aplikasi. Jangan aktifkan `FLASK_DEBUG` di server publik.

## Data

Database `rintissight.db` dibuat otomatis pada saat pertama dijalankan. Data awal merupakan data sintetis 30 hari untuk demonstrasi; catatan dan impor transaksi disimpan di database yang sama.
