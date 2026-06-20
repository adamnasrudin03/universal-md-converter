# Universal File-to-Markdown Converter

Proyek ini adalah konverter pintar berbasis Python yang mampu mengubah berbagai jenis format file dan link website menjadi *Atomic Notes* berformat Markdown (`.md`). Sistem ini terintegrasi dengan LLM lokal (Ollama) untuk merestrukturisasi catatan secara otomatis agar siap ditelan oleh sistem RAG (Retrieval-Augmented Generation) Trading Anda.

## Dukungan Format
- **PDF** (`.pdf`) - Teks diekstrak menggunakan `pdfplumber`.
- **Word** (`.docx`, `.doc`) - Diekstrak menggunakan `python-docx` (mempertahankan heading).
- **Gambar** (`.png`, `.jpg`, `.jpeg`) - Diekstrak menggunakan Tesseract OCR.
- **Video & Audio** (`.mp4`, `.mp3`, `.wav`, dll) - Ditranskripsi menjadi teks menggunakan OpenAI Whisper.
- **YouTube Video** (`youtube.com`, `youtu.be`) - Mengekstrak transkrip dari video YouTube (mendukung banyak bahasa dengan fallback otomatis).
- **Link Website** (`http/https`) - Diekstrak teks utamanya menggunakan BeautifulSoup dan diubah ke MD.
- **Link Instagram** (`instagram.com/p/...`) - Mendownload slide *carousel*, mengekstrak teks tiap gambarnya via OCR, dan menggabungkannya dengan *caption*.

