import pdfplumber
import logging
from .image_converter import convert_image

# Suppress annoying pdfminer warnings
logging.getLogger("pdfminer").setLevel(logging.ERROR)

def convert_pdf(file_path):
    text_content = []
    try:
        # Import pytesseract here to avoid circular/missing deps if not available, though it is in requirements
        import pytesseract
        from PIL import ImageEnhance
    except ImportError:
        pytesseract = None

    try:
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text(layout=True)
                
                # If extract_text fails or returns very little text, fallback to OCR
                if (not page_text or len(page_text.strip()) < 50) and pytesseract:
                    try:
                        # Extract image of the page
                        img = page.to_image(resolution=150).original
                        # Pre-process image slightly for better OCR (similar to image_converter)
                        img = img.convert('L')
                        img = ImageEnhance.Contrast(img).enhance(2.0)
                        
                        try:
                            ocr_text = pytesseract.image_to_string(img, lang='ind+eng')
                        except Exception:
                            ocr_text = pytesseract.image_to_string(img)
                            
                        if ocr_text and len(ocr_text.strip()) > len(page_text.strip() if page_text else ""):
                            page_text = ocr_text
                    except Exception as ocr_e:
                        print(f"Warning: OCR fallback failed on page {i+1}: {ocr_e}")
                
                if page_text and page_text.strip():
                    text_content.append(f"## Page {i + 1}\n\n{page_text}")
                    
        return "\n\n".join(text_content) if text_content else ""
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"
