import argparse
import os

# Optimasi Tesseract OCR agar tidak menggunakan seluruh core CPU
os.environ["OMP_THREAD_LIMIT"] = "1"

import sys
import urllib.parse
import re
import ollama
import concurrent.futures
from converters import convert_pdf, convert_docx, convert_image, convert_media, convert_link, convert_ig_link, convert_youtube
from utils.markdown_formatter import generate_markdown
from utils.chunking import chunk_text_intelligently, process_chunk_with_ai, extract_global_context
from utils.text_helpers import get_recommended_model, clean_raw_text, get_recommended_concurrency, check_system_requirements

def ensure_model_installed(model_name):
    """Checks if the Ollama model is available locally, and pulls it if not."""
    print(f"\n🔍 Mengecek ketersediaan model AI '{model_name}'...")
    try:
        model_list = ollama.list()
        
        # Handle different versions of ollama-python client
        if hasattr(model_list, 'models'):
            available = [m.model for m in model_list.models]
        else:
            available = [m.get('name', m.get('model', '')) for m in model_list.get('models', [])]
            
        # Match exact name or with a tag, e.g., "llama3" matches "llama3:latest" or "llama3" exactly
        is_installed = any(m == model_name or m.startswith(model_name + ':') for m in available)
        
        if not is_installed:
            print(f"📥 Model '{model_name}' belum ter-install. Sedang mendownload otomatis...")
            print("⏳ Mohon tunggu, proses ini bisa memakan waktu (bergantung kecepatan internet).")
            ollama.pull(model_name)
            print(f"✅ Berhasil mendownload model '{model_name}'.")
        else:
            print(f"✅ Model '{model_name}' sudah tersedia dan siap digunakan.")
    except ConnectionError: # pragma: no cover
        print(f"❌ Tidak bisa terhubung ke Ollama. Pastikan aplikasi Ollama sudah berjalan!")
        print("   Download di: https://ollama.com/download")
        raise SystemExit(1)
    except Exception as e: # pragma: no cover
        # Check for common connection error types wrapped in other exceptions
        err_str = str(e).lower()
        if 'connection' in err_str or 'refused' in err_str or 'unavailable' in err_str:
            print(f"❌ Tidak bisa terhubung ke Ollama. Pastikan aplikasi Ollama sudah berjalan!")
            print("   Download di: https://ollama.com/download")
            raise SystemExit(1)
        print(f"⚠️ Gagal mengecek status model: {e}")

def sanitize_basename(name):
    name = re.sub(r'[^a-zA-Z0-9\s-]', '', name).strip().lower()
    name = re.sub(r'[\s]+', '-', name)
    # Strip leading/trailing hyphens and collapse multiple hyphens
    name = re.sub(r'-+', '-', name).strip('-')
    return name if name else 'untitled'

