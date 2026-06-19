import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

def convert_link(url):
    try:
        # Add a simple user agent to avoid being blocked by some sites
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        # Parse HTML
        soup = BeautifulSoup(response.text, 'html.parser')

        # Remove scripts and styles
        for script_or_style in soup(['script', 'style', 'nav', 'footer', 'header']):
            script_or_style.extract()

        html_content = str(soup)
        
        # Convert HTML to Markdown
        markdown_text = md(html_content, heading_style="ATX")
        return markdown_text.strip()
    except Exception as e:
        return f"Error extracting Web Link: {str(e)}"
