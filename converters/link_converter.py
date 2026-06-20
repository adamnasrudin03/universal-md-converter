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

        # Remove scripts and styles
        for script_or_style in soup(['script', 'style', 'nav', 'footer', 'header']):
            script_or_style.extract()

        html_content = str(soup)
        
        # Convert HTML to Markdown
        markdown_text = md(html_content, heading_style="ATX")
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
