# Universal File-to-Markdown Converter

Proyek ini adalah konverter pintar berbasis Python yang mampu mengubah berbagai jenis format file dan link website menjadi *Atomic Notes* berformat Markdown (`.md`). Sistem ini terintegrasi dengan LLM lokal (Ollama) untuk merestrukturisasi catatan secara otomatis agar siap ditelan oleh sistem RAG (Retrieval-Augmented Generation) Trading Anda.

## Dukungan Format
- **PDF** (`.pdf`) - Teks diekstrak menggunakan `pdfplumber`.
- **Word** (`.docx`, `.doc`) - Diekstrak menggunakan `python-docx` (mempertahankan heading).
- **Gambar** (`.png`, `.jpg`, `.jpeg`) - Diekstrak menggunakan Tesseract OCR.
- **Video & Audio** (`.mp4`, `.mp3`, `.wav`, dll) - Ditranskripsi menjadi teks menggunakan OpenAI Whisper.
- **Link Website** (`http/https`) - Diekstrak teks utamanya menggunakan BeautifulSoup dan diubah ke MD.
- **Link Instagram** (`instagram.com/p/...`) - Mendownload slide *carousel*, mengekstrak teks tiap gambarnya via OCR, dan menggabungkannya dengan *caption*.

## Prasyarat (Requirements)
Pastikan Anda memiliki hal-hal berikut terinstal di sistem Anda:
1. **Python 3.9+**
2. **Ollama** (Wajib untuk fitur pemotongan dan format RAG otomatis berbasis AI lokal)
   - *Cara Install:* Unduh aplikasinya di [https://ollama.com/download](https://ollama.com/download).
   - *Model:* Setelah terinstal, wajib mengunduh model dengan membuka terminal dan menjalankan perintah: `ollama run llama3`.
3. **Tesseract OCR** (Untuk konversi gambar/slide IG): `brew install tesseract` (Mac) atau `apt-get install tesseract-ocr` (Linux).
   - *💡 Tips Ekstra: Agar Tesseract bisa membaca teks berbahasa Indonesia dengan jauh lebih akurat pada gambar/slide, sangat disarankan untuk menginstal paket bahasa Indonesianya: `brew install tesseract-lang` (Mac) atau `apt-get install tesseract-ocr-ind` (Linux).*
4. **FFmpeg** (Untuk pemrosesan audio/video dari Whisper): `brew install ffmpeg` (Mac) atau `apt-get install ffmpeg` (Linux).

## Cara Instalasi
```bash
# 1. Klon / masuk ke folder proyek
cd universal-md-converter

# 2. Buat virtual environment
python3 -m venv venv
source venv/bin/activate  # Untuk Mac/Linux

# 3. Instal dependensi Python
pip install -r requirements.txt
```

## Cara Penggunaan Optimal

Agar *formatting* berjalan dengan lancar menggunakan AI:
1. Pastikan aplikasi **Ollama sudah berjalan** di komputer Anda (biasanya ditandai dengan ikon Llama di menu bar atau system tray).
2. Aktifkan *virtual environment* Python Anda (`source venv/bin/activate`).
3. Jalankan script utama `main.py` melalui command line (CLI) dengan menyertakan target file/link dan folder output.

### 1. Mengonversi Link Instagram atau Website
Gunakan tanda kutip ganda `""` untuk mengapit URL, terutama jika link mengandung parameter khusus (seperti `?` atau `&`), untuk mencegah *error* di terminal.

```bash
# Contoh untuk Instagram:
python main.py "https://www.instagram.com/p/DZucoBjiQxd/?utm_source=ig_web_button_share_sheet" -o output_notes_ig

# Contoh untuk Website Artikel:
python main.py "https://www.cnbc.com/trading-news/" -o output_notes_web
```

### 2. Mengonversi File Dokumen Lokal (PDF/DOCX)
```bash
python main.py "/path/ke/buku_trading.pdf" -o output_notes
```

### 3. Mengonversi File Media Lokal (Video/Audio)
```bash
python main.py "/path/ke/rekaman_webinar.mp4" -o output_notes
```

### Format Output (RAG Trading)
Sistem akan memotong teks Anda (setiap ~600 kata), memprosesnya lewat Ollama (`llama3`), dan menyimpannya di folder `output_notes/` sebagai **Atomic Notes**. Format ini dioptimalkan agar mudah dibaca oleh manusia dan diolah oleh sistem AI lain.

Setiap file akan memiliki nama unik berdasarkan *slug* dan berisi:
- Metadata sumber & `#tags`
- `## 🧠 Summary Knowledge (RAG & Analisa)` - Ringkasan inti untuk tanya jawab.
- `## 💡 Key Concept` - Penjelasan teori utama.
- `## 🔍 Scanner & Alert Criteria` - Parameter teknikal/fundamental spesifik untuk membuat screener saham atau *trading alert*.
- `## ✅ Trading Checklist` - SOP dan langkah syarat sebelum *entry/exit*.
- `## 📓 Jurnal Evaluasi` - Poin penting untuk bahan evaluasi psikologi dan manajemen risiko ke depan.
- `## 📝 Original Context` - Kutipan asli dari sumber data.
