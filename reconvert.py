import os
import re
import argparse
import json
import sys

from utils.prompts import RAG_EXTRACTION_PROMPT
from utils.text_helpers import safe_truncate, get_recommended_model



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
        
    # Use targeted approach: find the FIRST and LAST `---` separator lines
    # to correctly isolate header, body, and footer. This avoids breaking
    # on internal `---` horizontal rules within the RAG content itself.
    separator = re.compile(r'^\s*---\s*$', re.MULTILINE)
    matches = list(separator.finditer(content))
    
    if len(matches) >= 2:
        first_sep = matches[0]
        last_sep = matches[-1]
        metadata = content[:first_sep.start()].rstrip()
        raw_text = content[first_sep.end():last_sep.start()].strip()
        footer = content[last_sep.end():].strip()
        return metadata, raw_text, footer
    elif len(matches) == 1:
        sep = matches[0]
        metadata = content[:sep.start()].rstrip()
        raw_text = content[sep.end():].replace("*Converted using Universal MD Converter*", "").strip()
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
    prompt = RAG_EXTRACTION_PROMPT.replace("{text_chunk}", safe_truncate(raw_text, 2500))
    
    try:
        response = ollama.chat(model=model_name, messages=[
            {'role': 'user', 'content': prompt}
        ], format='json', stream=True)
        
        response_text = ""
        for stream_chunk in response:
            # Handle both dict and object-style responses from ollama-python
            if isinstance(stream_chunk, dict):
                token = stream_chunk.get('message', {}).get('content', '')
            else:
                msg = getattr(stream_chunk, 'message', None)
                token = getattr(msg, 'content', '') if msg else ''
            if token:
                response_text += token
                print(token, end='', flush=True)
        print()  # newline after streaming
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
        
        # Extract content (guard against null from LLM)
        rag_content = parsed_json.get("rag_content", "") or ""
        
        # If the LLM returned a nested dict instead of a markdown string, convert it
        if isinstance(rag_content, dict):
            rag_parts = []
            for k, v in rag_content.items():
                if isinstance(v, str):
                    rag_parts.append(f"{k}\n{v}")
                else:
                    rag_parts.append(f"{k}\n{json.dumps(v, ensure_ascii=False)}")
            rag_content = "\n\n".join(rag_parts)
        elif not isinstance(rag_content, str):
            rag_content = str(rag_content)
            
        tags_list = parsed_json.get("tags", []) or []
        
        if tags_list and isinstance(tags_list, list):
            # Filter only valid string tags and sanitize to kebab-case
            valid_tags = []
            for t in tags_list:
                if t is not None:
                    t_str = re.sub(r'[^a-zA-Z0-9\s-]', '', str(t)).strip().lower()
                    t_str = re.sub(r'[\s]+', '-', t_str)
                    t_str = re.sub(r'-+', '-', t_str).strip('-')
                    if t_str:
                        valid_tags.append(t_str)
            if valid_tags:
                tags_str = "\n".join([f"#{t}" for t in valid_tags]) + "\n\n"
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
    parser.add_argument("--model", default="auto", help="Model Ollama yang digunakan (default: auto-detect berdasarkan RAM)")
    parser.add_argument("--retries", type=int, default=2, help="Jumlah maksimal percobaan reconvert jika masih gagal (default: 2)")
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.path):
        print(f"Error: {args.path} bukan direktori yang valid.")
        sys.exit(1)
    model = args.model
    if model == "auto":
        model = get_recommended_model()

    reconvert_directory(args.path, args.llm_validate, model, args.retries)
