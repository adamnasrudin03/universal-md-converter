import argparse
import os
import urllib.parse
import re
from converters import convert_pdf, convert_docx, convert_image, convert_media, convert_link, convert_ig_link
from utils.markdown_formatter import generate_markdown
from utils.chunking import chunk_text_intelligently

def sanitize_basename(name):
    name = re.sub(r'[^a-zA-Z0-9\s-]', '', name).strip().lower()
    return re.sub(r'[\s]+', '-', name)

def main():
    parser = argparse.ArgumentParser(description="Universal File-to-Markdown Converter (Atomic Notes)")
    parser.add_argument("source", help="Path to the local file or URL to convert")
    parser.add_argument("-o", "--outdir", help="Output directory to save atomic notes", default="./output_notes")
    
    args = parser.parse_args()
    source = args.source
    outdir = args.outdir
    
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
        base_name_raw = os.path.basename(source).split('.')[0]
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
            
    print("Splitting text into Atomic Notes intelligently...")
    atomic_notes = chunk_text_intelligently(content, base_title, max_words=600)
    
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
