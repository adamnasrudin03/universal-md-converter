import os
import re
import argparse
import json
import sys

def _safe_truncate(text, max_chars):
    """Truncate text to max_chars without breaking multi-byte UTF-8 characters."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(' ')
    if last_space > max_chars * 0.8:
        return truncated[:last_space]
    return truncated

try:
    import ollama
except ImportError:
    print("Error: Package 'ollama' belum ter-install. Silakan jalankan 'pip install ollama'.")
    sys.exit(1)

from validate_output import validate_file

def extract_raw_content(file_path):
    """
    Ekstrak metadata dan teks mentah dari file markdown yang gagal.
    Format default dari main.py adalah:
    # [title]
    
    **Source Type:** ...
    **Source Path/URL:** ...
    **Converted At:** ...
    
    ---
    [raw_content]
    ---
    *Converted using Universal MD Converter*
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    # Regex untuk memisahkan metadata dan konten utama
    # Menggunakan batasan fleksibel agar tidak patah karena spasi
    parts = re.split(r'\n+\s*---\s*\n+', content)
    
    if len(parts) >= 3:
        metadata = parts[0]
        raw_text = "\n\n---\n\n".join(parts[1:-1]).strip()
        footer = parts[-1]
        return metadata, raw_text, footer
    elif len(parts) == 2:
        metadata = parts[0]
        raw_text = parts[1].replace("*Converted using Universal MD Converter*", "").strip()
        footer = "*Converted using Universal MD Converter*"
        return metadata, raw_text, footer
    else:
        # Fallback jika struktur tidak standard
        return "", content, ""

def process_with_ai(raw_text, model_name='llama3'):
    """
    Menggunakan Ollama untuk merestrukturisasi raw_text menjadi format JSON RAG.
    Logic ini disamakan dengan chunking.py
    """
    prompt_template = """
Anda adalah asisten AI profesional spesialis ekstraksi informasi dan knowledge management.
Tugas Anda adalah mengekstrak, merangkum, dan merestrukturisasi potongan teks berikut menjadi 'Knowledge Summary' yang sangat terstruktur, komprehensif, namun mudah dibaca baik oleh manusia maupun AI.
Hasil ekstraksi ini akan digunakan sebagai basis data untuk sistem Retrieval-Augmented Generation (RAG).

KHUSUS JIKA TEKS BERKAITAN DENGAN SAHAM/TRADING: 
Pastikan hasil ekstraksi Anda dioptimalkan (melalui Header Dinamis) untuk keperluan berikut:
1. Tanya Jawab (RAG)
2. Membuat Scanner Saham
3. Membuat Alert Trading
4. Bahan Analisa Saham
5. Checklist Trading
6. Jurnal Evaluasi Trading

Format jawaban Anda HANYA dalam bentuk JSON valid tanpa teks tambahan di luar JSON.

Struktur JSON yang diharapkan:
{{
  "filename_slug": "kata-kunci-pendek-maks-3-kata",
  "tags": ["tag1", "tag2"],
  "rag_content": "## 🧠 Core Summary\\n[Ringkasan inti yang padat dan komprehensif dari materi ini...]\\n\\n## 💡 Key Concepts & Definitions\\n[Penjelasan konsep utama, teori, istilah, atau ide dasar...]\\n\\n## 📌 Important Details / Application\\n[Rincian penting, studi kasus, pedoman, atau penerapan praktis dari materi...]\\n\\n## [TAMBAHKAN 1 ATAU 2 HEADER DINAMIS SESUAI KONTEKS, misal: 💻 Code Snippets, 🥘 Ingredients, 📈 Trading Setup, ⏳ Timeline, dll]\\n[Isi dari header dinamis tersebut...]\\n\\n## 📝 Original Context & Quotes\\n[Kutipan penting, pesan moral, atau konteks asli dari sumber...]"
}}

Teks mentah:
{text_chunk}
"""
    prompt = prompt_template.replace("{text_chunk}", _safe_truncate(raw_text, 3000))
    
    try:
        response = ollama.chat(model=model_name, messages=[
            {'role': 'user', 'content': prompt}
        ], format='json')
        
        # Handle both dict and object-style responses from ollama-python
        if isinstance(response, dict):
            response_text = response.get('message', {}).get('content', '')
        else:
            msg = getattr(response, 'message', None)
            response_text = getattr(msg, 'content', '') if msg else ''
        try:
            parsed_json = json.loads(response_text)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                try:
                    parsed_json = json.loads(json_match.group(0))
                except json.JSONDecodeError:
                    print("Error: Regex matched but still not valid JSON")
                    return None
            else:
                print("Error: Valid JSON not found in LLM response")
                return None
        
        # Extract content
        rag_content = parsed_json.get("rag_content", "")
        tags_list = parsed_json.get("tags", [])
        
        if tags_list and isinstance(tags_list, list):
            tags_str = "\n".join([f"#{t}" for t in tags_list]) + "\n\n"
            rag_content = tags_str + rag_content
            
        return rag_content
    except Exception as e:
        print(f"Error during AI processing: {str(e)}")
        return None

