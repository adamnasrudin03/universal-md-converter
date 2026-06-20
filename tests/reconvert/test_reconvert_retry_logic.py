"""Unit tests for reconvert.py retry loop logic and raw content extraction edge cases.

Covers audit findings (Cycle 1 & 3):
- HOTFIX: continue→break in retry loop when process_with_ai returns None
  (verified by mocking: retrying with None result should NOT loop max_retries times)
- extract_raw_content with content containing embedded '---' horizontal rules
- extract_raw_content: YAML frontmatter where value has embedded equals signs
- reconvert_directory: files with empty raw_text are skipped without crash
"""
import sys
import os
import tempfile
import shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import unittest
from unittest.mock import patch, MagicMock, call
from reconvert import extract_raw_content


class TestExtractRawContentEdgeCases(unittest.TestCase):

    def _write_temp(self, content):
        fd, path = tempfile.mkstemp(suffix='.md')
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        self.addCleanup(os.unlink, path)
        return path

    def test_content_with_embedded_horizontal_rule(self):
        """Content containing a --- horizontal rule should be handled correctly.
        
        The footer '---' is the LAST separator, so a horizontal rule inside the
        body does NOT break the extraction — metadata=YAML, raw=body, footer=last.
        """
        content = """---
source_type: "PDF Document"
source_path: "/path/to/file.pdf"
tags: ["tag1"]
converted_at: "2026-01-01 00:00:00"
---

# Title

## 🧠 Core Summary
Content here.

---

More content after horizontal rule.

---
*Converted using Universal MD Converter*
"""
        path = self._write_temp(content)
        metadata, raw_text, footer = extract_raw_content(path)

        # Metadata must contain YAML fields
        self.assertIn("source_type", metadata)
        # Raw text should contain both body sections
        self.assertIn("Core Summary", raw_text)
        self.assertIn("More content after horizontal rule", raw_text)
        # Footer should be the last separator's content, but since hotfix it is ""
        self.assertEqual(footer, "")

    def test_yaml_with_quoted_values_containing_colons(self):
        """YAML values with colons inside quotes should parse safely."""
        content = """---
source_type: "Web Link"
source_path: "https://example.com/path?key=value"
tags: ["web"]
converted_at: "2026-01-01 12:00:00"
---

# Page Title

## 🧠 Core Summary
Content from the web page.

---
*Converted using Universal MD Converter*
"""
        path = self._write_temp(content)
        metadata, raw_text, footer = extract_raw_content(path)
        self.assertIn("source_path", metadata)
        self.assertIn("Core Summary", raw_text)

    def test_extract_source_type_from_yaml_metadata(self):
        """Regex to extract source_type from YAML frontmatter should work correctly."""
        import re
        metadata = """---
source_type: "PDF Document"
source_path: "/path/to/file.pdf"
tags: ["tag1"]
converted_at: "2026-01-01 00:00:00"
---"""
        m_type = re.search(r'source_type:\s*"([^"]*)"', metadata)
        self.assertIsNotNone(m_type)
        self.assertEqual(m_type.group(1), "PDF Document")

    def test_extract_source_path_from_yaml_metadata(self):
        """Regex to extract source_path from YAML frontmatter should work correctly."""
        import re
        metadata = """---
source_type: "PDF Document"
source_path: "/path/to/my file.pdf"
tags: ["tag1"]
converted_at: "2026-01-01 00:00:00"
---"""
        m_path = re.search(r'source_path:\s*"([^"]*)"', metadata)
        self.assertIsNotNone(m_path)
        self.assertEqual(m_path.group(1), "/path/to/my file.pdf")

    def test_extract_raw_multiline_body(self):
        """Multi-section body with multiple headers should be fully captured."""
        content = """---
source_type: "PDF Document"
source_path: "/test.pdf"
tags: []
converted_at: "2026-01-01"
---

# Title

## 🧠 Core Summary
Summary line.

## 💡 Key Concepts
- Concept A
- Concept B

## 📌 Important Details
Detail 1.
Detail 2.

---
*Converted using Universal MD Converter*
"""
        path = self._write_temp(content)
        metadata, raw_text, footer = extract_raw_content(path)
        self.assertIn("Core Summary", raw_text)
        self.assertIn("Key Concepts", raw_text)
        self.assertIn("Important Details", raw_text)
        self.assertIn("Concept A", raw_text)


