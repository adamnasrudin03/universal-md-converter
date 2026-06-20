import sys
import os
import unittest
import tempfile
import json
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from reconvert import extract_raw_content, process_with_ai, reconvert_directory


class TestReconvertHotfixes(unittest.TestCase):

    def _write_temp(self, content, name="test.md"):
        fd, path = tempfile.mkstemp(suffix='-' + name)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(content)
        self.addCleanup(os.unlink, path)
        return path

    def test_extract_raw_content_pure_yaml(self):
        """Bug Fix: Ensure pure YAML isn't swallowed by legacy fallback."""
        content = """---
source_type: "PDF Document"
---"""
        path = self._write_temp(content)
        metadata, raw_text, footer = extract_raw_content(path)
        
        # Metadata shouldn't be empty, and raw_text shouldn't erroneously swallow the file if it's only YAML
        self.assertIn("source_type", metadata)
        self.assertEqual(raw_text, "")

    @patch('ollama.chat')
    @patch('reconvert.extract_global_context')
    def test_tags_string_hallucination(self, mock_extract_global, mock_chat):
        """Bug Fix: Ensure tags as string is handled."""
        mock_extract_global.return_value = ""
        
        # Mock ollama to return a string for tags
        mock_response = [
            MagicMock(message=MagicMock(content='{"rag_content": "some content", "tags": "trading, strategy, test"}'))
        ]
        mock_chat.return_value = mock_response

        rag_content, tags = process_with_ai("raw text here", model_name="dummy")
        
        # Tags should be correctly split and sanitized
        self.assertIn("trading", tags)
        self.assertIn("strategy", tags)
        self.assertIn("test", tags)

    @patch('reconvert.generate_markdown')
    @patch('reconvert.process_with_ai')
    @patch('reconvert.validate_file')
    @patch('reconvert.save_validation_report')
    def test_metadata_regex_and_title_parsing(self, mock_save_report, mock_validate, mock_process_ai, mock_generate_md):
        """Bug Fix: Metadata regex without quotes + .md in filename."""
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: [os.unlink(os.path.join(temp_dir, f)) for f in os.listdir(temp_dir)] + [os.rmdir(temp_dir)])
        
        # Name with .md in the middle to test title bug
        file_name = "test.md.name.md"
        file_path = os.path.join(temp_dir, file_name)
        
        content = """---
source_type: Web Link
source_path: https://example.com/test
---
Some broken text
"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
        mock_validate.side_effect = [
            {"status": "NEEDS RECONVERT", "score": 50, "feedback": ["Bad"]},
            {"status": "OK", "score": 100, "feedback": []}
        ]
        mock_process_ai.return_value = ("New content", ["tag1"])
        mock_generate_md.return_value = "Generated md"

        reconvert_directory(temp_dir, use_llm_validation=False, max_retries=1)

        # Check what was passed to generate_markdown
        mock_generate_md.assert_called_once()
        kwargs = mock_generate_md.call_args[1]
        
        # Title should NOT be "test.name", but "test.md.name"
        self.assertEqual(kwargs['title'], "test.md.name")
        
        # Regex should have captured the full unquoted strings
        self.assertEqual(kwargs['source_type'], "Web Link")
        self.assertEqual(kwargs['source_path_or_url'], "https://example.com/test")

if __name__ == '__main__':
    unittest.main()
