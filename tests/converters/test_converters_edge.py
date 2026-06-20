import pytest
from unittest.mock import patch, MagicMock
import os

# --- ig_converter.py ---
from converters.ig_converter import convert_ig_link

class TestIgConverter:
    @patch('converters.ig_converter.instaloader.Instaloader')
    def test_convert_ig_invalid_url(self, mock_loader):
        res = convert_ig_link("https://instagram.com/just_profile")
        assert "Error" in res

    @patch('converters.ig_converter.convert_image')
    @patch('converters.ig_converter.os.walk')
    @patch('converters.ig_converter.instaloader.Instaloader')
    @patch('converters.ig_converter.instaloader.Post.from_shortcode')
    def test_convert_ig_valid(self, mock_post, mock_loader, mock_walk, mock_convert_image):
        mock_instance = MagicMock()
        mock_loader.return_value = mock_instance
        
        mock_post_obj = MagicMock()
        mock_post_obj.caption = "This is a test caption"
        mock_post.return_value = mock_post_obj
        
        # Mock os.walk to simulate found images
        mock_walk.return_value = [('/temp', [], ['1.jpg', '2.png', '3.txt'])]
        mock_convert_image.side_effect = ["OCR slide 1", "Error extracting Image text: fake", "  "]
        
        res = convert_ig_link("https://instagram.com/p/SHORTCODE")
        assert "This is a test caption" in res
        assert "OCR slide 1" in res
        assert "OCR could not extract text" in res

    @patch('converters.ig_converter.instaloader.Instaloader')
    def test_convert_ig_exception(self, mock_loader):
        mock_loader.side_effect = Exception("Instaloader error")
        res = convert_ig_link("https://instagram.com/p/SHORTCODE")
        assert "Error extracting IG" in res or "Error extracting Instagram" in res
        assert "Instaloader error" in res

# --- image_converter.py ---
from converters.image_converter import convert_image

class TestImageConverter:
    @patch('converters.image_converter.ImageEnhance')
    @patch('pytesseract.image_to_string')
    @patch('converters.image_converter.Image.open')
    def test_convert_image_success(self, mock_open, mock_ocr, mock_enhance):
        mock_img = MagicMock()
        mock_open.return_value = mock_img
        mock_ocr.return_value = "Extracted OCR text"
        
        res = convert_image("dummy.png")
        assert "Extracted OCR text" in res

    @patch('converters.image_converter.ImageEnhance')
    @patch('pytesseract.image_to_string')
    @patch('converters.image_converter.Image.open')
    def test_convert_image_fallback(self, mock_open, mock_ocr, mock_enhance):
        mock_img = MagicMock()
        mock_open.return_value = mock_img
        
        mock_ocr.side_effect = [Exception("Tesseract error"), "Fallback OCR text"]
        
        res = convert_image("dummy.png")
        assert "Fallback OCR text" in res
        
    def test_convert_image_exception(self):
        res = convert_image("non_existent_file.png")
        assert "Error extracting Image text" in res

    @patch('converters.image_converter.ImageEnhance')
    @patch('pytesseract.image_to_string')
    @patch('converters.image_converter.Image.open')
    def test_convert_image_empty_text(self, mock_open, mock_ocr, mock_enhance):
        mock_img = MagicMock()
        mock_open.return_value = mock_img
        mock_ocr.return_value = "   \n\t  "
        res = convert_image("dummy.png")
        assert res == ""

# --- media_converter.py ---
from converters.media_converter import convert_media

