"""Unit tests for process_source error handling in main.py.

Covers audit findings:
- Empty content guard
- Error prefix detection
- Unsupported file extension
- File not found
"""
import sys
import os
import tempfile
import shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import process_source, sanitize_basename
import unittest
from unittest.mock import patch


class TestProcessSourceErrorGuards(unittest.TestCase):

    def setUp(self):
        self.test_outdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_outdir)

    def test_file_not_found_graceful(self):
        """Should print error and return None for non-existent file."""
        result = process_source("/non/existent/file.pdf", self.test_outdir, "llama3")
        self.assertIsNone(result)
        # No crash = pass

    def test_unsupported_extension_graceful(self):
        """Should print error and return None for unsupported file types."""
        fd, path = tempfile.mkstemp(suffix='.xyz')
        os.close(fd)
        self.addCleanup(os.unlink, path)
        
        result = process_source(path, self.test_outdir, "llama3")
        self.assertIsNone(result)

    @patch('main.convert_pdf')
    @patch('main.chunk_text_intelligently')
    def test_empty_content_aborts(self, mock_chunk, mock_pdf):
        """Should abort when converter returns empty content."""
        mock_pdf.return_value = ""
        
        fd, path = tempfile.mkstemp(suffix='.pdf')
        os.close(fd)
        self.addCleanup(os.unlink, path)
        
        result = process_source(path, self.test_outdir, "llama3")
        self.assertIsNone(result)
        mock_chunk.assert_not_called()

    @patch('main.convert_pdf')
    @patch('main.chunk_text_intelligently')
    def test_error_prefix_aborts(self, mock_chunk, mock_pdf):
        """Should abort when converter returns an error string."""
        mock_pdf.return_value = "Error extracting PDF: file is corrupted"
        
        fd, path = tempfile.mkstemp(suffix='.pdf')
        os.close(fd)
        self.addCleanup(os.unlink, path)
        
        result = process_source(path, self.test_outdir, "llama3")
        self.assertIsNone(result)
        mock_chunk.assert_not_called()

    @patch('main.convert_pdf')
    @patch('main.chunk_text_intelligently')
    def test_whitespace_only_content_aborts(self, mock_chunk, mock_pdf):
        """Should abort when converter returns whitespace-only content."""
        mock_pdf.return_value = "   \n\n  \t  "
        
        fd, path = tempfile.mkstemp(suffix='.pdf')
        os.close(fd)
        self.addCleanup(os.unlink, path)
        
        result = process_source(path, self.test_outdir, "llama3")
        self.assertIsNone(result)
        mock_chunk.assert_not_called()


if __name__ == '__main__':
    unittest.main()
