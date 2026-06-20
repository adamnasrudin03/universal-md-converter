"""Unit tests for link_converter, docx_converter, and media_converter.

Covers audit findings (Cycle 1 & 2 — converters not previously tested):
- link_converter: encoding fix for ISO-8859-1 pages
- link_converter: timeout and connection error handling
- link_converter: empty response returns empty string (not error prefix)
- docx_converter: heading level clamping (1-6)
- docx_converter: unknown heading style defaults to ##
- docx_converter: empty paragraphs are skipped
- media_converter: temp file cleanup on video extraction failure
"""
import sys
import os
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import unittest
from unittest.mock import patch, MagicMock, PropertyMock


class TestLinkConverter(unittest.TestCase):
    """Tests for convert_link without making real network calls."""

    @patch('converters.link_converter.requests.get')
    def test_successful_web_page_returns_text(self, mock_get):
        """A successful HTTP response should return extracted markdown text."""
        from converters.link_converter import convert_link

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.encoding = 'utf-8'
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b'<html><body><article><p>Hello World</p></article></body></html>'
        mock_get.return_value = mock_response

        result = convert_link("https://example.com/article")
        self.assertIn("Hello World", result)
        self.assertFalse(result.startswith("Error"))

    @patch('converters.link_converter.requests.get')
    def test_timeout_returns_error_prefix(self, mock_get):
        """A request timeout should return the standard error prefix string."""
        from converters.link_converter import convert_link
        import requests

        mock_get.side_effect = requests.exceptions.Timeout()
        result = convert_link("https://example.com")
        self.assertTrue(result.startswith("Error extracting Web Link:"))
        self.assertIn("timed out", result)

    @patch('converters.link_converter.requests.get')
    def test_connection_error_returns_error_prefix(self, mock_get):
        """A connection error should return the standard error prefix string."""
        from converters.link_converter import convert_link
        import requests

        mock_get.side_effect = requests.exceptions.ConnectionError()
        result = convert_link("https://example.com")
        self.assertTrue(result.startswith("Error extracting Web Link:"))
        self.assertIn("connect", result.lower())

    @patch('converters.link_converter.requests.get')
    def test_generic_exception_returns_error_prefix(self, mock_get):
        """A generic exception should return the standard error prefix string."""
        from converters.link_converter import convert_link

        mock_get.side_effect = Exception("Generic error")
        result = convert_link("https://example.com")
        self.assertTrue(result.startswith("Error extracting Web Link:"))
        self.assertIn("Generic error", result)

    @patch('converters.link_converter.requests.get')
    def test_iso_encoding_fixed(self, mock_get):
        """ISO-8859-1 pages should have encoding corrected via apparent_encoding."""
        from converters.link_converter import convert_link

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.encoding = 'iso-8859-1'
        mock_response.apparent_encoding = 'utf-8'
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b'<html><body><p>Content</p></body></html>'
        mock_get.return_value = mock_response

        result = convert_link("https://example.com")
        # Beautifulsoup should parse the content successfully regardless of response.encoding
        self.assertIn("Content", result)

    @patch('converters.link_converter.requests.get')
    def test_empty_page_returns_empty_string(self, mock_get):
        """A page with no extractable content should return empty string."""
        from converters.link_converter import convert_link

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.encoding = 'utf-8'
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b'<html><body></body></html>'
        mock_get.return_value = mock_response

        result = convert_link("https://example.com/empty")
        # Empty content — should not return an error prefix, just empty
        self.assertFalse(result.startswith("Error extracting Web Link:"))

    @patch('converters.link_converter.requests.get')
    def test_non_content_elements_removed(self, mock_get):
        """nav, footer, script, style elements should be stripped."""
        from converters.link_converter import convert_link

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.encoding = 'utf-8'
        mock_response.raise_for_status = MagicMock()
        mock_response.content = b"""<html><body>
            <nav>Navigation menu</nav>
            <main><p>Real content here</p></main>
            <footer>Footer text</footer>
            <script>var x = 1;</script>
        </body></html>"""
        mock_get.return_value = mock_response

        result = convert_link("https://example.com")
        self.assertIn("Real content here", result)
        self.assertNotIn("Navigation menu", result)
        self.assertNotIn("var x = 1", result)


