"""Unit tests for extract_raw_content from reconvert.py.

Covers audit findings:
- YAML frontmatter extraction (3-separator case)
- Legacy format fallback (2-separator case)
- Fallback for missing separators
- Metadata regex correctness for source_type and source_path
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from reconvert import extract_raw_content
import unittest
import tempfile


class TestExtractRawContent(unittest.TestCase):

    def _write_temp(self, content):
        """Write content to a temp file and return path."""
        fd, path = tempfile.mkstemp(suffix='.md')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        self.addCleanup(os.unlink, path)
        return path

    def test_yaml_frontmatter_with_footer(self):
        """Standard format: YAML frontmatter + content + footer separator."""
        content = """---
source_type: "PDF Document"
source_path: "/path/to/file.pdf"
tags: ["tag1"]
converted_at: "2026-01-01 00:00:00"
---

# Title

## 🧠 Core Summary
Some content here.

---
*Converted using Universal MD Converter*
"""
        path = self._write_temp(content)
        metadata, raw_text, footer = extract_raw_content(path)
        
        # Metadata should contain the YAML block
        self.assertIn("source_type", metadata)
        self.assertIn("source_path", metadata)
        
        # Raw text should contain the actual content and NOT the footer
        self.assertIn("Core Summary", raw_text)
        self.assertIn("Some content here", raw_text)
        self.assertNotIn("Universal MD Converter", raw_text)
        
        # The footer return is now obsolete / empty string
        self.assertEqual(footer, "")

    def test_yaml_with_internal_horizontal_rule(self):
        """Content containing '---' should NOT be chopped."""
        content = """---
source_type: "PDF"
---

# Title
Some text.

---

More text after rule.

---
*Converted using Universal MD Converter*
"""
        path = self._write_temp(content)
        metadata, raw_text, footer = extract_raw_content(path)
        self.assertIn("More text after rule.", raw_text)

    def test_legacy_two_separator_format(self):
        """Legacy format with only two separators."""
        content = """---

Some raw text content here.

---"""
        path = self._write_temp(content)
        metadata, raw_text, footer = extract_raw_content(path)
        
        self.assertIn("raw text content", raw_text)

    def test_no_separators_fallback(self):
        """When no --- separators exist, should return full content as raw_text."""
        content = "Just some plain text without any markdown structure."
        path = self._write_temp(content)
        metadata, raw_text, footer = extract_raw_content(path)
        
        self.assertEqual(raw_text, content)
        self.assertEqual(metadata, "")
        self.assertEqual(footer, "")

    def test_legacy_bold_format(self):
        """Legacy format with **Source Type:** etc."""
        content = """**Source Type:** PDF Document
**Source Path/URL:** /path/to/file.pdf
**Converted At:** 2026-01-01 00:00:00

Some actual content here.

*Converted using Universal MD Converter*"""
        path = self._write_temp(content)
        metadata, raw_text, footer = extract_raw_content(path)
        
        self.assertIn("Source Type", metadata)
        self.assertIn("Some actual content", raw_text)

    def test_empty_file(self):
        """Empty file should not crash."""
        path = self._write_temp("")
        metadata, raw_text, footer = extract_raw_content(path)
        self.assertEqual(raw_text, "")


if __name__ == '__main__':
    unittest.main()
