import re

metadata_legacy = """# axel-jeremy-ebook-bandarmology-strategi-breakout-high-volume

**Source Type:** PDF Document
**Source Path/URL:** `/Users/adamnasrudin/Downloads/[Axel Jeremy] ebook bandarmology.pdf`
**Converted At:** 2026-06-20 11:06:52"""

m_type = re.search(r'\*\*Source Type:\*\*\s*(.*)', metadata_legacy)
m_path = re.search(r'\*\*Source Path/URL:\*\*\s*`?(.*?)`?\s*\n', metadata_legacy + '\n')
print(m_type.group(1) if m_type else "None")
print(m_path.group(1) if m_path else "None")
