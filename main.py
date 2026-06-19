import argparse
import os
import urllib.parse
import re
import ollama
from converters import convert_pdf, convert_docx, convert_image, convert_media, convert_link, convert_ig_link
from utils.markdown_formatter import generate_markdown
from utils.chunking import chunk_text_intelligently
import platform
import subprocess

def get_recommended_model():
    """Detects system RAM and returns an appropriate Ollama model name."""
    model = "llama3.2" # Default to lightweight
    try:
        system = platform.system()
        total_ram_gb = 0
        
        if system == "Darwin": # macOS
            res = subprocess.run(['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True)
            if res.returncode == 0:
                total_ram_bytes = int(res.stdout.strip())
                total_ram_gb = total_ram_bytes / (1024**3)
        elif system == "Linux":
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if 'MemTotal' in line:
                        kb = int(line.split()[1])
                        total_ram_gb = kb / (1024**2)
                        break
                        
        if total_ram_gb >= 15.5: # 16GB RAM or more
            model = "llama3"
            print(f"🖥️  System RAM: {total_ram_gb:.1f} GB. Auto-selecting heavy model: '{model}'")
        elif total_ram_gb > 0:
            print(f"🖥️  System RAM: {total_ram_gb:.1f} GB. Auto-selecting lightweight model: '{model}'")
        else:
            print(f"🖥️  Auto-selecting lightweight model: '{model}' (Failed to read RAM)")
            
    except Exception as e:
        print(f"🖥️  Auto-selecting lightweight model: '{model}' (System check error)")
        
    return model

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
    except Exception as e:
        print(f"⚠️ Gagal mengecek status model: {e}")

def sanitize_basename(name):
    name = re.sub(r'[^a-zA-Z0-9\s-]', '', name).strip().lower()
    return re.sub(r'[\s]+', '-', name)

def main():
    parser = argparse.ArgumentParser(description="Universal File-to-Markdown Converter (Atomic Notes)")
    parser.add_argument("source", help="Path to the local file or URL to convert")
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
    
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    
    is_url = source.startswith("http://") or source.startswith("https://")
    
    base_title = "doc"
    content = ""
    source_type = ""
    
    if is_url:
        print(f"Processing URL: {source}")
        parsed_url = urllib.parse.urlparse(source)
        base_title = sanitize_basename(parsed_url.netloc + parsed_url.path.replace('/', '-'))
        
        if "instagram.com" in parsed_url.netloc:
            source_type = "Instagram Post"
            content = convert_ig_link(source)
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
        elif ext in ['.docx', '.doc']:
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
    if content.startswith("Error") or content.startswith("Failed"):
        print(f"Converter returned an error: {content}")
        return
        
    print("Splitting text into Atomic Notes intelligently...")
    atomic_notes = chunk_text_intelligently(content, base_title, max_words=600, model_name=model_name)
    
    if not atomic_notes:
        print("Warning: No atomic notes were generated (text may be empty).")
        return
    
    for note in atomic_notes:
        filename = note["filename"]
        chunk_content = note["content"]
        
        # Format to markdown
        final_markdown = generate_markdown(
            title=filename.replace('.md', ''), 
            content=chunk_content, 
            source_type=source_type, 
            source_path_or_url=source
        )
        
        # Write to output directory
        filepath = os.path.join(outdir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_markdown)
            
        print(f"Saved atomic note: {filepath}")
        
    print(f"\nSuccess! Generated {len(atomic_notes)} atomic notes in '{outdir}'")

if __name__ == "__main__":
    main()
