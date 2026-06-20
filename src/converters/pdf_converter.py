import pdfplumber
import logging
from .image_converter import convert_image

# Optional dependencies
try:
    import fitz  # PyMuPDF
except ImportError: # pragma: no cover
    fitz = None

try:
    import pytesseract
    from PIL import ImageEnhance
except ImportError: # pragma: no cover
    pytesseract = None

# Suppress annoying pdfminer warnings
logging.getLogger("pdfminer").setLevel(logging.ERROR)

def convert_pdf(file_path):
    text_content = []
    try:
        if fitz:
            with fitz.open(file_path) as pdf:
                for i, page in enumerate(pdf):
                    page_text = page.get_text()
                    
                    if not page_text or len(page_text.strip()) < 50:
                        # Fallback to OCR if PyMuPDF returns nothing useful
                        if pytesseract: # pragma: no cover
                            try:
                                pix = page.get_pixmap(dpi=150)
                                from PIL import Image
                                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                                if hasattr(Image, 'Resampling'):
                                    img.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
                                else: # pragma: no cover
                                    img.thumbnail((2000, 2000), Image.LANCZOS)
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
                            finally:
                                if 'img' in locals():
                                    try:
                                        img.close()
                                    except Exception: # pragma: no cover
                                        pass
                                import gc
                                gc.collect()
                    
                    if page_text and page_text.strip():
                        text_content.append(f"## Page {i + 1}\n\n{page_text}")
            
            return "\n\n".join(text_content) if text_content else ""

        # Fallback to pdfplumber if PyMuPDF is not installed
        with pdfplumber.open(file_path) as pdf: # pragma: no cover
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text(layout=True)
                
                # If extract_text fails or returns very little text, fallback to OCR
                if (not page_text or len(page_text.strip()) < 50) and pytesseract:
                    try:
                        # Extract image of the page
                        img = page.to_image(resolution=150).original
                        from PIL import Image
                        if hasattr(Image, 'Resampling'):
                            img.thumbnail((2000, 2000), Image.Resampling.LANCZOS)
                        else:
                            img.thumbnail((2000, 2000), Image.LANCZOS)
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
                    finally:
                        if 'img' in locals():
                            try:
                                img.close()
                            except Exception:
                                pass
                        import gc
                        gc.collect()
                
                if page_text and page_text.strip():
                    text_content.append(f"## Page {i + 1}\n\n{page_text}")
                        
            return "\n\n".join(text_content) if text_content else ""
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"
