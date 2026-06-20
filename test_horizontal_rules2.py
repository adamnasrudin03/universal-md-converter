import sys
import os
import re

def extract_raw_content_fixed(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    footer_text = "*Converted using Universal MD Converter*"
    if footer_text in content:
        footer_idx = content.rfind(footer_text)
        last_sep_idx = content.rfind("---", 0, footer_idx)
        if last_sep_idx != -1 and (footer_idx - last_sep_idx) < 10:
            content = content[:last_sep_idx].strip()
        else:
            content = content[:footer_idx].strip()
            
    separator = re.compile(r'^\s*---\s*$', re.MULTILINE)
    matches = list(separator.finditer(content))
    
    if len(matches) >= 2 and matches[0].start() < 10:
        yaml_content = content[matches[0].end():matches[1].start()]
        after_yaml = content[matches[1].end():].strip()
        if after_yaml or "source_type" in yaml_content:
            metadata = content[:matches[1].end()]
            raw_text = after_yaml
            return metadata, raw_text, ""
            
    if len(matches) >= 2:
        metadata = content[:matches[0].start()].strip()
        raw_text = content[matches[0].end():matches[-1].start()].strip()
        if metadata == "" and "source_type" in raw_text:
            return content, "", ""
        if "**source type:**" in metadata.lower() or "source_type" in metadata.lower():
            return metadata, raw_text, ""
            
    m = re.search(r'(\*\*Source Type:\*\*.*?\*\*Converted At:\*\*.*?)\n\n', content, re.DOTALL)
    if m:
        metadata = content[:m.end()].strip()
        raw_text = content[m.end():].strip()
    else:
        metadata = ""
        raw_text = content.strip()
    return metadata, raw_text, ""

metadata, raw_text, _ = extract_raw_content_fixed('test_hr.md')
print("METADATA:", repr(metadata))
print("RAW_TEXT:", repr(raw_text))

content2 = """**Source Type:** PDF Document
**Converted At:** 2026-06-20

---
Legacy Content Here
---"""
with open('test_legacy.md', 'w') as f:
    f.write(content2)

m2, r2, _ = extract_raw_content_fixed('test_legacy.md')
print("LEGACY METADATA:", repr(m2))
print("LEGACY RAW_TEXT:", repr(r2))