## Prasyarat (Requirements)
Pastikan Anda memiliki hal-hal berikut terinstal di sistem Anda:
1. **Python 3.9+**
2. **Ollama** (Wajib untuk fitur pemotongan dan format RAG otomatis berbasis AI lokal)
   - *Cara Install:* Unduh aplikasinya di [https://ollama.com/download](https://ollama.com/download).
   - *(Script sudah dilengkapi fitur auto-download model, namun pastikan aplikasi Ollama Anda menyala di latar belakang saat script dijalankan).*
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
3. Jalankan script utama `main.py` melalui command line (CLI).

### Fitur Pintar Model AI (Auto-Detect RAM & Auto-Download)
Script ini secara otomatis mendeteksi spesifikasi RAM Mac/PC Anda:
- Jika RAM **>= 16GB**: Sistem otomatis memilih model `llama3` (lebih cerdas).
- Jika RAM **< 16GB**: Sistem otomatis memilih model `llama3.2` (lebih ringan dan cepat).

**Penting:** Jika model yang dipilih belum pernah diinstal di komputer Anda, script ini akan otomatis mendownloadnya dari server Ollama sebelum pemrosesan dimulai!
*(Versi terbaru script telah dilengkapi dengan berbagai optimasi RAM & CPU, seperti pembatasan ukuran konteks LLM, pembatasan multi-threading Tesseract OCR, dan *auto-resize* gambar besar agar terhindar dari hang atau CPU throttle saat ekstraksi bulk).*

### 1. Mengonversi Link Instagram atau Website
Gunakan tanda kutip ganda `""` untuk mengapit URL, terutama jika link mengandung parameter khusus (seperti `?` atau `&`), untuk mencegah *error* di terminal.

```bash
# Contoh untuk Instagram:
python src/main.py "https://www.instagram.com/p/DZucoBjiQxd/?utm_source=ig_web_button_share_sheet" -o outputs/notes_ig

# Contoh untuk Video YouTube:
python src/main.py "https://www.youtube.com/watch?v=jNQXAC9IVRw" -o outputs/notes_yt

# Contoh untuk Website Artikel:
python src/main.py "https://www.cnbc.com/trading-news/" -o outputs/notes_web
```

### 2. Mengonversi File Dokumen Lokal (PDF/DOCX) atau Batch Processing Folder
Anda dapat memproses satu file atau seluruh isi direktori/folder sekaligus. Script akan mencari semua file yang didukung jika Anda memberikan input folder.

```bash
# Satu file
python src/main.py "/path/ke/buku_trading.pdf" -o outputs/notes

# Seluruh direktori (Batch Processing)
python src/main.py "/path/ke/folder_dokumen/" -o outputs/notes
```

### 3. Mengonversi File Media Lokal (Video/Audio)
```bash
python src/main.py "/path/ke/rekaman_webinar.mp4" -o outputs/notes
```

### 4. Mengubah Model AI Secara Manual (Override)
Jika Anda tidak ingin menggunakan model auto-deteksi, Anda bisa memaksakan (override) penggunaan model tertentu menggunakan parameter `-m` atau `--model`.
```bash
python src/main.py "https://www.cnbc.com/trading-news/" -o outputs/notes -m qwen2.5:0.5b
```

### Format Output (RAG-Ready Multi-Domain)
Sistem akan memotong teks Anda (setiap ~600 kata), memprosesnya lewat Ollama (`llama3`/`llama3.2` dengan output streaming), dan menyimpannya di folder `outputs/notes/` sebagai **Atomic Notes**. Format ini dirancang khusus untuk RAG (Retrieval-Augmented Generation) di berbagai domain (seperti trading, pemrograman, kuliner, dll).

Setiap file akan memiliki nama unik berdasarkan *slug* deskriptif (3-5 kata kebab-case) dan berisi struktur konten berikut dengan **YAML Frontmatter**:
```yaml
---
source_type: "YouTube Video"
source_path: "https://www.youtube.com/watch?v=jNQXAC9IVRw"
tags: ["biologi", "fauna"]
converted_at: "2026-06-20 11:35:12"
---
```
- **Tags**: Tersedia di metadata YAML dan disanitasi otomatis.
- `## 🧠 Core Summary`: Paragraf ringkasan padat (3-5 kalimat) yang kaya kata kunci dan bersifat *self-contained* agar optimal saat diambil via semantic search.
- `## 💡 Key Concepts & Definitions` (Opsional): Daftar konsep, istilah kunci, atau ide dasar beserta definisi singkatnya dalam format bullet points.
- `## 📌 Important Details / Application` (Opsional): Rincian teknis, langkah-langkah, data kuantitatif, atau penerapan praktis.
- `## [HEADER DINAMIS]` (Maksimal 3): Header kontekstual sesuai dengan domain konten asli untuk menampung data substantif spesifik, contohnya:
  - **Trading**: `## 📈 Trading Setup & Criteria` atau `## 📊 Analisa Teknikal`
  - **Programming**: `## 💻 Code & Implementasi` atau `## 🏗️ Arsitektur Sistem`
  - **Kuliner**: `## 🥘 Bahan & Takaran` atau `## 👨‍🍳 Langkah Memasak`
- `## 📝 Original Context & Quotes` (Opsional): Kutipan langsung atau pesan kunci yang wajib dipertahankan kata per kata dari sumber aslinya.

## 🛠 Menggunakan Makefile (Shorthand)
Untuk mempermudah penggunaan tanpa harus selalu memanggil `venv` atau mengingat path, Anda bisa menggunakan perintah `make`:

```bash
# Setup Environment Pertama Kali
make setup

# Menggunakan 1 Perintah (Script Otomatis Menentukan Jenis File/Link)
# Contoh Konversi Instagram
make run INPUT="https://www.instagram.com/p/..."

# Contoh Konversi Website
make run INPUT="https://www.cnbc.com/..."

# Contoh Konversi File Lokal (Auto-Detect Model)
make run INPUT="/path/ke/buku.pdf"

# Contoh Jika Ingin Memilih Model Spesifik (Override)
make run INPUT="/path/ke/buku.pdf" MODEL="qwen2.5:0.5b"

# Jika Anda me-rename atau memindahkan file sumber, sinkronkan output Markdown-nya
make sync-path OLD="path/ke/file_lama.pdf" NEW="path/ke/file_baru.pdf"

# Menjalankan seluruh unit test
make test

# Hapus semua output sebelumnya
make clean
```

## 🕵️‍♂️ Pengujian (Unit Testing)
Proyek ini menggunakan `pytest` untuk *unit testing* dan menguji kestabilan setiap modul *converter*. Anda dapat menjalankan seluruh *test suite* secara mudah melalui *Makefile*:

```bash
make test
```
*Catatan: Proses testing dapat menghasilkan file laporan seperti `.coverage`.*

## 🧪 Validasi Output (Quality Control)
Sistem ini dilengkapi dengan `validate_output.py` untuk menilai apakah hasil ekstraksi sudah memenuhi standar format RAG atau perlu di-reconvert. Terdapat dua metode validasi:

**1. Validasi Cepat (Heuristic/Regex):**
Mengecek keberadaan judul/heading wajib, jumlah kata minimum, dan kesesuaian tag. Sangat cepat.
```bash
# Menggunakan Makefile (default ke outputs/notes/)
make validate

# Spesifik direktori
make validate DIR="outputs/notes_ig/"
```

**2. Validasi Mendalam (Ollama LLM):**
Menggunakan model AI lokal untuk menilai kualitas tulisan secara mendalam dengan pembagian skor total 100 poin:
- **Struktur (25 poin)**: Pemeriksaan bagian inti, penggunaan header dinamis yang wajar (maks. 3), dan penghilangan bagian kosong.
- **Kualitas RAG & Anti-Redundansi (30 poin)**: Kepadatan kata kunci di Core Summary, informasi padat, dan tidak mengulang definisi yang sama (*anti-redundancy*).
- **Formatting & Visualisasi (25 poin)**: Penggunaan *Markdown Table* untuk data statistik, *Numbered/Bullet List*, *bold* untuk kata kunci, dan menghindari *wall-of-text*.
- **Akurasi & Metadata (20 poin)**: Konsistensi faktual (menghindari halusinasi) serta keunikan slug/tag.
```bash
# Menggunakan Makefile (default ke outputs/notes/)
make validate-llm

# Spesifik direktori
make validate-llm DIR="outputs/notes_ig/"
```

## 🔄 Reconvert Otomatis
Jika proses validasi di atas menemukan file dengan status **NEEDS RECONVERT**, Anda bisa memproses ulang file tersebut secara otomatis. Sistem akan mengekstrak kembali teks aslinya (dari file `.raw.txt`) dan memanggil ulang Ollama untuk memperbaiki formatnya tanpa harus mengekstrak dokumen sumber dari awal. Sistem juga dilengkapi dengan fitur **auto-retry**, di mana file akan divalidasi ulang setelah proses reconvert dan jika masih gagal, akan diulang kembali (maksimal 2 kali percobaan).

```bash
# Mereconvert file yang gagal berdasarkan validasi cepat (Heuristic)
make reconvert

# Mereconvert file yang gagal berdasarkan validasi LLM (Lebih direkomendasikan)
make reconvert-llm

# Memaksa reconvert SEMUA file di dalam direktori tanpa melalui proses validasi
make force-reconvert DIR="outputs/notes/folder_anda/"
```

**💡 Tips Kustomisasi Validasi:**
Secara default, file yang mendapatkan skor di bawah 85 akan di-reconvert. Anda dapat memperketat seleksi ini dengan mengubah variabel lingkungan `MIN_SCORE`. Misalnya, jika Anda ingin memproses ulang semua file yang nilainya tidak sempurna (100):
```bash
MIN_SCORE=100 make reconvert-llm DIR="outputs/notes/folder_anda/"
```