class TestMediaConverter:
    @patch('faster_whisper.WhisperModel')
    @patch('converters.media_converter.os.path.exists')
    def test_convert_media_success(self, mock_exists, mock_load):
        mock_exists.return_value = True
        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "Transcribed audio text"
        mock_model.transcribe.return_value = ([mock_segment], None)
        mock_load.return_value = mock_model
        
        res = convert_media("dummy.mp4")
        assert "Transcribed audio text" in res

    def test_convert_media_file_not_found(self):
        res = convert_media("non_existent.mp4")
        assert "Error" in res

    @patch('faster_whisper.WhisperModel')
    @patch('converters.media_converter.os.path.exists')
    def test_convert_media_empty_text(self, mock_exists, mock_load):
        mock_exists.return_value = True
        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "   "
        mock_model.transcribe.return_value = ([mock_segment], None)
        mock_load.return_value = mock_model
        
        res = convert_media("dummy.mp4")
        assert res == ""

    @patch('faster_whisper.WhisperModel')
    @patch('converters.media_converter.os.path.exists')
    def test_convert_media_exception(self, mock_exists, mock_load):
        mock_exists.return_value = True
        mock_load.side_effect = Exception("Whisper error")
        res = convert_media("dummy.mp4")
        assert "Error transcribing media" in res

    @patch('converters.media_converter.extract_audio_from_video')
    @patch('faster_whisper.WhisperModel')
    @patch('converters.media_converter.os.path.exists')
    @patch('converters.media_converter.os.remove')
    def test_convert_media_video_success(self, mock_remove, mock_exists, mock_load, mock_extract):
        mock_extract.return_value = True
        mock_exists.return_value = True
        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "Video Text"
        mock_model.transcribe.return_value = ([mock_segment], None)
        mock_load.return_value = mock_model
        
        res = convert_media("test.mp4", is_video=True)
        assert res == "Video Text"
        mock_remove.assert_called_once_with("test.mp4.temp.wav")
        
    @patch('converters.media_converter.extract_audio_from_video')
    @patch('faster_whisper.WhisperModel')
    @patch('converters.media_converter.os.path.exists')
    @patch('converters.media_converter.os.remove')
    def test_convert_media_video_remove_fail(self, mock_remove, mock_exists, mock_load, mock_extract):
        mock_extract.return_value = True
        mock_exists.return_value = True
        mock_remove.side_effect = Exception("Failed to remove")
        mock_model = MagicMock()
        mock_segment = MagicMock()
        mock_segment.text = "Video Text"
        mock_model.transcribe.return_value = ([mock_segment], None)
        mock_load.return_value = mock_model
        
        res = convert_media("test.mp4", is_video=True)
        assert res == "Video Text" # Exception should be ignored

    @patch('converters.media_converter.extract_audio_from_video')
    @patch('converters.media_converter.os.path.exists')
    def test_convert_media_video_extract_fail(self, mock_exists, mock_extract):
        mock_exists.return_value = True
        mock_extract.return_value = False
        res = convert_media("test.mp4", is_video=True)
        assert res == "Failed to extract audio from video."

    @patch('converters.media_converter.VideoFileClip')
    def test_extract_audio_from_video_success(self, mock_video_class):
        mock_video = MagicMock()
        mock_video.audio = MagicMock()
        mock_video_class.return_value = mock_video
        
        from converters.media_converter import extract_audio_from_video
        res = extract_audio_from_video("test.mp4", "out.wav")
        assert res is True
        mock_video.audio.write_audiofile.assert_called_once_with("out.wav", verbose=False, logger=None)
        mock_video.close.assert_called_once()

    @patch('converters.media_converter.VideoFileClip')
    def test_extract_audio_from_video_no_audio(self, mock_video_class):
        mock_video = MagicMock()
        mock_video.audio = None
        mock_video_class.return_value = mock_video
        
        from converters.media_converter import extract_audio_from_video
        res = extract_audio_from_video("test.mp4", "out.wav")
        assert res is False

    @patch('converters.media_converter.VideoFileClip')
    def test_extract_audio_from_video_exception(self, mock_video_class):
        mock_video_class.side_effect = Exception("Video error")
        from converters.media_converter import extract_audio_from_video
        res = extract_audio_from_video("test.mp4", "out.wav")
        assert res is False

    @patch('converters.media_converter.VideoFileClip')
    def test_extract_audio_from_video_close_exception(self, mock_video_class):
        mock_video = MagicMock()
        mock_video.close.side_effect = Exception("Close error")
        mock_video_class.return_value = mock_video
        from converters.media_converter import extract_audio_from_video
        res = extract_audio_from_video("test.mp4", "out.wav")
        assert res is True # Exception ignored