def reconvert_directory(directory, use_llm_validation=False, model_name='llama3', max_retries=2):
    """Mencari file yang gagal validasi dan melakukan reconvert dengan auto-retry."""
    print(f"🔍 Mencari file yang butuh direconvert di {directory}...\n")
    
    files_to_reconvert = []
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                # Cetak progress agar user tau sedang memproses file apa
                print(f"  > Mengecek {file} ... ", end="", flush=True)
                
                # Validasi file
                res = validate_file(file_path, use_llm_validation, model_name)
                
                if res['status'] == "NEEDS RECONVERT":
                    print("❌ BUTUH RECONVERT")
                    files_to_reconvert.append((file_path, res))
                else:
                    print(f"✅ OK ({res['score']}/100)")
                    
    if not files_to_reconvert:
        print("✅ Tidak ada file yang butuh di-reconvert. Semuanya OK!")
        return
        
    print(f"⚠️ Ditemukan {len(files_to_reconvert)} file yang gagal validasi.")
    
    for idx, (file_path, validation_res) in enumerate(files_to_reconvert):
        print(f"\n[{idx+1}/{len(files_to_reconvert)}] Memproses ulang: {os.path.basename(file_path)}")
        
        for attempt in range(max_retries):
            if attempt > 0:
                print(f"  🔄 Retrying... (Attempt {attempt+1}/{max_retries})")
            
            print(f"  Feedback error sebelumnya:")
            for fb in validation_res['feedback']:
                print(f"    - {fb}")
                
            # 1. Ekstrak teks asli
            metadata, raw_text, footer = extract_raw_content(file_path)
            
            if not raw_text.strip():
                print("  ❌ Gagal ekstrak raw_text (kosong). Skip.")
                break
                
            # 2. Proses ulang menggunakan AI
            print(f"  ⏳ Memanggil Ollama ({model_name}) untuk convert ulang...")
            new_rag_content = process_with_ai(raw_text, model_name)
            
            if new_rag_content:
                # 3. Tulis ulang file
                new_file_content = f"{metadata}\n\n---\n\n{new_rag_content}\n\n---\n\n{footer}"
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_file_content)
                print("  ✅ Berhasil ditulis. Memvalidasi ulang secara otomatis...")
                
                # 4. Validasi Ulang
                validation_res = validate_file(file_path, use_llm_validation, model_name)
                if validation_res['status'] == "OK":
                    print(f"  🎉 Validasi sukses! Score: {validation_res['score']}/100")
                    break
                else:
                    print(f"  ❌ Validasi ulang masih gagal. Score: {validation_res['score']}/100")
                    if attempt == max_retries - 1:
                        print("  ⚠️ Gagal mencapai status OK setelah batas maksimal retry.")
            else:
                print("  ❌ Gagal reconvert (LLM return None).")
                break

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Mencari file yang gagal divalidasi dan meng-convert ulangnya dengan AI.")
    parser.add_argument("path", help="Path direktori output (contoh: output_notes/)")
    parser.add_argument("--llm-validate", action="store_true", help="Gunakan mode LLM untuk mencari file yang gagal")
    parser.add_argument("--model", default="llama3", help="Model Ollama yang digunakan (default: llama3)")
    parser.add_argument("--retries", type=int, default=2, help="Jumlah maksimal percobaan reconvert jika masih gagal (default: 2)")
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.path):
        print(f"Error: {args.path} bukan direktori yang valid.")
        exit(1)
        
    reconvert_directory(args.path, args.llm_validate, args.model, args.retries)
