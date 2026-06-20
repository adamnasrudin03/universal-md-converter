import os
import re
import argparse
import json
import sys

from utils.prompts import RAG_EXTRACTION_PROMPT
from utils.text_helpers import safe_truncate, get_recommended_model, check_system_requirements
from utils.markdown_formatter import generate_markdown
from utils.chunking import extract_global_context



try:
    import ollama
except ImportError: # pragma: no cover
    print("Error: Package 'ollama' belum ter-install. Silakan jalankan 'pip install ollama'.")
    sys.exit(1)

from validate_output import validate_file, save_validation_report

def _yaml_unescape(value):
    if not value:
        return value
    value = value.strip()
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        value = value[1:-1]
    return value.replace('\\"', '"').replace("\\'", "'").replace('\\\\', '\\')

def extract_raw_content(file_path):
    """
    Ekstrak metadata dan teks mentah dari file markdown yang gagal.
    Format menggunakan YAML frontmatter secara robust (mengabaikan --- di dalam teks).
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return "", "", ""
        
    # First, securely remove the footer without relying on '---' count
    footer_text = "*Converted using Universal MD Converter*"
    if footer_text in content:
        footer_idx = content.rfind(footer_text)
        last_sep_idx = content.rfind("---", 0, footer_idx)
        # If there's a horizontal rule right before the footer, strip it
        if last_sep_idx != -1 and (footer_idx - last_sep_idx) < 10:
            content = content[:last_sep_idx].strip()
        else:
            content = content[:footer_idx].strip()
            
    separator = re.compile(r'^\s*---\s*$', re.MULTILINE)
    matches = list(separator.finditer(content))
    
    # Check for YAML frontmatter at the start
    if len(matches) >= 2 and matches[0].start() < 10:
        yaml_content = content[matches[0].end():matches[1].start()]
        # It's YAML frontmatter if there's actual text AFTER the second separator OR it contains standard YAML keys
        after_yaml = content[matches[1].end():].strip()
        if after_yaml or "source_type" in yaml_content:
            metadata = content[:matches[1].end()]
            raw_text = after_yaml
            return metadata, raw_text, ""
            
    # Legacy fallback for --- separators (metadata before first sep, content between first and last sep)
    if len(matches) >= 2:
        metadata = content[:matches[0].start()].strip()
        raw_text = content[matches[0].end():matches[-1].start()].strip()
        # Ensure we don't accidentally swallow the whole file if it was actually just frontmatter
        if metadata == "" and "source_type" in raw_text:
            return content, "", ""
        if "**source type:**" in metadata.lower() or "source_type" in metadata.lower():
            return metadata, raw_text, ""
    # Fallback jika struktur tidak standard (legacy format)
    m = re.search(r'(\*\*Source Type:\*\*.*?\*\*Converted At:\*\*.*?)\n\n', content, re.DOTALL)
    if m:
        metadata = content[:m.end()].strip()
        raw_text = content[m.end():].strip()
    else:
        metadata = ""
        raw_text = content.strip()
    return metadata, raw_text, ""

def process_with_ai(raw_text, model_name='llama3', temperature=0.0):
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
    
    schema = {
        "type": "object",
        "properties": {
            "filename_slug": {"type": "string"},
            "source_context": {"type": "string"},
            "rag_content": {"type": "string"},
            "tags": {"type": "array", "items": {"type": "string"}}
        },
        "required": ["filename_slug", "source_context", "rag_content", "tags"]
    }
    
    try:
        response = ollama.chat(
            model=model_name,
            messages=[{'role': 'user', 'content': prompt}],
            format=schema,
            stream=False,
            options={'temperature': temperature}
        )
        
        response_text = ""
        if not isinstance(response, (list, tuple)) and hasattr(response, '__iter__') and not isinstance(response, dict) and not hasattr(response, 'message'):
            # Handle streaming response (backwards compatibility or custom setups)
            for stream_chunk in response:
                if isinstance(stream_chunk, dict):
                    token = stream_chunk.get('message', {}).get('content', '')
                else:
                    msg = getattr(stream_chunk, 'message', None)
                    token = getattr(msg, 'content', '') if msg else ''
                if token:
                    response_text += token
        else:
            # Handle non-streaming response or mocked responses in unit tests
            if isinstance(response, list) and len(response) > 0:
                first_chunk = response[0]
                if isinstance(first_chunk, dict):
                    response_text = first_chunk.get('message', {}).get('content', '')
                else:
                    msg = getattr(first_chunk, 'message', None)
                    response_text = getattr(msg, 'content', '') if msg else ''
            elif isinstance(response, dict):
                response_text = response.get('message', {}).get('content', '')
            else:
                msg = getattr(response, 'message', None)
                response_text = getattr(msg, 'content', '') if msg else ''
        
        # Clean markdown code block syntax if LLM hallucinates it
        clean_response = re.sub(r'^```(?:json)?\n?', '', response_text.strip(), flags=re.IGNORECASE)
        clean_response = re.sub(r'\n?```$', '', clean_response).strip()
        
        try:
            parsed_json = json.loads(clean_response)
        except json.JSONDecodeError:
            json_match = re.search(r'\{.*\}', clean_response, re.DOTALL)
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
        
        if isinstance(rag_content, dict):
            rag_parts = []
            for k, v in rag_content.items():
                # Ensure Core Summary has the emoji if the LLM missed it
                if k.strip().lower() == "core summary":
                    k = "🧠 Core Summary"
                
                # Ensure it has the ## header prefix
                if not k.startswith("#"):
                    k = f"## {k}"
                    
                if isinstance(v, str):
                    rag_parts.append(f"{k}\n{v}")
                else: # pragma: no cover
                    rag_parts.append(f"{k}\n{json.dumps(v, ensure_ascii=False)}")
            rag_content = "\n\n".join(rag_parts)
        elif not isinstance(rag_content, str):
            rag_content = str(rag_content)
            
        tags_list = parsed_json.get("tags", []) or []
        valid_tags = []
        
        if tags_list:
            if not isinstance(tags_list, (list, str)):
                tags_list = [str(tags_list)]
            if isinstance(tags_list, str):
                tags_list = tags_list.split(',')
            if isinstance(tags_list, list):
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

def reconvert_directory(directory, use_llm_validation=False, model_name='llama3', max_retries=3, force=False):
    """Mencari file yang gagal validasi dan melakukan reconvert dengan auto-retry. Jika force=True, semua file di direktori akan diproses ulang tanpa validasi."""
    print(f"🔍 Mencari file yang butuh direconvert di {directory}...\n")
    if force:
        print("⚡ Mode FORCE aktif: Semua file akan direconvert tanpa proses validasi!")
    
    files_to_reconvert = []
    
    for root, dirs, files in os.walk(directory):
        # Load cache if available
        dir_cache = {}
        report_file = os.path.join(root, "validation_report.json")
        if not force and os.path.exists(report_file):
            try:
                with open(report_file, 'r', encoding='utf-8') as f:
                    dir_cache = json.load(f)
                print(f"📦 Ditemukan cache validasi di {root}")
            except Exception: # pragma: no cover
                pass

        for file in files:
            if file.startswith('.'):
                continue
            if file.endswith(".md"):
                file_path = os.path.join(root, file)
                # Cetak progress agar user tau sedang memproses file apa
                print(f"  > Mengecek {file} ... ", end="", flush=True)
                
                if force:
                    print("❌ BUTUH RECONVERT (Forced)")
                    files_to_reconvert.append((file_path, {"status": "NEEDS RECONVERT", "feedback": ["Forced reconvert"], "score": 0}))
                    continue
                
                # Gunakan cache jika mtime file MD lebih lama atau sama dengan mtime cache
                res = None
                if file in dir_cache:
                    try:
                        md_mtime = os.path.getmtime(file_path)
                        cache_entry_mtime = dir_cache[file].get("mtime", 0)
                        if cache_entry_mtime >= md_mtime:
                            res = dir_cache[file]
                            print("[CACHE] ", end="")
                    except Exception: # pragma: no cover
                        pass

                # Validasi file jika tidak ada di cache atau cache usang
                if not res:
                    res = validate_file(file_path, use_llm_validation, model_name)
                    save_validation_report(file_path, res)
                
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
        
    print(f"⚠️ Ditemukan {len(files_to_reconvert)} file untuk di-reconvert.")
    
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
            # Escalating temperature logic
            temp = 0.0 if attempt == 0 else (0.3 if attempt == 1 else 0.7)
            
            if attempt > 0:
                print(f"  🔄 Retrying... (Attempt {attempt+1}/{max_retries}) dengan temperature {temp}")
            
            print(f"  Feedback error sebelumnya:")
            feedback_list = validation_res.get('feedback', []) or []
            if isinstance(feedback_list, str):
                feedback_list = [feedback_list]
            elif not isinstance(feedback_list, list):
                try:
                    feedback_list = list(feedback_list)
                except Exception:
                    feedback_list = [str(feedback_list)]
            for fb in feedback_list:
                print(f"    - {fb}")
                
            if not raw_text.strip():
                print("  ❌ Gagal ekstrak raw_text (kosong). Skip.")
                break
                
            # 2. Proses ulang menggunakan AI
            print(f"  ⏳ Memanggil Ollama ({model_name}) untuk convert ulang...")
            new_rag_content, new_tags = process_with_ai(raw_text, model_name, temperature=temp)
            
            if new_rag_content:
                # Ekstrak title untuk disisipkan kembali
                title = os.path.basename(file_path)[:-3] if file_path.endswith('.md') else os.path.basename(file_path)
                
                # Parse metadata to extract source_type, source_path and source_context
                source_type = "Unknown"
                source_path = "Unknown"
                source_context = None
                if metadata.strip().startswith("---"):
                    m_type = re.search(r'^\s*source_type:\s*(.*)', metadata, re.MULTILINE)
                    if m_type: source_type = _yaml_unescape(m_type.group(1))
                    m_path = re.search(r'^\s*source_path:\s*(.*)', metadata, re.MULTILINE)
                    if m_path: source_path = _yaml_unescape(m_path.group(1))
                    m_context = re.search(r'^\s*source_context:\s*(.*)', metadata, re.MULTILINE)
                    if m_context: source_context = _yaml_unescape(m_context.group(1))
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
                    tags=new_tags,
                    source_context=source_context
                )
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_file_content)
                print("  ✅ Berhasil ditulis. Memvalidasi ulang secara otomatis...")
                
                # 4. Validasi Ulang
                validation_res = validate_file(file_path, use_llm_validation, model_name)
                save_validation_report(file_path, validation_res)
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
        
        # Explicitly collect garbage after finishing one file to free up memory
        import gc
        gc.collect()

if __name__ == "__main__":
    check_system_requirements()
    
    parser = argparse.ArgumentParser(description="Mencari file yang gagal divalidasi dan meng-convert ulangnya dengan AI.")
    parser.add_argument("path", help="Path direktori output (contoh: output_notes/)")
    parser.add_argument("--llm-validate", action="store_true", help="Gunakan mode LLM untuk mencari file yang gagal")
    parser.add_argument("--model", default="auto", help="Model Ollama yang digunakan (default: auto-detect berdasarkan RAM)")
    parser.add_argument("--retries", type=int, default=3, help="Jumlah maksimal percobaan reconvert jika masih gagal (default: 3)")
    parser.add_argument("--force", action="store_true", help="Lewati proses validasi dan proses ulang semua file di direktori")
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.path):
        print(f"Error: {args.path} bukan direktori yang valid.")
        sys.exit(1)
    model = args.model
    if model == "auto":
        model = get_recommended_model()

    reconvert_directory(args.path, args.llm_validate, model, args.retries, args.force)