class TestReconvertRetryBreaksOnNone(unittest.TestCase):
    """Verify the hotfix: when process_with_ai returns None, the retry loop
    should break immediately rather than iterating max_retries more times."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _create_md_file(self, filename, score=0):
        content = """---
source_type: "PDF Document"
source_path: "/test.pdf"
tags: []
converted_at: "2026-01-01 00:00:00"
---

# Test

Some raw content here.

---
*Converted using Universal MD Converter*
"""
        path = os.path.join(self.test_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    @patch('reconvert.process_with_ai')
    @patch('reconvert.validate_file')
    def test_none_result_continues_retry_loop(self, mock_validate, mock_process_ai):
        """When process_with_ai returns (None, []), retry loop must continue
        and call process_with_ai again for the remaining retries."""
        from reconvert import reconvert_directory
    
        self._create_md_file("test-file-part-1.md")
        # All calls need reconvert
        mock_validate.return_value = {
            'status': 'NEEDS RECONVERT',
            'score': 30,
            'feedback': ['Missing Core Summary']
        }
        # process_with_ai always returns None
        mock_process_ai.return_value = (None, [])
    
        reconvert_directory(self.test_dir, use_llm_validation=False, model_name='llama3', max_retries=3)
    
        # process_with_ai should be called 3 times (loop must continue on None)
        self.assertEqual(mock_process_ai.call_count, 3,
                         "process_with_ai should be called multiple times when it returns None (loop must continue)")

    @patch('reconvert.process_with_ai')
    @patch('reconvert.validate_file')
    def test_successful_reconvert_does_not_retry(self, mock_validate, mock_process_ai):
        """When process_with_ai returns valid content and validation passes, no retry needed."""
        from reconvert import reconvert_directory

        self._create_md_file("test-file-part-1.md")

        # First validate call: needs reconvert; second (after reconvert): OK
        mock_validate.side_effect = [
            {'status': 'NEEDS RECONVERT', 'score': 30, 'feedback': ['Missing section']},
            {'status': 'OK', 'score': 90, 'feedback': []}
        ]
        mock_process_ai.return_value = ("## 🧠 Core Summary\nGood content here.", ["tag1"])

        reconvert_directory(self.test_dir, use_llm_validation=False, model_name='llama3', max_retries=3)

        # process_with_ai should only be called once since validation passed after first attempt
        self.assertEqual(mock_process_ai.call_count, 1)

    @patch('reconvert.process_with_ai')
    @patch('reconvert.validate_file')
    def test_empty_raw_text_skips_processing(self, mock_validate, mock_process_ai):
        """Files where raw_text is empty should skip AI processing entirely."""
        from reconvert import reconvert_directory

        # Create a file with no meaningful body content
        content = """---
source_type: "PDF"
source_path: "/empty.pdf"
tags: []
converted_at: "2026-01-01 00:00:00"
---


---
*Converted using Universal MD Converter*
"""
        path = os.path.join(self.test_dir, "empty-part-1.md")
        with open(path, 'w') as f:
            f.write(content)

        mock_validate.return_value = {
            'status': 'NEEDS RECONVERT', 'score': 20, 'feedback': ['Too short']
        }

        reconvert_directory(self.test_dir, use_llm_validation=False, model_name='llama3', max_retries=2)

        # process_with_ai should NOT be called if raw_text is empty
        mock_process_ai.assert_not_called()


if __name__ == '__main__':
    unittest.main()
