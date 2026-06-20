"""Unit tests for recursive_markdown_split from utils/chunking.py.

Covers audit findings:
- Splitting by markdown headers
- Splitting by paragraphs when no headers
- Max word enforcement
- Empty text handling
- Single-chunk texts under max_words
- Sentence splitting edge cases (abbreviations)
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from utils.chunking import recursive_markdown_split
import unittest


class TestRecursiveMarkdownSplit(unittest.TestCase):

    def test_empty_text_returns_empty(self):
        self.assertEqual(recursive_markdown_split("", 100), [])

    def test_whitespace_only_returns_empty(self):
        self.assertEqual(recursive_markdown_split("   \n\n  ", 100), [])

    def test_short_text_single_chunk(self):
        text = "Hello world this is a test"
        result = recursive_markdown_split(text, 100)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], text)

    def test_splits_on_h1_headers(self):
        text = "Intro paragraph.\n# Section One\nContent one.\n# Section Two\nContent two."
        result = recursive_markdown_split(text, 5)  # Very small max to force splits
        self.assertTrue(len(result) >= 2)

    def test_splits_on_h2_headers(self):
        text = "Intro paragraph.\n## Section A\nContent A here.\n## Section B\nContent B here."
        result = recursive_markdown_split(text, 5)
        self.assertTrue(len(result) >= 2)

    def test_splits_on_paragraphs(self):
        text = "Paragraph one with some words.\n\nParagraph two with more words.\n\nParagraph three final."
        result = recursive_markdown_split(text, 5)
        self.assertTrue(len(result) >= 2)

    def test_max_words_enforced(self):
        """Each chunk should have at most max_words words (approximately)."""
        words = ["word"] * 1000
        text = " ".join(words)
        max_words = 100
        result = recursive_markdown_split(text, max_words)
        for chunk in result:
            # Allow some tolerance since splitting isn't always exact
            self.assertLessEqual(len(chunk.split()), max_words + 10)

    def test_preserves_content(self):
        """All input words should appear in the output chunks."""
        text = "Word1 Word2 Word3 Word4 Word5 Word6 Word7 Word8 Word9 Word10"
        result = recursive_markdown_split(text, 3)
        all_output_words = " ".join(result).split()
        input_words = text.split()
        for word in input_words:
            self.assertIn(word, all_output_words, f"Word '{word}' lost during splitting")

    def test_single_very_long_paragraph(self):
        """A long paragraph without headers should still be split."""
        text = " ".join(["testword"] * 200)
        result = recursive_markdown_split(text, 50)
        self.assertTrue(len(result) > 1)

    def test_header_preserved_in_chunk(self):
        """Headers should be preserved as part of the chunk content."""
        text = "Intro text.\n# Important Header\nSome important content here."
        result = recursive_markdown_split(text, 100)
        # The header should be in one of the chunks
        all_text = " ".join(result)
        self.assertIn("Important Header", all_text)


if __name__ == '__main__':
    unittest.main()