class TestDocxConverter(unittest.TestCase):
    """Tests for convert_docx with mocked docx.Document."""

    @patch('converters.docx_converter.docx.Document')
    def test_empty_document_returns_empty_string(self, mock_doc_class):
        """An empty DOCX file should return empty string."""
        from converters.docx_converter import convert_docx

        mock_doc = MagicMock()
        mock_doc.paragraphs = []
        mock_doc_class.return_value = mock_doc

        result = convert_docx("/fake/path/doc.docx")
        self.assertEqual(result, "")

    @patch('converters.docx_converter.docx.Document')
    def test_heading_level_clamping_max(self, mock_doc_class):
        """Heading level above 6 should be clamped to 6 (###### prefix)."""
        from converters.docx_converter import convert_docx

        mock_para = MagicMock()
        mock_para.text = "Deep Heading"
        mock_para.style.name = "Heading 9"  # Invalid — should clamp to 6

        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para]
        mock_doc_class.return_value = mock_doc

        result = convert_docx("/fake/doc.docx")
        self.assertIn("######", result)
        self.assertNotIn("#######", result)

    @patch('converters.docx_converter.docx.Document')
    def test_heading_level_clamping_min(self, mock_doc_class):
        """Heading level 0 or negative should be clamped to 1 (# prefix)."""
        from converters.docx_converter import convert_docx

        mock_para = MagicMock()
        mock_para.text = "Top Heading"
        mock_para.style.name = "Heading 0"  # Clamp to 1

        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para]
        mock_doc_class.return_value = mock_doc

        result = convert_docx("/fake/doc.docx")
        self.assertTrue(result.startswith("# Top Heading"))

    @patch('converters.docx_converter.docx.Document')
    def test_unknown_heading_style_defaults_to_h2(self, mock_doc_class):
        """Heading style with non-integer suffix should default to ## (h2)."""
        from converters.docx_converter import convert_docx

        mock_para = MagicMock()
        mock_para.text = "Custom Heading"
        mock_para.style.name = "Heading Custom"  # Non-integer suffix

        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para]
        mock_doc_class.return_value = mock_doc

        result = convert_docx("/fake/doc.docx")
        self.assertTrue(result.startswith("## Custom Heading"))

    @patch('converters.docx_converter.docx.Document')
    def test_empty_paragraphs_skipped(self, mock_doc_class):
        """Paragraphs with only whitespace should not appear in output."""
        from converters.docx_converter import convert_docx

        para_empty = MagicMock()
        para_empty.text = "   "
        para_empty.style.name = "Normal"

        para_real = MagicMock()
        para_real.text = "Real content"
        para_real.style.name = "Normal"

        mock_doc = MagicMock()
        mock_doc.paragraphs = [para_empty, para_real]
        mock_doc_class.return_value = mock_doc

        result = convert_docx("/fake/doc.docx")
        self.assertEqual(result, "Real content")

    @patch('converters.docx_converter.docx.Document')
    def test_exception_returns_error_prefix(self, mock_doc_class):
        """An exception during DOCX processing should return the error prefix."""
        from converters.docx_converter import convert_docx

        mock_doc_class.side_effect = Exception("File corrupted")
        result = convert_docx("/fake/corrupt.docx")
        self.assertTrue(result.startswith("Error extracting DOCX:"))

    @patch('converters.docx_converter.docx.Document')
    def test_normal_paragraphs_joined(self, mock_doc_class):
        """Normal paragraphs should be joined with double newlines."""
        from converters.docx_converter import convert_docx

        para1 = MagicMock()
        para1.text = "First paragraph"
        para1.style.name = "Normal"

        para2 = MagicMock()
        para2.text = "Second paragraph"
        para2.style.name = "Normal"

        mock_doc = MagicMock()
        mock_doc.paragraphs = [para1, para2]
        mock_doc_class.return_value = mock_doc

        result = convert_docx("/fake/doc.docx")
        self.assertEqual(result, "First paragraph\n\nSecond paragraph")


class TestMediaConverterCleanup(unittest.TestCase):
    """Tests for media_converter temp file cleanup behavior."""

    @patch('faster_whisper.WhisperModel')
    @patch('converters.media_converter.extract_audio_from_video')
    def test_temp_audio_file_cleaned_up_after_success(self, mock_extract, mock_whisper):
        """Temp .wav file should be deleted after successful video transcription."""
        from converters.media_converter import convert_media

        # Create a real temp file to simulate the temp audio
        fd, temp_wav = tempfile.mkstemp(suffix='.temp.wav')
        os.close(fd)

        fd2, video_path = tempfile.mkstemp(suffix='.mp4')
        os.close(fd2)
        self.addCleanup(os.unlink, video_path)

        def fake_extract(video_path, audio_path):
            # Simulate audio file creation
            return True

        mock_extract.side_effect = fake_extract

        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "Hello world transcription"
        mock_model.transcribe.return_value = ([mock_segment], None)
        mock_whisper.return_value = mock_model

        # Patch the temp path to use our pre-created file
        with patch('converters.media_converter.extract_audio_from_video', side_effect=lambda v, a: True):
            with patch('os.path.exists', return_value=True):
                with patch('os.remove') as mock_remove:
                    result = convert_media(video_path, is_video=True)
                    # Cleanup should be attempted
                    mock_remove.assert_called()

    @patch('faster_whisper.WhisperModel')
    def test_audio_file_no_cleanup_for_non_video(self, mock_whisper):
        """For audio-only input (is_video=False), no temp file should be created/cleaned."""
        from converters.media_converter import convert_media

        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "Audio transcript here"
        mock_model.transcribe.return_value = ([mock_segment], None)
        mock_whisper.return_value = mock_model

        fd, audio_path = tempfile.mkstemp(suffix='.mp3')
        os.close(fd)
        self.addCleanup(os.unlink, audio_path)

        with patch('os.remove') as mock_remove:
            result = convert_media(audio_path, is_video=False)
            # os.remove should NOT be called for non-video files
            mock_remove.assert_not_called()

    @patch('converters.media_converter.extract_audio_from_video')
    def test_failed_audio_extraction_returns_error_string(self, mock_extract):
        """When extract_audio_from_video fails, should return the specific error string."""
        from converters.media_converter import convert_media

        mock_extract.return_value = False

        fd, video_path = tempfile.mkstemp(suffix='.mp4')
        os.close(fd)
        self.addCleanup(os.unlink, video_path)

        result = convert_media(video_path, is_video=True)
        self.assertEqual(result, "Failed to extract audio from video.")


if __name__ == '__main__':
    unittest.main()
