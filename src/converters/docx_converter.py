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
                        # Clamp to valid markdown heading range (1-6)
                        level = max(1, min(6, level))
                        prefix = '#' * level
                    except ValueError:
                        prefix = '##'  # Default to h2 for unrecognized heading styles
                    content.append(f"{prefix} {para.text}")
                else:
                    content.append(para.text)
        return "\n\n".join(content) if content else ""
    except Exception as e:
        return f"Error extracting DOCX: {str(e)}"