def process_source(source, outdir, model_name, global_used_filenames=None):
    is_url = source.startswith("http://") or source.startswith("https://")
    
    base_title = "doc"
    content = ""
    source_type = ""
    
    if is_url:
        print(f"Processing URL: {source}")
        parsed_url = urllib.parse.urlparse(source)
        # Use just the path for the base title, excluding the domain for cleaner filenames
        path_part = parsed_url.path.strip('/').replace('/', '-')
        base_title = sanitize_basename(path_part) if path_part else sanitize_basename(parsed_url.netloc)
        
        if "instagram.com" in parsed_url.netloc:
            source_type = "Instagram Post"
            content = convert_ig_link(source)
        elif "youtu.be" in parsed_url.netloc or "youtube.com" in parsed_url.netloc:
            source_type = "YouTube Video"
            content = convert_youtube(source)
        else:
            source_type = "Web Link"
            content = convert_link(source)
    else:
        if not os.path.exists(source):
            print(f"Error: File '{source}' not found.")
            return

        print(f"Processing File: {source}")
        ext = os.path.splitext(source)[1].lower()
        base_name_raw = os.path.splitext(os.path.basename(source))[0]
        base_title = sanitize_basename(base_name_raw)
        
        if ext == '.pdf':
            source_type = "PDF Document"
            content = convert_pdf(source)
        elif ext == '.docx':
            source_type = "Word Document"
            content = convert_docx(source)
        elif ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']:
            source_type = "Image (OCR)"
            content = convert_image(source)
        elif ext in ['.mp3', '.wav', '.m4a', '.flac']:
            source_type = "Audio (Whisper STT)"
            content = convert_media(source, is_video=False)
        elif ext in ['.mp4', '.avi', '.mkv', '.mov']:
            source_type = "Video (Whisper STT)"
            content = convert_media(source, is_video=True)
        else:
            print(f"Error: Unsupported file extension '{ext}'")
            return
            
    # Guard: abort if content is empty or is an error message from a converter
    if not content or not content.strip():
        print("Error: No content could be extracted from the source. Aborting.")
        return
        
    _CONVERTER_ERROR_PREFIXES = (
        "Error extracting PDF:",
        "Error extracting DOCX:",
        "Error extracting Image text:",
        "Error extracting Web Link:",
        "Error extracting Instagram post:",
        "Error extracting YouTube:",
        "Error transcribing media:",
        "Error: Invalid Instagram URL format.",
        "Failed to extract audio from video.",
    )
    if content.startswith(_CONVERTER_ERROR_PREFIXES):
        print(f"Converter returned an error: {content}")
        return
        
    # Clean raw text to optimize tokens and improve LLM output
    content = clean_raw_text(content)
        
    print("Splitting text into chunks...")
    raw_chunks = chunk_text_intelligently(content, max_words=600, overlap_words=50)
    total_chunks = len(raw_chunks)
    
    if total_chunks == 0:
        print("Warning: No chunks generated (text may be empty).")
        return
        
    print(f"📦 Ditemukan {total_chunks} chunk untuk diproses.", flush=True)
    
    print("\n🌐 Extracting Global Context...", flush=True)
    global_context = extract_global_context(content, model_name)
    if global_context:
        print(f"Context: {global_context}")
        global_context_block = f"\n[Konteks Global Dokumen: {global_context}]\n"
    else:
        global_context_block = ""
        
    # Ensure output directory exists and create a sub-directory for the specific source
    source_outdir = os.path.join(outdir, base_title)
    os.makedirs(source_outdir, exist_ok=True)
    
    if global_used_filenames is None:
        global_used_filenames = set()
    
    # Pre-dump chunks
    for i, chunk in enumerate(raw_chunks):
        raw_filepath = os.path.join(source_outdir, f"{base_title}-part-{i+1}.raw.txt")
        if not os.path.exists(raw_filepath):
            with open(raw_filepath, "w", encoding="utf-8") as f:
                f.write(chunk)
                
    # Detect resume state
    pending_indices = []
    existing_files = set(os.listdir(source_outdir))
    for i in range(total_chunks):
        # If any markdown file has prefix `base_title-part-{i+1}-` it means it's done
        prefix = f"{base_title}-part-{i+1}-"
        is_done = any(f.startswith(prefix) and f.endswith(".md") for f in existing_files)
        if not is_done:
            pending_indices.append(i)
            
    if not pending_indices:
        print(f"✅ All {total_chunks} chunks already processed. Skipping.")
        return
        
    print(f"Resume logic: {len(pending_indices)} out of {total_chunks} chunks remaining.")
    
    # Process Concurrency
    concurrency = get_recommended_concurrency()
    generated_count = total_chunks - len(pending_indices)
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        future_to_idx = {
            executor.submit(
                process_chunk_with_ai, 
                raw_chunks[i], 
                i, 
                total_chunks, 
                global_context_block, 
                base_title, 
                model_name
            ): i for i in pending_indices
        }
        
        futures_set = set(future_to_idx.keys())
        
        while futures_set:
            try:
                done, not_done = concurrent.futures.wait(futures_set, return_when=concurrent.futures.FIRST_COMPLETED)
                for future in done:
                    futures_set.remove(future)
                    idx = future_to_idx[future]
                    try:
                        note = future.result()
                        generated_count += 1
                        filename = note["filename"]
                        chunk_content = note["content"]
                        tags = note.get("tags", [])
                        source_context = note.get("source_context", "")
                        
                        # Collision check
                        stem = filename[:-3] if filename.endswith(".md") else filename
                        counter = 1
                        while filename in global_used_filenames:
                            filename = f"{stem}-{counter}.md"
                            counter += 1
                        global_used_filenames.add(filename)
                        
                        final_markdown = generate_markdown(
                            title=filename.replace('.md', ''), 
                            content=chunk_content, 
                            source_type=source_type, 
                            source_path_or_url=source,
                            tags=tags,
                            source_context=source_context
                        )
                        
                        filepath = os.path.join(source_outdir, filename)
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(final_markdown)
                            
                        # Keep standard suffix for reconvert script compatibility
                        raw_filepath = f"{filepath}.raw.txt"
                        with open(raw_filepath, "w", encoding="utf-8") as f:
                            f.write(note["raw_chunk"])
                            
                        print(f"Saved atomic note: {filepath}")
                        
                    except Exception as exc:
                        print(f"Chunk {idx+1} generated an exception: {exc}")
                        
            except KeyboardInterrupt:
                print("\n\n⚠️  Process Paused. Do you want to (r)esume, (s)ave & exit safely, or (q)uit immediately? [r/s/q]: ", end="", flush=True)
                try:
                    ans = sys.stdin.readline().strip().lower()
                except Exception:
                    ans = 's' # default to save if stdin fails
                    
                if ans == 's':
                    print("🛑 Cancelling pending tasks and waiting for running tasks to finish...")
                    for f in futures_set:
                        f.cancel()
                    executor.shutdown(wait=True)
                    print(f"Graceful exit complete. Run the same command again to resume.")
                    sys.exit(0)
                elif ans == 'q':
                    print("🛑 Quitting immediately.")
                    os._exit(1)
                else:
                    print("▶️  Resuming process...")
                    
    print(f"\nSuccess! Generated {generated_count} atomic notes in '{source_outdir}'")

