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
    
    # Sanitize values for YAML safety — escape embedded quotes and
    # strip newlines so multi-line strings don't break the frontmatter block.
    def _yaml_safe(value):
        s = str(value).replace('\\', '\\\\').replace('"', '\\"')
        # Collapse any newlines into spaces to keep the value on one line
        s = s.replace('\n', ' ').replace('\r', '')
        return s
    
    safe_source_type = _yaml_safe(source_type)
    safe_source_path = _yaml_safe(source_path_or_url)
    # Title appears after `# ` so just strip newlines to prevent heading injection
    safe_title = str(title).replace('\n', ' ').replace('\r', '')
    
    markdown_template = f"""---
source_type: "{safe_source_type}"
source_path: "{safe_source_path}"
tags: {tags_yaml}
converted_at: "{current_time}"
---

# {safe_title}

{content}

---
*Converted using Universal MD Converter*
"""
    return markdown_template