import unittest
from converters.ig_converter import convert_ig_link
class TestIGConverterEdgeCases(unittest.TestCase):
    @patch('converters.ig_converter.instaloader.Instaloader')
    @patch('converters.ig_converter.instaloader.Post')
    @patch('converters.ig_converter.tempfile.mkdtemp')
    @patch('converters.ig_converter.shutil.rmtree')
    def test_convert_ig_link_missing_shortcode(self, mock_rmtree, mock_mkdtemp, mock_post, mock_loader):
        res1 = convert_ig_link("https://www.instagram.com/p/")
        self.assertIn("Missing shortcode", res1)

        res2 = convert_ig_link("https://www.instagram.com/reel/")
        self.assertIn("Missing shortcode", res2)

        res3 = convert_ig_link("https://www.instagram.com/reels/")
        self.assertIn("Missing shortcode", res3)

    @patch('converters.ig_converter.instaloader.Instaloader')
    @patch('converters.ig_converter.instaloader.Post')
    @patch('converters.ig_converter.tempfile.mkdtemp')
    @patch('converters.ig_converter.os.walk')
    @patch('converters.ig_converter.shutil.rmtree')
    def test_convert_ig_link_caption_and_no_images(self, mock_rmtree, mock_walk, mock_mkdtemp, mock_post, mock_loader):
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        
        mock_post_instance = MagicMock()
        mock_post_instance.caption = "This is a caption"
        mock_post.from_shortcode.return_value = mock_post_instance
        
        mock_mkdtemp.return_value = "tempdir"
        mock_walk.return_value = [] # No files
        
        res = convert_ig_link("https://www.instagram.com/p/ABC123def/")
        self.assertIn("This is a caption", res)
        self.assertIn("No image slides found", res)

    @patch('converters.ig_converter.instaloader.Instaloader')
    @patch('converters.ig_converter.instaloader.Post')
    @patch('converters.ig_converter.tempfile.mkdtemp')
    @patch('converters.ig_converter.os.walk')
    @patch('converters.ig_converter.shutil.rmtree')
    @patch('converters.ig_converter.convert_image')
    def test_convert_ig_link_reels_success(self, mock_convert_image, mock_rmtree, mock_walk, mock_mkdtemp, mock_post, mock_loader):
        mock_loader_instance = MagicMock()
        mock_loader.return_value = mock_loader_instance
        
        mock_post_instance = MagicMock()
        mock_post_instance.caption = ""
        mock_post.from_shortcode.return_value = mock_post_instance
        
        mock_mkdtemp.return_value = "tempdir"
        mock_walk.return_value = [("tempdir", [], ["test.png"])]
        mock_convert_image.return_value = "Slide text OCR"
        
        res = convert_ig_link("https://www.instagram.com/reels/ABC123def/")
        self.assertIn("Slide text OCR", res)

# --- pdf_converter.py ---
from converters.pdf_converter import convert_pdf

class TestPdfConverter:
    @patch('converters.pdf_converter.fitz')
    def test_convert_pdf_success(self, mock_fitz):
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "This is a very long text that is definitely more than fifty characters long to bypass the OCR fallback check in PyMuPDF."
        # Simulate iterable pages
        mock_pdf.__iter__.return_value = [mock_page]
        mock_fitz.open.return_value.__enter__.return_value = mock_pdf
        
        res = convert_pdf("dummy.pdf")
        assert "This is a very long text" in res

    @patch('PIL.ImageEnhance')
    @patch('pytesseract.image_to_string')
    @patch('converters.pdf_converter.fitz')
    def test_convert_pdf_fallback_ocr(self, mock_fitz, mock_ocr, mock_enhance):
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "" 
        
        mock_pix = MagicMock()
        mock_pix.width = 100
        mock_pix.height = 100
        mock_pix.samples = b'\x00' * 30000
        mock_page.get_pixmap.return_value = mock_pix
        
        mock_pdf.__iter__.return_value = [mock_page]
        mock_fitz.open.return_value.__enter__.return_value = mock_pdf
        
        mock_ocr.return_value = "OCR fallback text"
        
        res = convert_pdf("dummy.pdf")
        assert "OCR fallback text" in res

    @patch('PIL.ImageEnhance')
    @patch('pytesseract.image_to_string')
    @patch('converters.pdf_converter.fitz')
    def test_convert_pdf_fallback_ocr_exception(self, mock_fitz, mock_ocr, mock_enhance):
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "" 
        
        mock_pix = MagicMock()
        mock_pix.width = 100
        mock_pix.height = 100
        mock_pix.samples = b'\x00' * 30000
        mock_page.get_pixmap.return_value = mock_pix
        mock_pdf.__iter__.return_value = [mock_page]
        mock_fitz.open.return_value.__enter__.return_value = mock_pdf
        
        mock_ocr.side_effect = Exception("OCR error")
        
        res = convert_pdf("dummy.pdf")
        assert res == "" 

    def test_convert_pdf_exception(self):
        res = convert_pdf("non_existent.pdf")
        assert "Error extracting PDF" in res

    @patch('converters.pdf_converter.fitz')
    def test_convert_pdf_long_text_skips_ocr(self, mock_fitz):
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        # Text is > 50 characters, should skip OCR entirely
        mock_page.get_text.return_value = "This is a very long text that is definitely more than fifty characters long to bypass the OCR fallback check."
        mock_pdf.__iter__.return_value = [mock_page]
        mock_fitz.open.return_value.__enter__.return_value = mock_pdf
        
        res = convert_pdf("dummy.pdf")
        assert "This is a very long text" in res

    @patch('PIL.ImageEnhance')
    @patch('pytesseract.image_to_string')
    @patch('converters.pdf_converter.fitz')
    def test_convert_pdf_ocr_shorter_than_text(self, mock_fitz, mock_ocr, mock_enhance):
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Short text" # < 50 chars, triggers OCR
        
        mock_pix = MagicMock()
        mock_pix.width = 100
        mock_pix.height = 100
        mock_pix.samples = b'\x00' * 30000
        mock_page.get_pixmap.return_value = mock_pix
        mock_pdf.__iter__.return_value = [mock_page]
        mock_fitz.open.return_value.__enter__.return_value = mock_pdf
        
        mock_ocr.return_value = "OCR" # Shorter than "Short text"
        
        res = convert_pdf("dummy.pdf")
        assert "Short text" in res # Should keep original text

