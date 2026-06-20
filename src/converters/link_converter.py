import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

def convert_link(url):
    try:
        # Add a simple user agent to avoid being blocked by some sites
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Fix encoding for non-UTF-8 pages (guard against apparent_encoding being None)
        if response.encoding and response.encoding.lower() == 'iso-8859-1':
            apparent = response.apparent_encoding
            if apparent:
                response.encoding = apparent

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove non-content elements
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside',
                         'form', 'noscript', 'iframe', 'svg']):
            tag.extract()

        # Prioritize <article> or <main> for the cleanest content.
        # Fall back to <body> if neither exists, and finally the whole soup.
        content_root = (
            soup.find('article')
            or soup.find('main')
            or soup.find('body')
            or soup
        )
        
        # Convert HTML to Markdown
        markdown_text = md(str(content_root), heading_style="ATX")
        result = markdown_text.strip()
        if not result:
            return ""
        return result
    except requests.exceptions.Timeout:
        return "Error extracting Web Link: Request timed out."
    except requests.exceptions.ConnectionError:
        return "Error extracting Web Link: Could not connect to the URL."
    except Exception as e:
        return f"Error extracting Web Link: {str(e)}"
