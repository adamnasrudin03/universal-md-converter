import pdfplumber

def convert_pdf(file_path):
    text_content = []
    try:
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_text = page.extract_text()
                if page_text:
                    text_content.append(f"## Page {i + 1}\n\n{page_text}")
        return "\n".join(text_content) if text_content else ""
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"
