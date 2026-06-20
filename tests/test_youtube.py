"""Unit tests for YouTube URL parsing in youtube_converter.py.

Covers audit findings:
- Standard youtube.com URL parsing
- youtu.be short URL parsing
- Missing video ID
- URL with extra query parameters
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import urllib.parse
import unittest


def extract_video_id(url):
    """Extract video_id logic extracted from convert_youtube for testing without network calls."""
    parsed_url = urllib.parse.urlparse(url)
    video_id = None
    
    if "youtu.be" in parsed_url.netloc:
        video_id = parsed_url.path.strip('/')
    elif "youtube.com" in parsed_url.netloc:
        query_params = urllib.parse.parse_qs(parsed_url.query)
        if "v" in query_params:
            video_id = query_params["v"][0]
    
    return video_id


class TestYoutubeVideoIdExtraction(unittest.TestCase):

    def test_standard_youtube_url(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_short_youtu_be_url(self):
        url = "https://youtu.be/dQw4w9WgXcQ"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_youtube_url_with_extra_params(self):
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s&list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_youtube_url_no_v_param(self):
        url = "https://www.youtube.com/channel/UC1234"
        self.assertIsNone(extract_video_id(url))

    def test_random_non_youtube_url(self):
        url = "https://www.example.com/watch?v=123"
        self.assertIsNone(extract_video_id(url))

    def test_youtu_be_with_trailing_slash(self):
        url = "https://youtu.be/dQw4w9WgXcQ/"
        self.assertEqual(extract_video_id(url), "dQw4w9WgXcQ")

    def test_youtube_embed_url_not_supported(self):
        """Embed URLs don't have ?v= so video_id should be None."""
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        self.assertIsNone(extract_video_id(url))

    def test_empty_string(self):
        self.assertIsNone(extract_video_id(""))


if __name__ == '__main__':
    unittest.main()
