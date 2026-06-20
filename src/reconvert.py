import os
import re
import argparse
import json
import sys

from utils.prompts import RAG_EXTRACTION_PROMPT
from utils.text_helpers import safe_truncate, get_recommended_model
from utils.markdown_formatter import generate_markdown
from utils.chunking import extract_global_context



try:
    import ollama
except ImportError:
    print("Error: Package 'ollama' belum ter-install. Silakan jalankan 'pip install ollama'.")
    sys.exit(1)

from validate_output import validate_file

def extract_raw_content(file_path):
    """
    Ekstrak metadata dan teks mentah dari file markdown yang gagal.
    Format menggunakan YAML frontmatter.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    separator = re.compile(r'^\s*---\s*$', re.MULTILINE)
    matches = list(separator.finditer(content))
    
    if len(matches) >= 3:
        # matches[0] = start of YAML
        # matches[1] = end of YAML
        # matches[-1] = start of footer
        metadata = content[:matches[1].end()]
        raw_text = content[matches[1].end():matches[-1].start()].strip()
        footer = content[matches[-1].start():].strip()
        return metadata, raw_text, footer
    elif len(matches) >= 2:
        # Legacy format fallback with ---
        first_sep = matches[0]
        last_sep = matches[-1]
        metadata = content[:first_sep.start()].rstrip()
        raw_text = content[first_sep.end():last_sep.start()].strip()
        footer = content[last_sep.end():].strip()
        return metadata, raw_text, footer
    else:
        # Fallback jika struktur tidak standard (e.g. no --- at all)
        m = re.search(r'(\*\*Source Type:\*\*.*?\*\*Converted At:\*\*.*?)\n\n', content, re.DOTALL)
        if m:
            metadata = content[:m.end()].strip()
            raw_text = content[m.end():].strip()
            if raw_text.endswith("*Converted using Universal MD Converter*"):
                footer = "*Converted using Universal MD Converter*"
                raw_text = raw_text[:-len(footer)].strip()
            else:
                footer = ""
        else:
            metadata = ""
            raw_text = content
            footer = ""
        return metadata, raw_text, footer

def process_with_ai(raw_text, model_name='llama3'):
    """
    Menggunakan Ollama untuk merestrukturisasi raw_text menjadi format JSON RAG.
    Logic ini disamakan dengan chunking.py
    """
    global_context = extract_global_context(raw_text, model_name)
    if global_context:
        global_context_block = f"\n[Konteks Global Dokumen: {global_context}]\n"
    else:
        global_context_block = ""
        
    prompt = RAG_EXTRACTION_PROMPT.replace("{global_context_block}", global_context_block).replace("{text_chunk}", safe_truncate(raw_text, 4000))
    
    try:
        response = ollama.chat(model=model_name, messages=[
            {'role': 'user', 'content': prompt}
        ], format='json', stream=True, options={'temperature': 0.0})
        
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
                    return None, []
            else:
                print("Error: Valid JSON not found in LLM response")
                return None, []
        
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
        valid_tags = []
        
        if tags_list and isinstance(tags_list, list):
            # Filter only valid string tags and sanitize to kebab-case
            for t in tags_list:
                if t is not None:
                    t_str = re.sub(r'[^a-zA-Z0-9\s-]', '', str(t)).strip().lower()
                    t_str = re.sub(r'[\s]+', '-', t_str)
                    t_str = re.sub(r'-+', '-', t_str).strip('-')
                    if t_str:
                        valid_tags.append(t_str)
            
        return rag_content, valid_tags
    except Exception as e:
        print(f"Error during AI processing: {str(e)}")
        return None, []

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
                    print(f"❌ BUTUH RECONVERT ({res['score']}/100)")
                    files_to_reconvert.append((file_path, res))
                elif res['status'] == "ERROR":
                    print(f"⚠️ ERROR VALIDASI ({res['score']}/100)")
                    # We can consider it as needing reconvert if it's completely broken
                    files_to_reconvert.append((file_path, res))
                else:
                    print(f"✅ OK ({res['score']}/100)")
                    
                if res.get('feedback'):
                    feedback_text = ' | '.join(res['feedback'])
                    print(f"    Alasan: {feedback_text}")
                    
    if not files_to_reconvert:
        print("✅ Tidak ada file yang butuh di-reconvert. Semuanya OK!")
        return
        
    print(f"⚠️ Ditemukan {len(files_to_reconvert)} file yang gagal validasi.")
    
    for idx, (file_path, validation_res) in enumerate(files_to_reconvert):
        print(f"\n[{idx+1}/{len(files_to_reconvert)}] Memproses ulang: {os.path.basename(file_path)}")
        
        # 1. Ekstrak teks asli HANYA pada percobaan pertama
        metadata, raw_text_from_md, footer = extract_raw_content(file_path)
        
        # Gunakan raw.txt jika tersedia (untuk menghindari halusinasi berantai)
        raw_filepath = f"{file_path}.raw.txt"
        if os.path.exists(raw_filepath):
            with open(raw_filepath, 'r', encoding='utf-8') as f:
                raw_text = f.read()
        else:
            raw_text = raw_text_from_md
            
        for attempt in range(max_retries):
            if attempt > 0:
                print(f"  🔄 Retrying... (Attempt {attempt+1}/{max_retries})")
            
            print(f"  Feedback error sebelumnya:")
            for fb in validation_res['feedback']:
                print(f"    - {fb}")
                
            if not raw_text.strip():
                print("  ❌ Gagal ekstrak raw_text (kosong). Skip.")
                break
                
            # 2. Proses ulang menggunakan AI
            print(f"  ⏳ Memanggil Ollama ({model_name}) untuk convert ulang...")
            new_rag_content, new_tags = process_with_ai(raw_text, model_name)
            
            if new_rag_content:
                # Ekstrak title untuk disisipkan kembali
                title = os.path.basename(file_path).replace('.md', '')
                
                # Parse metadata to extract source_type and source_path
                source_type = "Unknown"
                source_path = "Unknown"
                if metadata.startswith("---"):
                    # Match quoted YAML values: source_type: "value" or source_type: value
                    m_type = re.search(r'source_type:\s*"([^"]*)"', metadata)
                    if not m_type:
                        m_type = re.search(r'source_type:\s*(\S+)', metadata)
                    if m_type: source_type = m_type.group(1)
                    m_path = re.search(r'source_path:\s*"([^"]*)"', metadata)
                    if not m_path:
                        m_path = re.search(r'source_path:\s*(\S+)', metadata)
                    if m_path: source_path = m_path.group(1)
                else:
                    m_type = re.search(r'\*\*Source Type:\*\*\s*(.*)', metadata)
                    if m_type: source_type = m_type.group(1).strip()
                    m_path = re.search(r'\*\*Source Path/URL:\*\*\s*`?(.*?)`?\s*\n', metadata + '\n')
                    if m_path: source_path = m_path.group(1).strip()

                new_file_content = generate_markdown(
                    title=title,
                    content=new_rag_content,
                    source_type=source_type,
                    source_path_or_url=source_path,
                    tags=new_tags
                )
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_file_content)
                print("  ✅ Berhasil ditulis. Memvalidasi ulang secara otomatis...")
                
                # 4. Validasi Ulang
                validation_res = validate_file(file_path, use_llm_validation, model_name)
                if validation_res['status'] == "OK":
                    print(f"  🎉 Validasi sukses! Score: {validation_res['score']}/100")
                else:
                    print(f"  ❌ Validasi ulang masih gagal. Score: {validation_res['score']}/100")
                    
                if validation_res.get('feedback'):
                    print(f"    Alasan: {' | '.join(validation_res['feedback'])}")
                    
                if validation_res['status'] == "OK":
                    break
                else:
                    if attempt == max_retries - 1:
                        print("  ⚠️ Gagal mencapai status OK setelah batas maksimal retry.")
            else:
                print("  ❌ Gagal reconvert (LLM return None).")
                continue

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
