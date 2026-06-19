import docx

def convert_docx(file_path):
    try:
        doc = docx.Document(file_path)
        content = []
        for para in doc.paragraphs:
            if para.text.strip():
                # Simple check for heading styles
                if para.style.name.startswith('Heading'):
                    level = para.style.name.split(' ')[-1]
                    try:
                        level = int(level)
                        prefix = '#' * level
                    except ValueError:
                        prefix = '###'
                    content.append(f"{prefix} {para.text}")
                else:
                    content.append(para.text)
        return "\n\n".join(content)
    except Exception as e:
        return f"Error extracting DOCX: {str(e)}"
