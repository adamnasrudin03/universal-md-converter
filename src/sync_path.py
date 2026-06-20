import os
import argparse
import urllib.parse
from main import sanitize_basename

def get_base_title(source):
    is_url = source.startswith("http://") or source.startswith("https://")
    if is_url:
        parsed_url = urllib.parse.urlparse(source)
        path_part = parsed_url.path.strip('/').replace('/', '-')
        base_title = sanitize_basename(path_part) if path_part else sanitize_basename(parsed_url.netloc)
    else:
        base_name_raw = os.path.splitext(os.path.basename(source))[0]
        base_title = sanitize_basename(base_name_raw)
    return base_title

def sync_path(old_path, new_path, directory):
    old_prefix = get_base_title(old_path)
    new_prefix = get_base_title(new_path)
    
    print(f"🔍 Mencari file dengan prefix '{old_prefix}-' di dalam {directory} ...")
    
    count = 0
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith(".md") and file.startswith(f"{old_prefix}-"):
                old_filepath = os.path.join(root, file)
                
                # Baca konten file
                with open(old_filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Update isi Metadata Source Path
                # Support modern YAML frontmatter format: source_path: "..."
                new_content = content.replace(
                    f'source_path: "{old_path}"',
                    f'source_path: "{new_path}"'
                )
                # Also support legacy bold-format metadata (backward compat)
                new_content = new_content.replace(
                    f"**Source Path/URL:** {old_path}",
                    f"**Source Path/URL:** {new_path}"
                )
                
                # Buat nama file baru (hanya ganti prefix pertama)
                new_filename = file.replace(f"{old_prefix}-", f"{new_prefix}-", 1)
                new_filepath = os.path.join(root, new_filename)
                
                # Tulis file baru dan hapus yang lama (rename)
                with open(old_filepath, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                
                # Guard: don't overwrite an existing file at the destination
                if os.path.exists(new_filepath) and old_filepath != new_filepath:
                    print(f"⚠️ Skip rename {file}: target '{new_filename}' already exists.")
                else:
                    os.rename(old_filepath, new_filepath)
                    print(f"✅ Diperbarui: {file} -> {new_filename}")
                
                # Also rename companion .raw.txt file if it exists
                old_raw = f"{old_filepath}.raw.txt"
                new_raw = f"{new_filepath}.raw.txt"
                if os.path.exists(old_raw):
                    if os.path.exists(new_raw) and old_raw != new_raw:
                        print(f"⚠️ Skip rename raw: target '{os.path.basename(new_raw)}' already exists.")
                    else:
                        os.rename(old_raw, new_raw)
                        
                count += 1
                
    if count == 0:
        print(f"⚠️ Tidak ada file yang ditemukan dengan prefix '{old_prefix}-' dan metadata yang cocok.")
    else:
        print(f"\nSelesai! {count} file berhasil disinkronisasi.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sinkronisasi perubahan nama/path file sumber ke hasil output Markdown.")
    parser.add_argument("--old", required=True, help="Path/URL file sumber yang lama")
    parser.add_argument("--new", required=True, help="Path/URL file sumber yang baru")
    parser.add_argument("--dir", default="./output_notes", help="Direktori hasil output (default: ./output_notes)")
    
    args = parser.parse_args()
    
    if not os.path.isdir(args.dir):
        print(f"Error: '{args.dir}' bukan direktori yang valid atau tidak ditemukan.")
        exit(1)
        
    sync_path(args.old, args.new, args.dir)
