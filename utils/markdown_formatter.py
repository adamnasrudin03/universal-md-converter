import datetime
import json

def generate_markdown(title, content, source_type, source_path_or_url, tags=None):
    """
    Standardize the Markdown output format for all converted files using YAML Frontmatter.
    
    :param title: The title of the document.
    :param content: The extracted text/markdown content.
    :param source_type: The type of the source (e.g., 'PDF', 'Word', 'Image', 'Video', 'Audio', 'Web Link')
    :param source_path_or_url: The original path or URL of the source.
    :param tags: A list of tags for the document.
    :return: Formatted markdown string.
    """
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tags_yaml = json.dumps(tags or [])
    
    markdown_template = f"""---
source_type: "{source_type}"
source_path: "{source_path_or_url}"
tags: {tags_yaml}
converted_at: "{current_time}"
---

# {title}

{content}

---
*Converted using Universal MD Converter*
"""
    return markdown_template
