import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from reconvert import extract_raw_content

content = """Title of the page

Some intro text here.

---

Main content in between.

---

Conclusion text here."""

with open('test_hr.md', 'w') as f:
    f.write(content)

metadata, raw_text, footer = extract_raw_content('test_hr.md')

print("METADATA:", repr(metadata))
print("RAW_TEXT:", repr(raw_text))
