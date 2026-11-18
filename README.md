# RintisSight

Prototipe pendamping dan analitik UMKM berbasis Streamlit: asesmen ide, workspace dengan simulasi 30 hari, pencatatan dan impor CSV, dashboard enam grafik, simulator BEP, konsultasi AI opsional, serta pratinjau label.

## Menjalankan

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Mengaktifkan Gemini

1. Pasang dependensi proyek: `pip install -r requirements.txt` (sudah mencakup paket resmi `google-genai`).
2. Buat API key Gemini di [Google AI Studio](https://aistudio.google.com/app/apikey).
3. Buka PowerShell di folder proyek dan tetapkan key untuk terminal yang sedang dipakai:

   ```powershell
   $env:GEMINI_API_KEY = "tempel-api-key-di-sini"
   ```

4. Dari terminal yang sama jalankan `streamlit run app.py`.
5. Buka menu **Konsultan AI**. Jika API key terbaca, aplikasi mengirim ringkasan profil usaha, omzet, laba, margin, serta pertanyaan pengguna ke Gemini. Jika key belum terpasang atau API gagal, aplikasi menggunakan jawaban demo.

Variabel `$env:` hanya berlaku selama terminal itu masih terbuka. Untuk pemakaian lebih tetap, atur `GEMINI_API_KEY` melalui Environment Variables Windows lalu buka terminal baru. Jangan menaruh API key di `app.py`, membagikannya, atau mengunggahnya ke Git.

SQLite `rintissight.db` dibuat otomatis. Data awal merupakan data sintetis untuk demonstrasi.
