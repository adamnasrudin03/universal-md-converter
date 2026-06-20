import datetime
import json
import re

def generate_markdown(title, content, source_type, source_path_or_url, tags=None, source_context=None):
    """
    Standardize the Markdown output format for all converted files using YAML Frontmatter.
    
    :param title: The title of the document.
    :param content: The extracted text/markdown content.
    :param source_type: The type of the source (e.g., 'PDF', 'Word', 'Image', 'Video', 'Audio', 'Web Link')
    :param source_path_or_url: The original path or URL of the source.
    :param tags: A list of tags for the document.
    :param source_context: Information about the page or chapter of the chunk.
    :return: Formatted markdown string.
    """
    current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    tags_yaml = json.dumps(tags or [])
    
    # Normalize standard headers to enforce correct emojis and markdown formatting
    if content:
        # Normalize Core Summary
        content = re.sub(
            r'^#{0,3}\s*(?:[^\w\s\n]*\s*)?Core Summary\s*$',
            r'## 🧠 Core Summary',
            content,
            flags=re.IGNORECASE | re.MULTILINE
        )
        # Normalize Key Concepts & Definitions
        content = re.sub(
            r'^#{0,3}\s*(?:[^\w\s\n]*\s*)?Key Concepts(?:\s*&\s*Definitions)?\s*$',
            r'## 💡 Key Concepts & Definitions',
            content,
            flags=re.IGNORECASE | re.MULTILINE
        )
        # Normalize Important Details / Application
        content = re.sub(
            r'^#{0,3}\s*(?:[^\w\s\n]*\s*)?Important Details(?:\s*/\s*Application)?\s*$',
            r'## 📌 Important Details / Application',
            content,
            flags=re.IGNORECASE | re.MULTILINE
        )
        # Normalize Original Context & Quotes
        content = re.sub(
            r'^#{0,3}\s*(?:[^\w\s\n]*\s*)?Original Context(?:\s*&\s*Quotes)?\s*$',
            r'## 📝 Original Context & Quotes',
            content,
            flags=re.IGNORECASE | re.MULTILINE
        )

    # Sanitize values for YAML safety — escape embedded quotes and
    # strip newlines so multi-line strings don't break the frontmatter block.
    def _yaml_safe(value):
        s = str(value).replace('\\', '\\\\').replace('"', '\\"')
        # Collapse any newlines into spaces to keep the value on one line
        s = s.replace('\n', ' ').replace('\r', '')
        return s
    
    safe_source_type = _yaml_safe(source_type)
    safe_source_path = _yaml_safe(source_path_or_url)
    
    # Optional source_context injection
    source_context_yaml = ""
    if source_context and str(source_context).strip(): # pragma: no cover
        safe_context = _yaml_safe(source_context)
        source_context_yaml = f'\nsource_context: "{safe_context}"'
        
    # Title appears after `# ` so just strip newlines to prevent heading injection
    safe_title = str(title).replace('\n', ' ').replace('\r', '')
    
    markdown_template = f"""---
source_type: "{safe_source_type}"
source_path: "{safe_source_path}"{source_context_yaml}
tags: {tags_yaml}
converted_at: "{current_time}"
---

# {safe_title}

{content}

---
*Converted using Universal MD Converter*
"""
    return markdown_template

