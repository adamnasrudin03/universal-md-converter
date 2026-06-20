"""Unit tests for sanitize_basename from main.py.

Covers edge cases found during audit:
- Special characters, unicode, empty input
- Leading/trailing hyphens
- All-special-char input → 'untitled'
- Multiple spaces/hyphens collapsing
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from main import sanitize_basename
import unittest


class TestSanitizeBasename(unittest.TestCase):

    def test_basic_name(self):
        self.assertEqual(sanitize_basename("my document"), "my-document")

    def test_special_characters_removed(self):
        self.assertEqual(sanitize_basename("hello@world!"), "helloworld")

    def test_mixed_case_lowered(self):
        self.assertEqual(sanitize_basename("MyDoc-Name"), "mydoc-name")

    def test_multiple_spaces_collapsed(self):
        self.assertEqual(sanitize_basename("word   with   spaces"), "word-with-spaces")

    def test_multiple_hyphens_collapsed(self):
        self.assertEqual(sanitize_basename("my---doc---name"), "my-doc-name")

    def test_leading_trailing_hyphens_stripped(self):
        self.assertEqual(sanitize_basename("---hello---"), "hello")

    def test_empty_string_returns_untitled(self):
        self.assertEqual(sanitize_basename(""), "untitled")

    def test_all_special_chars_returns_untitled(self):
        self.assertEqual(sanitize_basename("@#$%^&*()"), "untitled")

    def test_unicode_removed(self):
        result = sanitize_basename("dokumen-tes 📄")
        self.assertEqual(result, "dokumen-tes")

    def test_whitespace_only_returns_untitled(self):
        self.assertEqual(sanitize_basename("   "), "untitled")

    def test_path_like_input(self):
        # Basename extraction happens before sanitize, but test the sanitizer itself
        result = sanitize_basename("[Axel Jeremy] ebook bandarmology")
        self.assertEqual(result, "axel-jeremy-ebook-bandarmology")

    def test_numeric_input(self):
        self.assertEqual(sanitize_basename("12345"), "12345")

    def test_hyphen_only_returns_untitled(self):
        self.assertEqual(sanitize_basename("---"), "untitled")


if __name__ == '__main__':
    unittest.main()
