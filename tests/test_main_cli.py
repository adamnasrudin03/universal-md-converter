import os
import sys
from unittest.mock import patch, MagicMock
from src.main import ensure_model_installed, sanitize_basename, process_source, main

class TestMainCLI:

    @patch('src.main.ollama')
    def test_ensure_model_installed_already_installed(self, mock_ollama):
        # mock ollama.list() to return model_name
        class MockList:
            models = [MagicMock(model='llama3')]
        mock_ollama.list.return_value = MockList()
        
        ensure_model_installed('llama3')
        mock_ollama.pull.assert_not_called()

    @patch('src.main.ollama')
    def test_ensure_model_installed_not_installed(self, mock_ollama):
        class MockList:
            pass
        mock_ollama.list.return_value = MockList()
        # Fallback to get empty list since hasattr fails on dict vs mock object
        # but mock obj returns empty list when models is accessed if not set? Wait.
        # Actually in main.py, it uses hasattr(model_list, 'models')
        # If true, available = [m.model for m in model_list.models]
        # Else, available = [m.get('name', m.get('model', '')) for m in model_list.get('models', [])]
        
        mock_ollama.list.return_value = {'models': [{'name': 'other_model'}]}
        
        ensure_model_installed('llama3')
        mock_ollama.pull.assert_called_once_with('llama3')

    @patch('src.main.ollama')
    def test_ensure_model_installed_exception(self, mock_ollama):
        mock_ollama.list.side_effect = Exception("Connection refused")
        try:
            ensure_model_installed('llama3')
        except SystemExit:
            pass
        except Exception as e:
            assert False, "Should raise SystemExit on connection error"

    def test_sanitize_basename(self):
        assert sanitize_basename("Hello World!") == "hello-world"
        assert sanitize_basename("  spaces  and -- hyphens  ") == "spaces-and-hyphens"
        assert sanitize_basename("") == "untitled"

    @patch('src.main.convert_link')
    @patch('src.main.chunk_text_intelligently')
    @patch('src.main.generate_markdown')
    @patch('src.main.os.makedirs')
    @patch('builtins.open', new_callable=MagicMock)
    def test_process_source_url(self, mock_open, mock_makedirs, mock_gen, mock_chunk, mock_convert):
        mock_convert.return_value = "URL text"
        mock_chunk.return_value = [{"filename": "url.md", "content": "RAG", "raw_chunk": "raw", "tags": []}]
        mock_gen.return_value = "MD content"
        
        process_source("http://example.com", "outdir", "model")
        mock_convert.assert_called_once()
        mock_chunk.assert_called_once()
        mock_gen.assert_called_once()
        mock_open.assert_called()

    @patch('src.main.convert_youtube')
    @patch('src.main.chunk_text_intelligently')
    def test_process_source_youtube(self, mock_chunk, mock_convert):
        mock_convert.return_value = "YT text"
        mock_chunk.return_value = [{"filename": "yt.md", "content": "RAG", "raw_chunk": "raw", "tags": []}]
        with patch('builtins.open', new_callable=MagicMock):
            process_source("https://youtube.com/watch?v=123", "outdir", "model")
            mock_convert.assert_called_once()

    @patch('src.main.convert_ig_link')
    @patch('src.main.chunk_text_intelligently')
    def test_process_source_ig(self, mock_chunk, mock_convert):
        mock_convert.return_value = "IG text"
        mock_chunk.return_value = [{"filename": "ig.md", "content": "RAG", "raw_chunk": "raw", "tags": []}]
        with patch('builtins.open', new_callable=MagicMock):
            process_source("https://instagram.com/p/123", "outdir", "model")
            mock_convert.assert_called_once()

    @patch('src.main.os.path.exists')
    def test_process_source_file_not_found(self, mock_exists):
        mock_exists.return_value = False
        # Should return without doing anything
        process_source("missing.pdf", "outdir", "model")

    @patch('src.main.os.path.exists')
    @patch('src.main.convert_pdf')
    @patch('src.main.chunk_text_intelligently')
    def test_process_source_file_pdf(self, mock_chunk, mock_convert, mock_exists):
        mock_exists.return_value = True
        mock_convert.return_value = "PDF text"
        mock_chunk.return_value = [{"filename": "doc.md", "content": "RAG", "raw_chunk": "raw", "tags": []}]
        with patch('builtins.open', new_callable=MagicMock):
            process_source("file.pdf", "outdir", "model")
            mock_convert.assert_called_once()

    @patch('src.main.os.path.exists')
    @patch('src.main.convert_docx')
    @patch('src.main.chunk_text_intelligently')
    def test_process_source_file_docx(self, mock_chunk, mock_convert, mock_exists):
        mock_exists.return_value = True
        mock_convert.return_value = "DOCX text"
        mock_chunk.return_value = [{"filename": "doc.md", "content": "RAG", "raw_chunk": "raw", "tags": []}]
        with patch('builtins.open', new_callable=MagicMock):
            process_source("file.docx", "outdir", "model")
            mock_convert.assert_called_once()

    @patch('src.main.os.path.exists')
    @patch('src.main.convert_image')
    @patch('src.main.chunk_text_intelligently')
    def test_process_source_file_image(self, mock_chunk, mock_convert, mock_exists):
        mock_exists.return_value = True
        mock_convert.return_value = "Image text"
        mock_chunk.return_value = [{"filename": "doc.md", "content": "RAG", "raw_chunk": "raw", "tags": []}]
        with patch('builtins.open', new_callable=MagicMock):
            process_source("file.png", "outdir", "model")
            mock_convert.assert_called_once()

    @patch('src.main.os.path.exists')
    @patch('src.main.convert_media')
    @patch('src.main.chunk_text_intelligently')
    def test_process_source_file_audio(self, mock_chunk, mock_convert, mock_exists):
        mock_exists.return_value = True
        mock_convert.return_value = "Audio text"
        mock_chunk.return_value = [{"filename": "doc.md", "content": "RAG", "raw_chunk": "raw", "tags": []}]
        with patch('builtins.open', new_callable=MagicMock):
            process_source("file.mp3", "outdir", "model")
            mock_convert.assert_called_once_with("file.mp3", is_video=False)

    @patch('src.main.os.path.exists')
    @patch('src.main.convert_media')
    @patch('src.main.chunk_text_intelligently')
    def test_process_source_file_video(self, mock_chunk, mock_convert, mock_exists):
        mock_exists.return_value = True
        mock_convert.return_value = "Video text"
        mock_chunk.return_value = [{"filename": "doc.md", "content": "RAG", "raw_chunk": "raw", "tags": []}]
        with patch('builtins.open', new_callable=MagicMock):
            process_source("file.mp4", "outdir", "model")
            mock_convert.assert_called_once_with("file.mp4", is_video=True)

    @patch('src.main.os.path.exists')
    def test_process_source_unsupported_ext(self, mock_exists):
        mock_exists.return_value = True
        # Should return without extracting
        process_source("file.unknown", "outdir", "model")

    @patch('src.main.os.path.exists')
    @patch('src.main.convert_pdf')
    def test_process_source_converter_error(self, mock_convert, mock_exists):
        mock_exists.return_value = True
        mock_convert.return_value = "Error extracting PDF: Something failed"
        # Should abort early
        process_source("file.pdf", "outdir", "model")

    @patch('src.main.os.path.exists')
    @patch('src.main.convert_pdf')
    def test_process_source_empty_content(self, mock_convert, mock_exists):
        mock_exists.return_value = True
        mock_convert.return_value = "   "
        # Should abort early
        process_source("file.pdf", "outdir", "model")

    @patch('src.main.os.path.exists')
    @patch('src.main.convert_pdf')
    @patch('src.main.chunk_text_intelligently')
    def test_process_source_no_atomic_notes(self, mock_chunk, mock_convert, mock_exists):
        mock_exists.return_value = True
        mock_convert.return_value = "PDF text"
        mock_chunk.return_value = [] # Empty notes
        # Should abort early
        process_source("file.pdf", "outdir", "model")

    @patch('src.main.argparse.ArgumentParser.parse_args')
    @patch('src.main.ensure_model_installed')
    @patch('src.main.os.path.isdir')
    @patch('src.main.process_source')
    def test_main_single_source(self, mock_proc, mock_isdir, mock_ensure, mock_args):
        mock_args.return_value = MagicMock(source="file.pdf", outdir="out", model="model")
        mock_isdir.return_value = False # Not a directory
        
        main()
        mock_proc.assert_called_once_with("file.pdf", "out", "model")

    @patch('src.main.argparse.ArgumentParser.parse_args')
    @patch('src.main.ensure_model_installed')
    @patch('src.main.os.path.isdir')
    @patch('src.main.os.walk')
    @patch('src.main.process_source')
    def test_main_batch_directory(self, mock_proc, mock_walk, mock_isdir, mock_ensure, mock_args):
        mock_args.return_value = MagicMock(source="dir", outdir="out", model="model")
        mock_isdir.return_value = True
        mock_walk.return_value = [("root", [], ["file1.pdf", ".hidden", "file2.docx"])]
        
        main()
        assert mock_proc.call_count == 2 # file1.pdf and file2.docx

    @patch('src.main.main')
    def test_main_block(self, mock_main):
        import runpy
        runpy.run_module('src.main', run_name='__main__')
        mock_main.assert_called_once()
