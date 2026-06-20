import sys
import os
import unittest
import tempfile
import shutil
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from reconvert import _yaml_unescape, extract_raw_content, reconvert_directory

class TestReconvertUnescapeAndContext(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_yaml_unescape_helper(self):
        """Verify _yaml_unescape resolves escaped quotes, double backslashes, and strips outer quotes."""
        self.assertEqual(_yaml_unescape(None), None)
        self.assertEqual(_yaml_unescape(""), "")
        self.assertEqual(_yaml_unescape('"C:\\\\path\\\\to\\\\file.pdf"'), "C:\\path\\to\\file.pdf")
        self.assertEqual(_yaml_unescape("'C:\\\\path\\\\to\\\\file.pdf'"), "C:\\path\\to\\file.pdf")
        self.assertEqual(_yaml_unescape('"https://example.com/search?q=\\"test\\""'), 'https://example.com/search?q="test"')
        self.assertEqual(_yaml_unescape('unquoted-simple'), 'unquoted-simple')

    @patch('reconvert.generate_markdown')
    @patch('reconvert.process_with_ai')
    @patch('reconvert.validate_file')
    @patch('reconvert.save_validation_report')
    def test_reconvert_preserves_source_context(self, mock_save_report, mock_validate, mock_process_ai, mock_generate_md):
        """Verify source_context is parsed from old frontmatter and passed back to generate_markdown."""
        file_path = os.path.join(self.test_dir, "test_context.md")
        content = """---
source_type: "PDF Document"
source_path: "C:\\\\test.pdf"
source_context: "Bagian 2 dari 5 | Bab 1"
tags: []
converted_at: "2026-01-01"
---
Some content
"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        mock_validate.side_effect = [
            {"status": "NEEDS RECONVERT", "score": 50, "feedback": ["Bad"]},
            {"status": "OK", "score": 100, "feedback": []}
        ]
        mock_process_ai.return_value = ("New content", ["tag1"])
        mock_generate_md.return_value = "Generated md"

        reconvert_directory(self.test_dir, use_llm_validation=False, max_retries=1)

        # Check the arguments to generate_markdown
        mock_generate_md.assert_called_once()
        kwargs = mock_generate_md.call_args[1]
        self.assertEqual(kwargs['source_context'], "Bagian 2 dari 5 | Bab 1")
        # Ensure backslashes are resolved to single backslash
        self.assertEqual(kwargs['source_path_or_url'], "C:\\test.pdf")

    @patch('reconvert.generate_markdown')
    @patch('reconvert.process_with_ai')
    @patch('reconvert.validate_file')
    @patch('reconvert.save_validation_report')
    def test_reconvert_handles_leading_whitespace_metadata(self, mock_save_report, mock_validate, mock_process_ai, mock_generate_md):
        """Verify that metadata with leading whitespace/newlines still matches YAML frontmatter correctly."""
        file_path = os.path.join(self.test_dir, "test_whitespace.md")
        content = """

---
source_type: "PDF Document"
source_path: "C:\\\\test.pdf"
tags: []
converted_at: "2026-01-01"
---
Some content
"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        mock_validate.side_effect = [
            {"status": "NEEDS RECONVERT", "score": 50, "feedback": ["Bad"]},
            {"status": "OK", "score": 100, "feedback": []}
        ]
        mock_process_ai.return_value = ("New content", ["tag1"])
        mock_generate_md.return_value = "Generated md"

        reconvert_directory(self.test_dir, use_llm_validation=False, max_retries=1)

        mock_generate_md.assert_called_once()
        kwargs = mock_generate_md.call_args[1]
        self.assertEqual(kwargs['source_type'], "PDF Document")
        self.assertEqual(kwargs['source_path_or_url'], "C:\\test.pdf")

    @patch('reconvert.generate_markdown')
    @patch('reconvert.process_with_ai')
    @patch('reconvert.validate_file')
    @patch('reconvert.save_validation_report')
    def test_reconvert_prevent_truncation_on_quotes(self, mock_save_report, mock_validate, mock_process_ai, mock_generate_md):
        """Verify that metadata values containing quotes (like search query URLs) are parsed completely without truncation."""
        file_path = os.path.join(self.test_dir, "test_quotes.md")
        content = """---
source_type: "Web Link"
source_path: "https://example.com/search?q=\\"test\\""
tags: []
converted_at: "2026-01-01"
---
Some content
"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        mock_validate.side_effect = [
            {"status": "NEEDS RECONVERT", "score": 50, "feedback": ["Bad"]},
            {"status": "OK", "score": 100, "feedback": []}
        ]
        mock_process_ai.return_value = ("New content", ["tag1"])
        mock_generate_md.return_value = "Generated md"

        reconvert_directory(self.test_dir, use_llm_validation=False, max_retries=1)

        mock_generate_md.assert_called_once()
        kwargs = mock_generate_md.call_args[1]
        self.assertEqual(kwargs['source_path_or_url'], 'https://example.com/search?q="test"')

if __name__ == '__main__':
    unittest.main()
