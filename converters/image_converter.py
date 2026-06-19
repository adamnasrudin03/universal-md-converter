import pytesseract
from PIL import Image, ImageEnhance, ImageFilter

def convert_image(file_path):
    try:
        image = Image.open(file_path)
        
        # Pre-processing untuk meningkatkan akurasi Tesseract pada gambar desain/grafis
        # 1. Ubah ke Grayscale
        image = image.convert('L')
        
        # 2. Tingkatkan Kontras agar teks lebih menonjol dari background
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)
        
        # 3. Ketajaman (Opsional tapi membantu font tebal/tipis)
        sharpness = ImageEnhance.Sharpness(image)
        image = sharpness.enhance(1.5)
        
        # Ekstrak teks
        # (Catatan: Jika hasil masih jelek karena bahasa, pastikan tesseract-ocr-ind terinstall dan tambahkan argumen: lang='ind+eng')
        text = pytesseract.image_to_string(image)
        
        if not text.strip():
            return "*No text could be extracted from this image.*"
        return text
    except Exception as e:
        return f"Error extracting Image text: {str(e)}"
