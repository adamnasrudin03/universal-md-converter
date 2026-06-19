import os
import shutil
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
        elif 'reel' in path_parts:
            idx = path_parts.index('reel')
            if idx + 1 < len(path_parts):
                shortcode = path_parts[idx + 1]
            else:
                return "Error: Invalid Instagram URL format. Missing shortcode after /reel/."
        else:
            return "Error: Invalid Instagram URL format. Make sure it's a /p/ or /reel/ link."
            
        L = instaloader.Instaloader()
        
        # Load the post
        post = instaloader.Post.from_shortcode(L.context, shortcode)
        
        content = []
        if post.caption:
            content.append("## Instagram Caption\n")
            content.append(post.caption)
            content.append("\n\n---\n\n")
            
        temp_dir = f"temp_ig_{shortcode}"
        os.makedirs(temp_dir, exist_ok=True)
        
        # Download the post to a temporary directory
        L.download_post(post, target=temp_dir)
        
        # Iterate over downloaded files and run OCR on images
        content.append("## Text from Images (OCR)\n")
        images_found = False
        
        # Sort files to ensure slides are processed in order
        files = sorted(os.listdir(temp_dir))
        for filename in files:
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                images_found = True
                filepath = os.path.join(temp_dir, filename)
                ocr_text = convert_image(filepath)
                
                content.append(f"### Slide {filename}\n")
                content.append(ocr_text)
                content.append("\n\n")
                
        if not images_found:
            content.append("*No image slides found in this post.*")
            
        return "".join(content)
        
    except Exception as e:
        return f"Error extracting Instagram post: {str(e)}"
    finally:
        # Selalu bersihkan temporary directory terlepas ada error atau tidak
        if temp_dir and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
