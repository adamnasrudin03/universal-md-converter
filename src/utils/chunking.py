import re
import json
import ollama

from utils.prompts import RAG_EXTRACTION_PROMPT
from utils.text_helpers import safe_truncate

def extract_global_context(text, model_name='llama3'):
    """Extract a quick 2-3 sentence global context from the first part of the document."""
    try:
        truncated_text = safe_truncate(text, 4000)
        prompt = f"""Tugas Anda adalah membaca teks berikut dan memberikan ringkasan 2-3 kalimat mengenai topik utamanya.
Ringkasan ini akan digunakan sebagai konteks global. JANGAN menggunakan kata pengantar, langsung berikan ringkasan.
Teks:
{truncated_text}
"""
        response = ollama.chat(model=model_name, messages=[
            {'role': 'user', 'content': prompt}
        ], keep_alive=0, options={'temperature': 0.0, 'num_thread': 4, 'num_ctx': 4096})
        
        if isinstance(response, dict):
            context = response.get('message', {}).get('content', '')
        else:
            msg = getattr(response, 'message', None)
            context = getattr(msg, 'content', '') if msg else ''
            
        return context.strip()
    except Exception as e:
        print(f"Warning: Failed to extract global context: {e}")
        return ""

def recursive_markdown_split(text, max_words=600, overlap_words=50):
    """Split text recursively using markdown headers, then paragraphs, then sentences.
    Includes overlap logic when splitting by exact max_words to preserve context.
    """
    separators = [r'\n# ', r'\n## ', r'\n### ', r'\n\s*\n', r'\.\s']
    
    def _split(t, separator_index):
        if not t.strip(): return []
        if len(t.split()) <= max_words: return [t]
        if separator_index >= len(separators):
            words_list = t.split()
            chunks = []
            i = 0
            while i < len(words_list):
                chunk = " ".join(words_list[i:i+max_words])
                chunks.append(chunk)
                if i + max_words >= len(words_list):
                    break
                # Advance by max_words - overlap_words, ensure at least 1
                step = max(1, max_words - overlap_words)
                i += step
            return chunks
            
        sep = separators[separator_index]
        is_prefix_sep = '#' in sep
        parts = re.split(f'({sep})', t)
        
        combined_parts, current_part = [], ""
        for i, part in enumerate(parts):
            if i % 2 == 1:
                if is_prefix_sep:
                    if current_part: combined_parts.append(current_part)
                    current_part = part
                else:
                    current_part += part
                    combined_parts.append(current_part)
                    current_part = ""
            else: current_part += part
        if current_part: combined_parts.append(current_part)
        combined_parts = [p for p in combined_parts if p.strip()]
        
        
        final_chunks, current_chunk = [], ""
        for part in combined_parts:
            if len(part.split()) > max_words:
                if current_chunk:
                    final_chunks.append(current_chunk)
                    current_chunk = ""
                final_chunks.extend(_split(part, separator_index + 1))
            else:
                if len((current_chunk + part).split()) > max_words and current_chunk:
                    final_chunks.append(current_chunk)
                    current_chunk = part
                else: current_chunk += part
        if current_chunk: final_chunks.append(current_chunk)
        return final_chunks
        
    return _split(text, 0)

def chunk_text_intelligently(text, max_words=600, overlap_words=50):
    """
    Split text into chunks recursively, with overlap, without hitting AI yet.
    Returns a list of raw string chunks.
    """
    if not text or not text.strip():
        return []
    
    chunks = recursive_markdown_split(text, max_words, overlap_words)
    return chunks

def process_chunk_with_ai(chunk, chunk_index, total_chunks, global_context_block, base_name, model_name):
    """
    Processes a single raw text chunk with Ollama using native JSON Schema.
    Returns a dict containing filename, content, tags, and source_context.
    """
    filename = f"{base_name}-part-{chunk_index+1}.md"
    formatted_content = chunk
    final_tags = []
    source_context = ""
    
    try:
        # Prompt the local LLM
        prompt = RAG_EXTRACTION_PROMPT.replace("{global_context_block}", global_context_block).replace("{text_chunk}", safe_truncate(chunk, 4000))
        
        print(f"\n⏳ Memproses chunk {chunk_index+1} dari {total_chunks} menggunakan AI ({model_name})...", flush=True)
        
        # Define JSON schema for native structured output
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
        
        response = ollama.chat(model=model_name, messages=[
            {'role': 'user', 'content': prompt}
        ], format=schema, stream=False, keep_alive=0, options={'temperature': 0.0, 'num_thread': 4, 'num_ctx': 4096})
        
        if isinstance(response, dict):
            response_text = response.get('message', {}).get('content', '')
        else:
            msg = getattr(response, 'message', None)
            response_text = getattr(msg, 'content', '') if msg else ''
            
        print(f"✅ Selesai memproses chunk {chunk_index+1}.")
        
        parsed_json = json.loads(response_text)
        
        # Extract filename slug
        slug = parsed_json.get("filename_slug", "") or ""
        if not isinstance(slug, str): # pragma: no cover
            slug = str(slug)
        slug = re.sub(r'[^a-zA-Z0-9\s-]', '', slug).strip().lower()
        slug = re.sub(r'[\s]+', '-', slug)
        slug = re.sub(r'-+', '-', slug).strip('-')
        if slug:
            filename = f"{base_name}-{slug}.md"
            
        # Extract source context
        src = parsed_json.get("source_context", "")
        if src and isinstance(src, str) and src.strip() and src.strip().lower() not in ["none", "null", "n/a", "unknown"]:
            source_context = f"Bagian {chunk_index+1} dari {total_chunks} | {src.strip()}"
        else:
            source_context = f"Bagian {chunk_index+1} dari {total_chunks}"
        
        # Extract content
        rag_content = parsed_json.get("rag_content", "") or ""
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

        if rag_content.strip():
            formatted_content = rag_content
        
        # Extract tags
        tags_list = parsed_json.get("tags", []) or []
        if tags_list and isinstance(tags_list, list):
            valid_tags = []
            for t in tags_list:
                if t is not None:
                    t_str = re.sub(r'[^a-zA-Z0-9\s-]', '', str(t)).strip().lower()
                    t_str = re.sub(r'[\s]+', '-', t_str)
                    t_str = re.sub(r'-+', '-', t_str).strip('-')
                    if t_str:
                        valid_tags.append(t_str)
            if valid_tags:
                final_tags = valid_tags
            
    except Exception as e:
        print(f"Warning: Chunk {chunk_index+1} failed AI processing ({str(e)}). Using raw text.")

    return {
        "filename": filename,
        "content": formatted_content,
        "raw_chunk": chunk,
        "tags": final_tags,
        "source_context": source_context
    }

