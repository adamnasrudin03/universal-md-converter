import argparse
import os
import urllib.parse
import re
import ollama
from converters import convert_pdf, convert_docx, convert_image, convert_media, convert_link, convert_ig_link, convert_youtube
from utils.markdown_formatter import generate_markdown
from utils.chunking import chunk_text_intelligently
from utils.text_helpers import get_recommended_model



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
    except ConnectionError:
        print(f"❌ Tidak bisa terhubung ke Ollama. Pastikan aplikasi Ollama sudah berjalan!")
        print("   Download di: https://ollama.com/download")
        raise SystemExit(1)
    except Exception as e:
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
        
    print("Splitting text into Atomic Notes intelligently...")
    atomic_notes = chunk_text_intelligently(content, base_title, max_words=600, model_name=model_name)
    
    if not atomic_notes:
        print("Warning: No atomic notes were generated (text may be empty).")
        return
    
    # Ensure output directory exists (safe for programmatic callers)
    os.makedirs(outdir, exist_ok=True)
    
    # Resolve cross-file filename collisions in batch mode
    if global_used_filenames is None:
        global_used_filenames = set()
    
    for note in atomic_notes:
        filename = note["filename"]
        chunk_content = note["content"]
        raw_chunk_content = note.get("raw_chunk", "")
        tags = note.get("tags", [])
        
        # Guard: prevent overwriting a file produced by a prior source in batch mode
        stem = filename[:-3] if filename.endswith(".md") else filename
        counter = 1
        while filename in global_used_filenames:
            filename = f"{stem}-{counter}.md"
            counter += 1
        global_used_filenames.add(filename)
        
        # Format to markdown
        final_markdown = generate_markdown(
            title=filename.replace('.md', ''), 
            content=chunk_content, 
            source_type=source_type, 
            source_path_or_url=source,
            tags=tags
        )
        
        # Write to output directory
        filepath = os.path.join(outdir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_markdown)
            
        # Write the raw chunk for validation/reconvert fallback
        raw_filepath = f"{filepath}.raw.txt"
        with open(raw_filepath, "w", encoding="utf-8") as f:
            f.write(raw_chunk_content)
            
        print(f"Saved atomic note: {filepath}")
        
    print(f"\nSuccess! Generated {len(atomic_notes)} atomic notes in '{outdir}'")

def main():
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
                ext = os.path.splitext(file)[1].lower()
                if ext in ['.pdf', '.docx', '.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.mp3', '.wav', '.m4a', '.flac', '.mp4', '.avi', '.mkv', '.mov']:
                    file_path = os.path.join(root, file)
                    print(f"\n--- Processing: {file_path} ---")
                    process_source(file_path, outdir, model_name, batch_used_filenames)
    else:
        process_source(source, outdir, model_name)

if __name__ == "__main__":
    main()
