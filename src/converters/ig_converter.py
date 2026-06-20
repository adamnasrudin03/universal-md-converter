import os
import shutil
import tempfile
import instaloader
from urllib.parse import urlparse
from .image_converter import convert_image

def convert_ig_link(url):
    """
    Downloads an Instagram post (Caption + Slide Images), extracts text via OCR, and combines them.
    """
    temp_dir = None
    try:
        # Extract shortcode from URL
        # e.g., https://www.instagram.com/p/DZucoBjiQxd/ -> DZucoBjiQxd
        path_parts = urlparse(url).path.strip('/').split('/')
        if 'p' in path_parts:
            idx = path_parts.index('p')
            if idx + 1 < len(path_parts):
                shortcode = path_parts[idx + 1]
            else:
                return "Error: Invalid Instagram URL format. Missing shortcode after /p/."
        elif 'reel' in path_parts or 'reels' in path_parts:
            # Handle both /reel/ and /reels/
            key = 'reel' if 'reel' in path_parts else 'reels'
            idx = path_parts.index(key)
            if idx + 1 < len(path_parts):
                shortcode = path_parts[idx + 1]
            else:
                return f"Error: Invalid Instagram URL format. Missing shortcode after /{key}/."
        else:
            return "Error: Invalid Instagram URL format. Make sure it's a /p/, /reel/, or /reels/ link."
            
        L = instaloader.Instaloader()
        
        # Load the post
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        content = []
        if post.caption:
            content.append("## Instagram Caption\n")
            content.append(post.caption)
            content.append("\n\n---\n\n")
            
        temp_dir = tempfile.mkdtemp(prefix=f"temp_ig_{shortcode}_")
        
        # Download the post to a temporary directory
        L.download_post(post, target=temp_dir)
        
        # Iterate over downloaded files and run OCR on images
        # Instaloader creates nested subdirectories inside target, so we must
        # use os.walk to traverse all levels and find the actual image files.
        content.append("## Text from Images (OCR)\n")
        images_found = False
        slide_number = 0
        
        image_files = []
        for root, dirs, files_in_dir in os.walk(temp_dir):
            for fname in sorted(files_in_dir):
                if fname.lower().endswith(('.png', '.jpg', '.jpeg')):
                    image_files.append(os.path.join(root, fname))
        
        # Sort by full path to maintain slide order
        image_files.sort()
        
        for filepath in image_files:
            images_found = True
            slide_number += 1
            ocr_text = convert_image(filepath)
            
            # Skip slides where OCR returned an error or empty result
            if ocr_text.startswith("Error extracting Image text:") or not ocr_text.strip():
                content.append(f"### Slide {slide_number}\n")
                content.append("*OCR could not extract text from this slide.*")
                content.append("\n\n")
                import gc; gc.collect()
                continue
            
            content.append(f"### Slide {slide_number}\n")
            content.append(ocr_text)
            content.append("\n\n")
            import gc; gc.collect()
                
        if not images_found:
            content.append("*No image slides found in this post.*")
            
        return "".join(content)
        
    except Exception as e:
        return f"Error extracting Instagram post: {str(e)}"
    finally:
        # Selalu bersihkan temporary directory terlepas ada error atau tidak
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
