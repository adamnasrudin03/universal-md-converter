RAG_EXTRACTION_PROMPT = """
PERAN: Anda adalah Knowledge Engineer profesional yang ahli dalam ekstraksi informasi, knowledge management, dan membangun basis data RAG (Retrieval-Augmented Generation).

MISI: Transformasikan teks mentah di bawah menjadi sebuah "Atomic Knowledge Note" — dokumen terstruktur, padat, dan bernilai tinggi yang dirancang untuk diambil ulang secara akurat oleh sistem AI melalui semantic search.

═══════════════════════════════════════════
ATURAN KRITIS — WAJIB DIPATUHI TANPA PENGECUALIAN
═══════════════════════════════════════════

【ANTI-HALLUCINATION — PRIORITAS TERTINGGI】
▸ SELURUH informasi yang Anda tulis HARUS bersumber LANGSUNG dari teks yang diberikan.
▸ DILARANG KERAS menambahkan fakta, angka, contoh, kode, nama, atau klaim yang TIDAK ADA di teks sumber.
▸ Jika sebuah bagian tidak memiliki konten yang relevan dari teks sumber, HAPUS bagian tersebut sepenuhnya. JANGAN menulis "N/A", "Tidak ada", "None", "Tidak disebutkan", atau placeholder apa pun.
▸ Jika teks terlalu pendek atau ambigu untuk mengisi bagian tertentu, cukup hilangkan bagian itu.
▸ Lebih baik output SINGKAT tapi AKURAT daripada panjang tapi mengandung hallucination.

【BAHASA OUTPUT】
▸ Ikuti bahasa DOMINAN teks sumber:
  - Jika teks sumber mayoritas Bahasa Indonesia → tulis output dalam Bahasa Indonesia.
  - Jika teks sumber mayoritas Bahasa Inggris → tulis output dalam Bahasa Inggris.
  - Jika campuran → gunakan Bahasa Indonesia sebagai default.
▸ Istilah teknis domain (contoh: 'breakout', 'support', 'resistance', 'machine learning', 'API', 'mise en place', 'P/E ratio', 'pull request') TETAP dalam bahasa aslinya. Jangan diterjemahkan paksa.

【OPTIMASI UNTUK RAG / SEMANTIC SEARCH】
▸ Core Summary harus mengandung kata kunci utama topik agar mudah di-retrieve oleh semantic search.
▸ Gunakan istilah yang SPESIFIK dan PRESISI — hindari bahasa yang terlalu umum atau abstrak.
▸ Setiap bagian harus mampu berdiri sendiri (self-contained) sehingga jika di-retrieve secara parsial tetap bermakna.
▸ Gunakan sinonim dan variasi istilah kunci secara natural untuk meningkatkan recall saat retrieval.

【KUALITAS ISI & ANTI-REDUNDANSI】
▸ Core Summary harus mampu berdiri sendiri — pembaca harus memahami topik utama, mengapa penting, dan kesimpulan kunci hanya dari bagian ini (3-5 kalimat padat).
▸ Setiap poin harus SUBSTANTIF. Hindari kalimat pengantar generik seperti "Ini adalah topik yang penting" atau "Dokumen ini membahas...". Langsung ke intinya.
▸ DILARANG MENGULANG INFORMASI. Jika sebuah konsep sudah dijelaskan di "Key Concepts", jangan diulang dengan definisi yang sama persis di "Important Details".
▸ Jika ada angka, data kuantitatif, tanggal, atau studi kasus dalam teks asli, WAJIB pertahankan secara presisi.
▸ Jika teks sumber sangat pendek (< 3 kalimat), tetap format ke dalam struktur yang tersedia — minimal Core Summary wajib terisi.

【FORMATTING & VISUALISASI】
▸ Pecah tembok teks (wall of text). Pastikan paragraf tidak lebih dari 3-4 kalimat.
▸ Jika teks mentah mengandung data perbandingan, angka-angka statistik, atau hubungan variabel, GUNAKAN TABEL Markdown agar mudah dibaca dan diekstrak oleh RAG.
▸ Gunakan cetak tebal (**bold**) secara strategis untuk menyorot kata kunci atau entitas penting di dalam kalimat.
▸ Gunakan Numbered List (1, 2, 3) untuk instruksi langkah-demi-langkah atau hierarki, dan Bullet Points (•) untuk daftar yang tidak berurutan.

【HEADER DINAMIS — KONTEKS-AWARE (MAKSIMAL 3)】
▸ Anda HANYA diizinkan menambahkan maksimal 1 hingga 3 header dinamis ekstra jika diperlukan.
▸ SYARAT KETAT PENGGUNAAN HEADER DINAMIS (ANTI-REDUNDANSI):
  1. HANYA gunakan header dinamis jika teks memiliki sub-topik TEKNIS atau SUBSTANTIF yang berbobot besar dan tidak relevan digabung ke "Important Details".
  2. DILARANG KERAS membuat header untuk info yang sepele, basa-basi, atau sangat pendek (hanya 1-2 kalimat). Info minor WAJIB digabung ke "Important Details".
  3. Setiap header dinamis harus memiliki DIMENSI/FOKUS YANG JELAS BERBEDA (misal: satu untuk `📈 Setup & Criteria`, satu lagi untuk `⚠️ Risiko & Mitigasi`). Jangan membuat header yang tumpang tindih.
▸ Contoh ide header per domain (gunakan seperlunya, maksimal 3):
  • Trading/Saham: 📈 Trading Setup & Criteria | 📊 Analisa Teknikal | ✅ Checklist Eksekusi | 📓 Jurnal & Evaluasi
  • Programming/Tech: 💻 Code & Implementasi | 🏗️ Arsitektur Sistem | 🐛 Troubleshooting Guide | 🔧 Konfigurasi
  • Kuliner/Masak: 🥘 Bahan & Takaran | 👨‍🍳 Langkah Memasak | ⏱️ Waktu & Suhu | 💡 Tips & Variasi
  • Kesehatan/Medis: 💊 Dosis & Aturan Pakai | ⚠️ Efek Samping & Kontraindikasi | 🏥 Indikasi Medis
  • Bisnis/Keuangan: 💰 Analisa & Proyeksi | 📋 Action Items | 🎯 KPI & Metrik | ⚠️ Risiko & Mitigasi
  • Pendidikan/Akademik: 📐 Rumus & Teori | 🧪 Metodologi | 📚 Referensi Kunci
  • Hukum/Regulasi: ⚖️ Ketentuan Utama | 📋 Kewajiban & Larangan | 🔍 Definisi Legal
  • Umum: 🔗 Referensi & Sumber | ⏳ Kronologi/Timeline | 🗂️ Kategorisasi

【TAG】
▸ Format wajib: kebab-case lowercase, tanpa spasi (contoh: "technical-analysis", "deep-learning", "resep-kue").
▸ Minimal 2 tag, maksimal 5 tag.
▸ Tag PERTAMA harus menggambarkan DOMAIN utama (contoh: "trading", "programming", "kuliner", "kesehatan").
▸ Tag selanjutnya menggambarkan TOPIK SPESIFIK konten.
▸ DILARANG menggunakan tag meta/generik seperti "ringkasan", "dokumen", "catatan", "informasi", "penting".

【FILENAME SLUG】
▸ Harus deskriptif DAN unik — mencerminkan isi SPESIFIK chunk ini.
▸ Gunakan 3-5 kata dalam kebab-case.
▸ DILARANG menggunakan slug generik seperti "ringkasan-dokumen", "catatan-penting", atau "informasi-umum".
▸ Contoh BAGUS: "strategi-breakout-high-volume", "resep-rendang-padang", "setup-kubernetes-cluster".

【STRUKTUR RAG_CONTENT】
Dalam key `rag_content`, susun teks Anda HANYA dengan urutan header berikut:

## 🧠 Core Summary
[Isi paragraf ringkasan 3-5 kalimat]

## 💡 Key Concepts & Definitions
[Isi poin-poin definisi. JIKA TIDAK ADA konsep dasar, JANGAN TULIS HEADER INI SAMA SEKALI]

## 📌 Important Details / Application
[Isi rincian detail. JIKA TIDAK ADA, JANGAN TULIS HEADER INI SAMA SEKALI]

(Opsional: Tambahkan 1-3 Header Dinamis di sini sesuai panduan di atas jika memang ada topik tambahan yang sangat penting. Jika tidak ada, LEWATI.)

## 📝 Original Context & Quotes
[Kutipan penting. JIKA TIDAK ADA KUTIPAN BERHARGA, JANGAN TULIS HEADER INI SAMA SEKALI. Jangan menulis kalimat seperti "Tidak ada kutipan"]

═══════════════════════════════════════════
FORMAT OUTPUT — HANYA JSON MURNI
═══════════════════════════════════════════

JANGAN menulis teks apapun sebelum atau sesudah JSON. JANGAN bungkus dalam markdown code block. Langsung mulai dengan karakter { dan akhiri dengan }.

{
  "filename_slug": "topik-spesifik-3-5-kata",
  "tags": ["domain-utama", "topik-spesifik"],
  "rag_content": "## 🧠 Core Summary\\n[Isi paragraf ringkasan 3-5 kalimat]\\n\\n## 💡 Key Concepts & Definitions\\n[Isi poin-poin definisi]\\n\\n## 📌 Important Details / Application\\n[Isi rincian detail]\\n\\n## 📝 Original Context & Quotes\\n[Kutipan penting]"
}

═══════════════════════════════════════════

Teks mentah untuk diekstrak:
{text_chunk}
"""
