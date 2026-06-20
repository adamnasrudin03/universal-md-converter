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

    @patch('ollama.chat')
    @patch('reconvert.extract_global_context')
    def test_process_with_ai_markdown_json_wrapping(self, mock_extract_global, mock_chat):
        """Bug Fix: Ensure JSON wrapped in ```json ... ``` is handled safely."""
        mock_extract_global.return_value = ""
        
        # Mock ollama to return json wrapped in markdown
        mock_response = [
            MagicMock(message=MagicMock(content='```json\n{"rag_content": "some content", "tags": "testing"}\n```'))
        ]
        mock_chat.return_value = mock_response

        rag_content, tags = process_with_ai("raw text here", model_name="dummy", temperature=0.0)
        
        # Tags should be parsed correctly despite the markdown
        self.assertEqual(rag_content, "some content")
        self.assertIn("testing", tags)

    @patch('reconvert.generate_markdown')
    @patch('reconvert.process_with_ai')
    @patch('reconvert.validate_file')
    @patch('reconvert.save_validation_report')
    def test_reconvert_escalating_temperature(self, mock_save_report, mock_validate, mock_process_ai, mock_generate_md):
        """Feature: Ensure Deep Audit Hotfix correctly escalates temperature over 3 retries."""
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: [os.unlink(os.path.join(temp_dir, f)) for f in os.listdir(temp_dir)] + [os.rmdir(temp_dir)])
        
        file_path = os.path.join(temp_dir, "temp_test.md")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("Some text\n")
            
        # Mock validation to fail initially, then fail 2 times inside the loop, and succeed on the 3rd
        mock_validate.side_effect = [
            {"status": "NEEDS RECONVERT", "score": 50, "feedback": ["Initial"]},
            {"status": "NEEDS RECONVERT", "score": 50, "feedback": ["Attempt 1"]},
            {"status": "NEEDS RECONVERT", "score": 50, "feedback": ["Attempt 2"]},
            {"status": "OK", "score": 100, "feedback": []}
        ]
        
        mock_process_ai.return_value = ("New content", ["tag"])
        mock_generate_md.return_value = "Generated md"

        reconvert_directory(temp_dir, use_llm_validation=False, max_retries=3)

        # Ensure process_with_ai was called 3 times
        self.assertEqual(mock_process_ai.call_count, 3)
        
        # Verify temperatures were escalating (0.0, 0.3, 0.7)
        calls = mock_process_ai.call_args_list
        self.assertEqual(calls[0][1]['temperature'], 0.0)
        self.assertEqual(calls[1][1]['temperature'], 0.3)
        self.assertEqual(calls[2][1]['temperature'], 0.7)

    def test_extract_raw_content_horizontal_rules(self):
        """Bug Fix: Ensure markdown with horizontal rules but no metadata is not destroyed."""
        content = """Title of the page

Some intro text here.

---

Main content in between.

---

Conclusion text here."""
        path = self._write_temp(content)
        metadata, raw_text, footer = extract_raw_content(path)
        
        # Metadata should be empty because there's no source_type, and raw_text should be the whole content.
        self.assertEqual(metadata, "")
        self.assertEqual(raw_text, content.strip())

    @patch('reconvert.generate_markdown')
    @patch('reconvert.process_with_ai')
    @patch('reconvert.validate_file')
    @patch('reconvert.save_validation_report')
    def test_metadata_regex_single_quotes(self, mock_save_report, mock_validate, mock_process_ai, mock_generate_md):
        """Bug Fix: Ensure YAML frontmatter with single quotes is parsed properly."""
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: [os.unlink(os.path.join(temp_dir, f)) for f in os.listdir(temp_dir)] + [os.rmdir(temp_dir)])
        
        file_path = os.path.join(temp_dir, "test.md")
        content = """---
source_type: 'PDF Document'
source_path: 'local/path/to/file.pdf'
---
Text content
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
        
        # Single quotes should be stripped
        self.assertEqual(kwargs['source_type'], "PDF Document")
        self.assertEqual(kwargs['source_path_or_url'], "local/path/to/file.pdf")

    @patch('ollama.chat')
    @patch('reconvert.extract_global_context')
    def test_process_with_ai_formats_nested_dict_headers(self, mock_extract_global, mock_chat):
        """Bug Fix: Ensure nested dicts from LLM get proper Markdown headers, especially for Core Summary."""
        mock_extract_global.return_value = ""
        
        # Mock LLM returning a nested dict instead of markdown
        nested_json = {
            "rag_content": {
                "Core Summary": "This is a summary",
                "Key Concepts": "These are concepts"
            },
            "tags": []
        }
        mock_response = [
            MagicMock(message=MagicMock(content=json.dumps(nested_json)))
        ]
        mock_chat.return_value = mock_response

        rag_content, tags = process_with_ai("raw text here", model_name="dummy")
        
        # Ensure it prefixed with ## and the emoji for Core Summary
        self.assertIn("## 🧠 Core Summary\nThis is a summary", rag_content)
        self.assertIn("## Key Concepts\nThese are concepts", rag_content)

    @patch('reconvert.generate_markdown')
    @patch('reconvert.process_with_ai')
    @patch('reconvert.validate_file')
    @patch('reconvert.save_validation_report')
    def test_reconvert_directory_continues_on_none_llm_response(self, mock_save_report, mock_validate, mock_process_ai, mock_generate_md):
        """Bug Fix: Ensure a None return from LLM doesn't break the retry loop."""
        temp_dir = tempfile.mkdtemp()
        self.addCleanup(lambda: [os.unlink(os.path.join(temp_dir, f)) for f in os.listdir(temp_dir)] + [os.rmdir(temp_dir)])
        
        file_path = os.path.join(temp_dir, "test_none.md")
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write("Some text\n")
            
        mock_validate.side_effect = [
            {"status": "NEEDS RECONVERT", "score": 40, "feedback": ["Bad"]},
            {"status": "OK", "score": 100, "feedback": []}
        ]
        
        # First attempt: LLM fails (returns None). Second attempt: LLM succeeds.
        mock_process_ai.side_effect = [
            (None, []),
            ("Valid Content", ["tag"])
        ]
        mock_generate_md.return_value = "Generated md"

        reconvert_directory(temp_dir, use_llm_validation=False, max_retries=2)

        # Ensure process_with_ai was called 2 times (retry loop didn't break early)
        self.assertEqual(mock_process_ai.call_count, 2)
        mock_generate_md.assert_called_once()

if __name__ == '__main__':
    unittest.main()