def main():
    check_system_requirements()
    
    parser = argparse.ArgumentParser(description="Universal File-to-Markdown Converter (Atomic Notes)")
    parser.add_argument("source", help="Path to the local file, directory, or URL to convert")
    parser.add_argument("-o", "--outdir", help="Output directory to save atomic notes", default="./output_notes")
    parser.add_argument("-m", "--model", help="Ollama model to use for AI formatting (default: auto)", default="auto")
    
    args = parser.parse_args()
    source = args.source
    outdir = args.outdir
    
    model_name = args.model
    if model_name == "auto":
        model_name = get_recommended_model()
        
    # Ensure model is downloaded before proceeding
    ensure_model_installed(model_name)
    
    os.makedirs(outdir, exist_ok=True)
    
    if not (source.startswith("http://") or source.startswith("https://")) and os.path.isdir(source):
        print(f"Batch Processing Directory: {source}")
        # Shared set to prevent cross-file filename collisions across the entire batch
        batch_used_filenames = set()
        for root, _, files in os.walk(source):
            for file in files:
                if file.startswith('.'):
                    continue
                ext = os.path.splitext(file)[1].lower()
                if ext in ['.pdf', '.docx', '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.mp3', '.wav', '.m4a', '.flac', '.mp4', '.avi', '.mkv', '.mov']:
                    file_path = os.path.join(root, file)
                    print(f"\n--- Processing: {file_path} ---")
                    process_source(file_path, outdir, model_name, batch_used_filenames)
                    import gc
                    gc.collect()
    else:
        process_source(source, outdir, model_name)
        import gc
        gc.collect()

if __name__ == "__main__":
    main()
