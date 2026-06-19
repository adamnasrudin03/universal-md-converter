import datetime

def generate_markdown(title, content, source_type, source_path_or_url):
    """
    Standardize the Markdown output format for all converted files.
    
    :param title: The title of the document.
    :param content: The extracted text/markdown content.
    :param source_type: The type of the source (e.g., 'PDF', 'Word', 'Image', 'Video', 'Audio', 'Web Link')
    :param source_path_or_url: The original path or URL of the source.
    :return: Formatted markdown string.
    """
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    markdown_template = f"""# {title}

**Source Type:** {source_type}
**Source Path/URL:** `{source_path_or_url}`
**Converted At:** {current_time}

---

{content}

---
*Converted using Universal MD Converter*
"""
    return markdown_template
