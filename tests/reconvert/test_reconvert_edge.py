import unittest
from unittest.mock import patch, MagicMock
from src.reconvert import process_with_ai, extract_raw_content, reconvert_directory
import json

class TestReconvertEdge(unittest.TestCase):
    @patch('src.reconvert.extract_global_context')
    @patch('src.reconvert.ollama')
    def test_process_with_ai_global_context(self, mock_ollama, mock_extract):
        mock_extract.return_value = "Global context"
        mock_response = [
            {'message': {'content': '{"rag_content": {"key": "value"}, "tags": ["tag1", "T@G2"]} '}}
        ]
        mock_ollama.chat.return_value = mock_response
        rag, tags = process_with_ai("raw text")
        self.assertIn("key\nvalue", rag)
        self.assertIn("tag1", tags)
        self.assertIn("tg2", tags)

    @patch('src.reconvert.extract_global_context')
    @patch('src.reconvert.ollama')
    def test_process_with_ai_object_style_stream(self, mock_ollama, mock_extract):
        mock_extract.return_value = None
        mock_response = [
            MagicMock(message=MagicMock(content='{"rag_content": "some text", "tags": [null]}'))
        ]
        mock_ollama.chat.return_value = mock_response
        rag, tags = process_with_ai("raw text")
        self.assertEqual(rag, "some text")
        self.assertEqual(len(tags), 0)

    @patch('src.reconvert.extract_global_context')
    @patch('src.reconvert.ollama')
    def test_process_with_ai_regex_fallback_fail(self, mock_ollama, mock_extract):
        mock_extract.return_value = None
        mock_response = [{'message': {'content': '{ invalid json }'}}]
        mock_ollama.chat.return_value = mock_response
        rag, tags = process_with_ai("raw text")
        self.assertIsNone(rag)

    @patch('src.reconvert.extract_global_context')
    @patch('src.reconvert.ollama')
    def test_process_with_ai_no_json(self, mock_ollama, mock_extract):
        mock_extract.return_value = None
        mock_response = [{'message': {'content': 'just plain text'}}]
        mock_ollama.chat.return_value = mock_response
        rag, tags = process_with_ai("raw text")
        self.assertIsNone(rag)

    @patch('src.reconvert.extract_global_context')
    @patch('src.reconvert.ollama')
    def test_process_with_ai_rag_content_not_string(self, mock_ollama, mock_extract):
        mock_extract.return_value = None
        mock_response = [{'message': {'content': '{"rag_content": 123}'}}]
        mock_ollama.chat.return_value = mock_response
        rag, tags = process_with_ai("raw text")
        self.assertEqual(rag, "123")

    @patch('src.reconvert.extract_global_context')
    @patch('src.reconvert.ollama')
    def test_process_with_ai_exception(self, mock_ollama, mock_extract):
        mock_extract.return_value = None
        mock_ollama.chat.side_effect = Exception("Ollama failed")
        rag, tags = process_with_ai("raw text")
        self.assertIsNone(rag)

    @patch('src.reconvert.os.walk')
    @patch('src.reconvert.validate_file')
    @patch('src.reconvert.extract_raw_content')
    @patch('src.reconvert.process_with_ai')
    @patch('src.reconvert.generate_markdown')
    def test_reconvert_directory_error_status(self, mock_gen, mock_process, mock_extract, mock_validate, mock_walk):
        mock_walk.return_value = [("root", [], ["file.md"])]
        mock_validate.side_effect = [
            {"status": "ERROR", "score": 0, "feedback": ["Error"]}, # initial check
            {"status": "ERROR", "score": 0, "feedback": ["Still error"]} # after retry
        ]
        mock_extract.return_value = ("---source_type: doc---", "raw", "")
        mock_process.return_value = ("new content", ["tag"])
        mock_gen.return_value = "new md"
        
        with patch('builtins.open', new_callable=MagicMock):
            with patch('src.reconvert.os.path.exists', return_value=False):
                reconvert_directory("test_dir", max_retries=1)
        mock_process.assert_called_once()
        mock_validate.assert_called()

    @patch('src.reconvert.os.walk')
    @patch('src.reconvert.validate_file')
    @patch('src.reconvert.extract_raw_content')
    @patch('src.reconvert.process_with_ai')
    @patch('src.reconvert.generate_markdown')
    def test_reconvert_directory_llm_returns_none(self, mock_gen, mock_process, mock_extract, mock_validate, mock_walk):
        mock_walk.return_value = [("root", [], ["file.md"])]
        mock_validate.return_value = {"status": "NEEDS RECONVERT", "score": 50, "feedback": []}
        mock_extract.return_value = ("**Source Type:** doc\n**Source Path/URL:** `url`\n", "raw", "")
        mock_process.return_value = (None, [])
        
        with patch('builtins.open', new_callable=MagicMock):
            with patch('src.reconvert.os.path.exists', return_value=True):
                reconvert_directory("test_dir", max_retries=1)
        mock_process.assert_called_once()
        mock_gen.assert_not_called()

    @patch('src.reconvert.os.walk')
    @patch('src.reconvert.validate_file')
    @patch('src.reconvert.extract_raw_content')
    def test_reconvert_directory_raw_empty(self, mock_extract, mock_validate, mock_walk):
        mock_walk.return_value = [("root", [], ["file.md"])]
        mock_validate.return_value = {"status": "NEEDS RECONVERT", "score": 50, "feedback": []}
        mock_extract.return_value = ("meta", "", "") # empty raw text
        
        with patch('builtins.open', new_callable=MagicMock) as mock_open:
            # mock raw file read to also be empty
            mock_open.return_value.__enter__.return_value.read.return_value = "  "
            with patch('src.reconvert.os.path.exists', return_value=True):
                reconvert_directory("test_dir", max_retries=1)
        
        mock_extract.assert_called_once()

    @patch('src.reconvert.ollama', None)
    def test_missing_ollama_import(self):
        pass

    @patch('src.reconvert.os.walk')
    @patch('src.reconvert.validate_file')
    @patch('src.reconvert.extract_raw_content')
    @patch('src.reconvert.process_with_ai')
    @patch('src.reconvert.generate_markdown')
    def test_reconvert_directory_success_after_retry_and_metadata_fallback(self, mock_gen, mock_process, mock_extract, mock_validate, mock_walk):
        mock_walk.return_value = [("root", [], [".hidden", "file.md", "ok_file.md"])]
        
        def validate_side_effect(path, *args, **kwargs):
            if "ok_file.md" in path:
                return {"status": "OK", "score": 100, "feedback": []}
            if "file.md" in path:
                if mock_process.call_count <= 1:
                    return {"status": "NEEDS RECONVERT", "score": 50, "feedback": ["Needs it"]}
                return {"status": "OK", "score": 100, "feedback": []}
            return {"status": "OK", "score": 100}
            
        mock_validate.side_effect = validate_side_effect
        mock_extract.return_value = ("**Source Type:** docs\n**Source Path/URL:** `my_url`\n", "raw", "")
        # First call returns bad content (causes validation fail), second call succeeds
        mock_process.side_effect = [("bad content", []), ("new content", ["tag"])]
        
        with patch('builtins.open', new_callable=MagicMock):
            with patch('src.reconvert.os.path.exists', return_value=False):
                reconvert_directory("test_dir", max_retries=2)
                
        self.assertEqual(mock_process.call_count, 2)
        self.assertEqual(mock_gen.call_count, 2)

    @patch('src.reconvert.os.walk')
    def test_reconvert_directory_empty(self, mock_walk):
        mock_walk.return_value = []
        # should return early and do nothing
        reconvert_directory("test_dir")

    @patch('src.reconvert.os.walk')
    @patch('src.reconvert.validate_file')
    @patch('src.reconvert.extract_raw_content')
    @patch('src.reconvert.process_with_ai')
    def test_reconvert_directory_all_retries_fail(self, mock_process, mock_extract, mock_validate, mock_walk):
        mock_walk.return_value = [("root", [], ["file.md"])]
        
        def validate_side_effect(path, *args, **kwargs):
            return {"status": "NEEDS RECONVERT", "score": 50, "feedback": ["Fail"]}
            
        mock_validate.side_effect = validate_side_effect
        mock_extract.return_value = ("**Source Type:** docs\n**Source Path/URL:** `url`\n", "raw", "")
        mock_process.return_value = ("new content", ["tag"])
        
        with patch('builtins.open', new_callable=MagicMock):
            with patch('src.reconvert.os.path.exists', return_value=False):
                reconvert_directory("test_dir", max_retries=2)
                
        self.assertEqual(mock_process.call_count, 2)

    @patch('src.reconvert.os.walk')
    @patch('src.reconvert.validate_file')
    @patch('src.reconvert.extract_raw_content')
    @patch('src.reconvert.process_with_ai')
    @patch('src.reconvert.generate_markdown')
    def test_reconvert_directory_force(self, mock_gen, mock_process, mock_extract, mock_validate, mock_walk):
        mock_walk.return_value = [("root", [], ["file.md"])]
        
        mock_extract.return_value = ("---source_type: doc---", "raw", "")
        mock_process.return_value = ("new content", ["tag"])
        mock_gen.return_value = "new md"
        
        # We need mock_validate to pass after retry so the loop breaks
        mock_validate.return_value = {"status": "OK", "score": 100, "feedback": []}
        
        with patch('builtins.open', new_callable=MagicMock):
            with patch('src.reconvert.os.path.exists', return_value=False):
                reconvert_directory("test_dir", max_retries=1, force=True)
                
        # validate_file should only be called once AFTER processing (the re-validation step), 
        # but NOT before processing since force skips the initial validation.
        self.assertEqual(mock_validate.call_count, 1)
        mock_process.assert_called_once()
        mock_gen.assert_called_once()


