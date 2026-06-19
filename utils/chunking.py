import re
import json
import ollama

from utils.prompts import RAG_EXTRACTION_PROMPT

def _safe_truncate(text, max_chars):
    """Truncate text to max_chars without breaking multi-byte UTF-8 characters."""
    if len(text) <= max_chars:
        return text
    # Encode to UTF-8, truncate bytes, then decode safely
    truncated = text[:max_chars]
    # Find the last space within the truncated text to avoid mid-word cuts
    last_space = truncated.rfind(' ')
    if last_space > max_chars * 0.8:  # Only use space-break if it's not too far back
        return truncated[:last_space]
    return truncated

def chunk_text_intelligently(text, base_name, max_words=600, model_name='llama3'):
    """
    Split text into chunks, then use Ollama to format the text specifically for Trading RAG.
    """
    # Guard: check for empty text BEFORE chunking to avoid wasteful processing
    if not text or not text.strip():
        return []
    
    lines = text.splitlines(keepends=True)
    chunks = []
    current_chunk = ""
    current_words = 0
    
    # Split by lines to preserve original markdown formatting and newlines
    for line in lines:
        word_count = len(line.split())
        if current_words + word_count > max_words and current_words > 0:
            chunks.append(current_chunk)
            current_chunk = line
            current_words = word_count
        else:
            current_chunk += line
            current_words += word_count
            
    if current_chunk:
        chunks.append(current_chunk)
        
    atomic_notes = []
    used_filenames = set()
    

    
    for idx, chunk in enumerate(chunks):
        filename = f"{base_name}-part-{idx+1}.md"
        formatted_content = chunk
        tags = ""
        
        try:
            # Prompt the local LLM
            prompt = RAG_EXTRACTION_PROMPT.replace("{text_chunk}", _safe_truncate(chunk, 2500))
            
            print(f"\n⏳ Memproses chunk {idx+1} dari {len(chunks)} menggunakan AI ({model_name})...", flush=True)
            
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
                # Filter only valid string tags
                valid_tags = [str(t) for t in tags_list if t is not None and str(t).strip()]
                if valid_tags:
                    tags = "\n".join([f"#{t}" for t in valid_tags]) + "\n\n"
                    formatted_content = tags + formatted_content
                
        except Exception as e:
            # Fallback if parsing fails or Ollama is off
            print(f"Warning: Chunk {idx+1} failed AI processing ({str(e)}). Using raw text.")
            # We don't 'pass' here, we just let it use the fallback formatted_content (raw chunk)

        # Prevent any filename collision (both from AI slug or fallback)
        candidate = filename
        counter = 1
        while candidate in used_filenames:
            if candidate.endswith(".md"):
                candidate = f"{candidate[:-3]}-{counter}.md"
            else:
                candidate = f"{candidate}-{counter}.md"
            counter += 1
        filename = candidate
        
        used_filenames.add(filename)
        atomic_notes.append({
            "filename": filename,
            "content": formatted_content
        })
        
    return atomic_notes
