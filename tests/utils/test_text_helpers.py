"""Unit tests for safe_truncate and get_recommended_model from utils/text_helpers.py.

Covers audit findings:
- Word-boundary truncation behavior
- Edge cases: empty string, exact length, very long strings without spaces
- 80% threshold for space-based truncation
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from utils.text_helpers import safe_truncate
import unittest


class TestSafeTruncate(unittest.TestCase):

    def test_short_text_unchanged(self):
        text = "Hello world"
        self.assertEqual(safe_truncate(text, 100), text)

    def test_exact_length_unchanged(self):
        text = "a" * 100
        self.assertEqual(safe_truncate(text, 100), text)

    def test_truncates_at_word_boundary(self):
        text = "Hello world this is a test of truncation"
        # Should break at a space, not mid-word
        result = safe_truncate(text, 20)
        self.assertFalse(result.endswith("thi"))
        self.assertTrue(len(result) <= 20)

    def test_empty_string(self):
        self.assertEqual(safe_truncate("", 100), "")

    def test_no_spaces_hard_cut(self):
        """When no spaces exist near the truncation point, hard-cut at max_chars."""
        text = "a" * 200
        result = safe_truncate(text, 100)
        self.assertEqual(len(result), 100)

    def test_space_at_80_percent_threshold(self):
        """Spaces below 80% of max_chars should be ignored (hard-cut instead)."""
        # Create text with space only at position 10 out of 100 (10% = below threshold)
        text = "a" * 10 + " " + "b" * 100
        result = safe_truncate(text, 100)
        # Space at position 10 is < 80% of 100, so should hard-cut at 100
        self.assertEqual(len(result), 100)

    def test_space_above_80_percent_threshold(self):
        """Spaces above 80% of max_chars should be used as break point."""
        # Create text with space at position 85 out of 100
        text = "a" * 85 + " " + "b" * 50
        result = safe_truncate(text, 100)
        # Should break at the space (position 85)
        self.assertEqual(len(result), 85)

    def test_preserves_content_when_within_limit(self):
        text = "word1 word2 word3"
        self.assertEqual(safe_truncate(text, 4000), text)

    def test_max_chars_zero(self):
        """Edge case: max_chars=0 should return empty."""
        self.assertEqual(safe_truncate("hello", 0), "")

    def test_clean_raw_text_empty(self):
        from utils.text_helpers import clean_raw_text
        self.assertEqual(clean_raw_text(""), "")
        self.assertEqual(clean_raw_text(None), None)

    def test_clean_raw_text_cleaning(self):
        from utils.text_helpers import clean_raw_text
        raw = "  Line 1   \t\n\n\n\n  Line 2  "
        self.assertEqual(clean_raw_text(raw), "Line 1\n\nLine 2")

from unittest.mock import patch, MagicMock, mock_open
from src.utils.text_helpers import get_recommended_model

class TestGetRecommendedModel(unittest.TestCase):
    @patch('src.utils.text_helpers.platform.system')
    @patch('src.utils.text_helpers.subprocess.run')
    def test_get_recommended_model_mac_large_ram(self, mock_run, mock_system):
        mock_system.return_value = "Darwin"
        mock_run.return_value = MagicMock(returncode=0, stdout="34359738368\n") # 32GB
        self.assertEqual(get_recommended_model(), "llama3")

    @patch('src.utils.text_helpers.platform.system')
    @patch('src.utils.text_helpers.subprocess.run')
    def test_get_recommended_model_mac_small_ram(self, mock_run, mock_system):
        mock_system.return_value = "Darwin"
        mock_run.return_value = MagicMock(returncode=0, stdout="8589934592\n") # 8GB
        self.assertEqual(get_recommended_model(), "llama3.2")

    @patch('src.utils.text_helpers.platform.system')
    @patch('src.utils.text_helpers.subprocess.run')
    def test_get_recommended_model_mac_subprocess_error(self, mock_run, mock_system):
        mock_system.return_value = "Darwin"
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        self.assertEqual(get_recommended_model(), "llama3.2")

    @patch('src.utils.text_helpers.platform.system')
    def test_get_recommended_model_exception(self, mock_system):
        mock_system.side_effect = Exception("General error")
        self.assertEqual(get_recommended_model(), "llama3.2")

    @patch('src.utils.text_helpers.platform.system')
    def test_get_recommended_model_linux_large(self, mock_system):
        mock_system.return_value = "Linux"
        mock_open = MagicMock()
        mock_open.return_value.__enter__.return_value = ["MemTotal:       33554432 kB\n"] # 32GB
        with patch('builtins.open', mock_open):
            self.assertEqual(get_recommended_model(), "llama3")

    @patch('src.utils.text_helpers.platform.system')
    def test_get_recommended_model_linux_16gb(self, mock_system):
        mock_system.return_value = "Linux"
        with patch("builtins.open", mock_open(read_data="MemTotal:       16777216 kB\n")) as mock_file:
            model = get_recommended_model()
            self.assertEqual(model, "llama3")

    @patch('src.utils.text_helpers.platform.system')
    def test_get_recommended_model_linux_8gb(self, mock_system):
        mock_system.return_value = "Linux"
        with patch("builtins.open", mock_open(read_data="MemTotal:       8388608 kB\n")) as mock_file:
            model = get_recommended_model()
            self.assertEqual(model, "llama3.2")

    @patch('src.utils.text_helpers.platform.system')
    def test_get_recommended_model_windows(self, mock_system):
        mock_system.return_value = "Windows"
        self.assertEqual(get_recommended_model(), "llama3.2")

    @patch('src.utils.text_helpers.platform.system')
    def test_get_recommended_model_linux_no_memtotal(self, mock_system):
        mock_system.return_value = "Linux"
        with patch("builtins.open", mock_open(read_data="OtherInfo: 123 kB\nAnotherInfo: 456 kB\n")) as mock_file:
            self.assertEqual(get_recommended_model(), "llama3.2")

if __name__ == '__main__':
    unittest.main()

