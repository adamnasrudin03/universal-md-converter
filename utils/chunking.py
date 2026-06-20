import re
import json
import ollama

from utils.prompts import RAG_EXTRACTION_PROMPT
from utils.text_helpers import safe_truncate

def chunk_text_intelligently(text, base_name, max_words=600, model_name='llama3'):
    """
    Split text into chunks, then use Ollama to format each chunk into
    a structured RAG-ready Knowledge Summary.
    """
    # Guard: check for empty text BEFORE chunking to avoid wasteful processing
    if not text or not text.strip():
        return []
    
    # Semantic paragraph chunking with overlap
    paragraphs = re.split(r'\n\s*\n', text)
    chunks = []
    current_chunk = ""
    current_words = 0
    last_paragraph = ""
    
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
            
        word_count = len(para.split())
        
        if current_words + word_count > max_words and current_words > 0:
            chunks.append(current_chunk.strip())
            # Mulai chunk baru dengan overlap (menyertakan paragraf terakhir dari chunk sebelumnya)
            if last_paragraph and len(last_paragraph.split()) < (max_words / 2):
                current_chunk = last_paragraph + "\n\n" + para + "\n\n"
                current_words = len(last_paragraph.split()) + word_count
            else:
                current_chunk = para + "\n\n"
                current_words = word_count
        else:
            current_chunk += para + "\n\n"
            current_words += word_count
            
        last_paragraph = para
            
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
        
    atomic_notes = []
    used_filenames = set()
    
    for idx, chunk in enumerate(chunks):
        filename = f"{base_name}-part-{idx+1}.md"
        formatted_content = chunk
        final_tags = []
        
        try:
            # Prompt the local LLM
            prompt = RAG_EXTRACTION_PROMPT.replace("{text_chunk}", safe_truncate(chunk, 2500))
            
            print(f"\n⏳ Memproses chunk {idx+1} dari {len(chunks)} menggunakan AI ({model_name})...", flush=True)
            
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
            
            print("\n✅ Selesai memproses chunk.")
            
            # Since we forced format='json', we should be able to parse it directly
            try:
                parsed_json = json.loads(response_text)
            except json.JSONDecodeError:
                # Fallback regex if LLM still wraps in markdown blocks
                json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                if json_match:
                    try:
                        parsed_json = json.loads(json_match.group(0))
                    except json.JSONDecodeError:
                        raise Exception("Regex matched but still not valid JSON")
                else:
                    raise Exception("Valid JSON not found in LLM response")
            
            # Extract filename (guard against null from LLM)
            slug = parsed_json.get("filename_slug", "") or ""
            if not isinstance(slug, str):
                slug = str(slug)
            slug = re.sub(r'[^a-zA-Z0-9\s-]', '', slug).strip().lower()
            slug = re.sub(r'[\s]+', '-', slug)
            slug = re.sub(r'-+', '-', slug).strip('-')  # Collapse multiple hyphens
            if slug:
                filename = f"{base_name}-{slug}.md"
            
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

            if rag_content.strip():
                formatted_content = rag_content
            
            # Extract tags (guard against null from LLM)
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
                    final_tags = valid_tags
                
        except Exception as e:
            # Fallback if parsing fails or Ollama is off
            print(f"Warning: Chunk {idx+1} failed AI processing ({str(e)}). Using raw text.")
            # We don't 'pass' here, we just let it use the fallback formatted_content (raw chunk)

        # Prevent any filename collision (both from AI slug or fallback)
        # Snapshot base_filename ONCE before the loop, so counter increments cleanly
        # without cascading suffixes like name-slug-1-2-3.md
        base_filename = filename
        stem = base_filename[:-3] if base_filename.endswith(".md") else base_filename
        counter = 1
        while filename in used_filenames:
            filename = f"{stem}-{counter}.md"
            counter += 1
        
        used_filenames.add(filename)
        atomic_notes.append({
            "filename": filename,
            "content": formatted_content,
            "raw_chunk": chunk,
            "tags": final_tags
        })
        
    return atomic_notes