# --- youtube_converter.py ---
from converters.youtube_converter import convert_youtube

class TestYoutubeConverterEdge:
    def test_convert_youtube_invalid_url(self):
        res = convert_youtube("https://youtube.com/not-a-video")
        assert "Error extracting YouTube: Invalid URL format" in res

    @patch('converters.youtube_converter.TextFormatter.format_transcript')
    @patch('converters.youtube_converter.YouTubeTranscriptApi.list')
    def test_convert_youtube_success_id(self, mock_list, mock_formatter):
        mock_transcript_list = MagicMock()
        mock_transcript_obj = MagicMock()
        mock_transcript_obj.fetch.return_value = [{"text": "Hello world"}]
        mock_transcript_list.find_transcript.return_value = mock_transcript_obj
        mock_list.return_value = mock_transcript_list
        mock_formatter.return_value = "Hello world"
        
        res = convert_youtube("https://youtube.com/watch?v=VIDEOID")
        assert "Hello world" in res

    @patch('converters.youtube_converter.TextFormatter.format_transcript')
    @patch('converters.youtube_converter.YouTubeTranscriptApi.list')
    def test_convert_youtube_fallback_language(self, mock_list, mock_formatter):
        mock_transcript_list = MagicMock()
        mock_transcript_obj = MagicMock()
        mock_transcript_obj.fetch.return_value = [{"text": "Bonjour"}]
        
        mock_transcript_list.find_transcript.side_effect = [Exception("Not found"), mock_transcript_obj]
        
        mock_t1 = MagicMock()
        mock_t1.language_code = 'fr'
        mock_transcript_list.__iter__.return_value = iter([mock_t1])
        
        mock_list.return_value = mock_transcript_list
        mock_formatter.return_value = "Bonjour"
        
        res = convert_youtube("https://youtube.com/watch?v=VIDEOID")
        assert "Bonjour" in res

    @patch('converters.youtube_converter.YouTubeTranscriptApi.list')
    def test_convert_youtube_no_transcripts(self, mock_list):
        mock_transcript_list = MagicMock()
        mock_transcript_list.find_transcript.side_effect = Exception("Not found")
        mock_transcript_list.__iter__.return_value = iter([])
        mock_list.return_value = mock_transcript_list
        
        res = convert_youtube("https://youtube.com/watch?v=VIDEOID")
        assert "No transcripts available" in res

    @patch('converters.youtube_converter.YouTubeTranscriptApi.list')
    def test_convert_youtube_empty_transcript(self, mock_list):
        mock_transcript_list = MagicMock()
        mock_transcript_obj = MagicMock()
        mock_transcript_obj.fetch.return_value = []
        mock_transcript_list.find_transcript.return_value = mock_transcript_obj
        mock_list.return_value = mock_transcript_list
        
        res = convert_youtube("https://youtube.com/watch?v=VIDEOID")
        assert "Transcript is empty" in res

    @patch('converters.youtube_converter.YouTubeTranscriptApi.list')
    def test_convert_youtube_exception(self, mock_list):
        mock_list.side_effect = Exception("Network error")
        res = convert_youtube("https://youtube.com/watch?v=VIDEOID")
        assert "Error extracting YouTube: Network error" in res

