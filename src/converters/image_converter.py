import pytesseract
from PIL import Image, ImageEnhance

def convert_image(file_path):
    try:
        image = Image.open(file_path)
        
        # Pre-processing untuk meningkatkan akurasi Tesseract pada gambar desain/grafis
        # 1. Resize gambar raksasa untuk menghemat RAM drastis saat OCR
        if hasattr(Image, 'Resampling'):
            image.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
        else: # pragma: no cover
            image.thumbnail((2000, 2000), Image.LANCZOS)
            
        # 2. Ubah ke Grayscale
        image = image.convert('L')
        
        # 2. Tingkatkan Kontras agar teks lebih menonjol dari background
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # 3. Ketajaman (Opsional tapi membantu font tebal/tipis)
        sharpness = ImageEnhance.Sharpness(image)
        image = sharpness.enhance(1.5)
        
        # Ekstrak teks — gunakan multi-language untuk mendukung konten Indonesia + Inggris
        # Pastikan tesseract-ocr-ind terinstall: sudo apt install tesseract-ocr-ind (Linux)
        # atau: brew install tesseract-lang (macOS)
        try:
            text = pytesseract.image_to_string(image, lang='ind+eng')
        except Exception:
            # Fallback jika language pack tidak tersedia
            text = pytesseract.image_to_string(image)
        
        if not text.strip():
            return ""
        return text
    except Exception as e:
        return f"Error extracting Image text: {str(e)}"
