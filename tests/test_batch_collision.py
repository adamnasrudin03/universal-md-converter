"""Unit tests for batch processing filename collision prevention in main.py.

Covers audit findings (Cycle 3 - HOTFIX):
- Two sources in a batch producing identical filenames must NOT overwrite each other
- global_used_filenames is passed across file boundaries
- Single-file processing is not affected (global_used_filenames defaults to None)
- Counter suffix format for collision resolution
"""
import sys
import os
import tempfile
import shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from unittest.mock import patch, MagicMock


def _make_note(filename, content="Some content", raw_chunk="raw"):
    return {"filename": filename, "content": content, "raw_chunk": raw_chunk, "tags": ["test"]}


def _get_all_md_files(directory):
    md_files = []
    for root, _, files in os.walk(directory):
        for f in files:
            if f.endswith('.md'):
                md_files.append(f)
    return md_files

class TestBatchFilenameCollision(unittest.TestCase):
    """Tests for cross-file filename deduplication in batch mode (process_source)."""

    def setUp(self):
        self.test_outdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_outdir)

    @patch('main.chunk_text_intelligently')
    @patch('main.convert_pdf')
    def test_single_file_no_collision_needed(self, mock_pdf, mock_chunk):
        """Single file call should work normally with no collision guard needed."""
        from main import process_source
        mock_pdf.return_value = "Valid content here for testing purposes."
        mock_chunk.return_value = [_make_note("doc-summary.md")]

        fd, path = tempfile.mkstemp(suffix='.pdf')
        os.close(fd)
        self.addCleanup(os.unlink, path)

        process_source(path, self.test_outdir, "llama3")

        output_files = _get_all_md_files(self.test_outdir)
        self.assertEqual(len(output_files), 1)
        self.assertIn("doc-summary.md", output_files)

    @patch('main.chunk_text_intelligently')
    @patch('main.convert_pdf')
    def test_shared_set_prevents_overwrite_in_batch(self, mock_pdf, mock_chunk):
        """Two process_source calls with shared global_used_filenames should not
        produce files with the same name (second gets a counter suffix)."""
        from main import process_source

        mock_pdf.return_value = "Valid content here for testing purposes."
        # Both files would produce the same filename slug
        mock_chunk.return_value = [_make_note("report-summary.md")]

        fd1, path1 = tempfile.mkstemp(suffix='.pdf')
        os.close(fd1)
        fd2, path2 = tempfile.mkstemp(suffix='.pdf')
        os.close(fd2)
        self.addCleanup(os.unlink, path1)
        self.addCleanup(os.unlink, path2)

        shared = set()
        process_source(path1, self.test_outdir, "llama3", global_used_filenames=shared)
        process_source(path2, self.test_outdir, "llama3", global_used_filenames=shared)

        output_files = _get_all_md_files(self.test_outdir)
        # Both files should exist but with different names
        self.assertEqual(len(output_files), 2)
        # Original and a counter-suffixed version
        self.assertIn("report-summary.md", output_files)
        # The second should have been renamed to avoid collision
        self.assertTrue(any(f != "report-summary.md" for f in output_files))

    @patch('main.chunk_text_intelligently')
    @patch('main.convert_pdf')
    def test_without_shared_set_second_call_overwrites(self, mock_pdf, mock_chunk):
        """Without a shared set, the second call to process_source WILL overwrite
        the first if they produce the same filename (demonstrates the problem)."""
        from main import process_source

        mock_pdf.return_value = "Valid content here."
        mock_chunk.return_value = [_make_note("collision-file.md")]

        fd1, path1 = tempfile.mkstemp(suffix='.pdf')
        os.close(fd1)
        fd2, path2 = tempfile.mkstemp(suffix='.pdf')
        os.close(fd2)
        self.addCleanup(os.unlink, path1)
        self.addCleanup(os.unlink, path2)

        # Each call gets its OWN set (no sharing) — old behavior
        process_source(path1, self.test_outdir, "llama3")
        process_source(path1, self.test_outdir, "llama3")

        # Without dedup, both write to the same file (only 1 file on disk)
        output_files = _get_all_md_files(self.test_outdir)
        # There will be exactly 1 unique .md file because the second overwrote the first
        self.assertEqual(len(output_files), 1)

    @patch('main.chunk_text_intelligently')
    @patch('main.convert_pdf')
    def test_counter_suffix_format(self, mock_pdf, mock_chunk):
        """Collision counter should produce stem-1.md, stem-2.md format."""
        from main import process_source

        mock_pdf.return_value = "Valid content."
        mock_chunk.return_value = [_make_note("topic-overview.md")]

        shared = set()
        paths = []
        for _ in range(3):
            fd, path = tempfile.mkstemp(suffix='.pdf')
            os.close(fd)
            paths.append(path)
            self.addCleanup(os.unlink, path)
            process_source(path, self.test_outdir, "llama3", global_used_filenames=shared)

        output_files = sorted(_get_all_md_files(self.test_outdir))
        self.assertEqual(len(output_files), 3)
        self.assertIn("topic-overview.md", output_files)
        self.assertIn("topic-overview-1.md", output_files)
        self.assertIn("topic-overview-2.md", output_files)


class TestProcessSourceGuardsUnchanged(unittest.TestCase):
    """Regression tests to ensure existing guards still work after HOTFIX."""

    def setUp(self):
        self.test_outdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_outdir)

    @patch('main.convert_pdf')
    def test_empty_content_still_aborts(self, mock_pdf):
        from main import process_source
        mock_pdf.return_value = ""
        fd, path = tempfile.mkstemp(suffix='.pdf')
        os.close(fd)
        self.addCleanup(os.unlink, path)

        result = process_source(path, self.test_outdir, "llama3")
        self.assertIsNone(result)
        # No .md files created
        self.assertEqual(_get_all_md_files(self.test_outdir), [])

    @patch('main.convert_pdf')
    def test_error_prefix_still_aborts(self, mock_pdf):
        from main import process_source
        mock_pdf.return_value = "Error extracting PDF: some error"
        fd, path = tempfile.mkstemp(suffix='.pdf')
        os.close(fd)
        self.addCleanup(os.unlink, path)

        result = process_source(path, self.test_outdir, "llama3")
        self.assertIsNone(result)

    def test_nonexistent_file_still_aborts(self):
        from main import process_source
        result = process_source("/nonexistent/path/file.pdf", self.test_outdir, "llama3")
        self.assertIsNone(result)


if __name__ == '__main__':
    unittest.main()
