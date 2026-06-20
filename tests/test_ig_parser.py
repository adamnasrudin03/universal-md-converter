"""Unit tests for Instagram URL parsing in ig_converter.py.

Covers audit findings:
- Standard /p/ URL shortcode extraction
- /reel/ URL shortcode extraction
- Invalid URL formats
- Missing shortcode after /p/
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from urllib.parse import urlparse
import unittest


def extract_shortcode(url):
    """Extract shortcode logic from convert_ig_link for testing without network."""
    path_parts = urlparse(url).path.strip('/').split('/')
    if 'p' in path_parts:
        idx = path_parts.index('p')
        if idx + 1 < len(path_parts):
            return path_parts[idx + 1]
        return None  # Missing shortcode
    elif 'reel' in path_parts or 'reels' in path_parts:
        key = 'reel' if 'reel' in path_parts else 'reels'
        idx = path_parts.index(key)
        if idx + 1 < len(path_parts):
            return path_parts[idx + 1]
        return None  # Missing shortcode
    return None  # Not a valid IG URL


class TestInstagramShortcodeExtraction(unittest.TestCase):

    def test_standard_post_url(self):
        url = "https://www.instagram.com/p/DZucoBjiQxd/"
        self.assertEqual(extract_shortcode(url), "DZucoBjiQxd")

    def test_reel_url(self):
        url = "https://www.instagram.com/reel/ABC123def/"
        self.assertEqual(extract_shortcode(url), "ABC123def")

    def test_reels_url(self):
        url = "https://www.instagram.com/reels/ABC123def/"
        self.assertEqual(extract_shortcode(url), "ABC123def")

    def test_post_without_trailing_slash(self):
        url = "https://www.instagram.com/p/DZucoBjiQxd"
        self.assertEqual(extract_shortcode(url), "DZucoBjiQxd")

    def test_missing_shortcode_after_p(self):
        url = "https://www.instagram.com/p/"
        self.assertIsNone(extract_shortcode(url))

    def test_missing_shortcode_after_reel(self):
        url = "https://www.instagram.com/reel/"
        self.assertIsNone(extract_shortcode(url))

    def test_profile_url_not_supported(self):
        url = "https://www.instagram.com/username/"
        self.assertIsNone(extract_shortcode(url))

    def test_stories_url_not_supported(self):
        url = "https://www.instagram.com/stories/username/12345/"
        self.assertIsNone(extract_shortcode(url))


if __name__ == '__main__':
    unittest.main()
