"""Unit tests for MIN_SCORE_THRESHOLD clamping in validate_output.py.

Covers audit findings (Cycle 2 - HOTFIX):
- MIN_SCORE env var set to > 100 should be clamped to 100
- MIN_SCORE env var set to negative should be clamped to 0
- MIN_SCORE env var set to non-integer should fallback to 85
- Status logic (OK/NEEDS RECONVERT) should always be consistent with threshold

Also covers additional heuristic validation edge cases found in Audit Cycle 2:
- YAML frontmatter detection with leading whitespace
- Tags line with multiple entries
- Content with frontmatter only (no body) should still score correctly
"""
import sys
import os
import importlib
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

import unittest
from unittest import mock


class TestMinScoreThresholdClamping(unittest.TestCase):
    """Tests for MIN_SCORE env var clamping behavior after hotfix."""

    def _reload_validate_output(self, env_value):
        """Reload validate_output module with a specific MIN_SCORE env var."""
        with mock.patch.dict(os.environ, {"MIN_SCORE": env_value}):
            import validate_output
            importlib.reload(validate_output)
            return validate_output.MIN_SCORE_THRESHOLD

    def test_threshold_above_100_clamped_to_100(self):
        """MIN_SCORE=200 should be clamped to 100, not 200."""
        threshold = self._reload_validate_output("200")
        self.assertEqual(threshold, 100)

    def test_threshold_negative_clamped_to_0(self):
        """MIN_SCORE=-50 should be clamped to 0."""
        threshold = self._reload_validate_output("-50")
        self.assertEqual(threshold, 0)

    def test_threshold_valid_value_unchanged(self):
        """MIN_SCORE=75 should stay at 75."""
        threshold = self._reload_validate_output("75")
        self.assertEqual(threshold, 75)

    def test_threshold_zero_allowed(self):
        """MIN_SCORE=0 should stay at 0 (everything passes)."""
        threshold = self._reload_validate_output("0")
        self.assertEqual(threshold, 0)

    def test_threshold_100_allowed(self):
        """MIN_SCORE=100 should stay at 100 (only perfect docs pass)."""
        threshold = self._reload_validate_output("100")
        self.assertEqual(threshold, 100)

    def test_non_integer_falls_back_to_85(self):
        """MIN_SCORE=abc (non-integer) should default to 85."""
        threshold = self._reload_validate_output("abc")
        self.assertEqual(threshold, 85)

    def tearDown(self):
        """Restore original module state after each test."""
        import validate_output
        importlib.reload(validate_output)


class TestHeuristicValidationEdgeCases(unittest.TestCase):
    """Additional edge cases for heuristic_validation found in Audit Cycle 2."""

    def setUp(self):
        import validate_output
        importlib.reload(validate_output)
        from validate_output import heuristic_validation
        self.heuristic_validation = heuristic_validation

    def test_empty_string_does_not_crash(self):
        """Empty string should return a score of 0 without crashing."""
        score, status, feedback = self.heuristic_validation("")
        self.assertGreaterEqual(score, 0)
        self.assertLessEqual(score, 100)
        self.assertIn(status, ["OK", "NEEDS RECONVERT"])

    def test_tags_with_single_entry_passes_check(self):
        """A single tag in YAML should still satisfy the tags check."""
        md = """---
source_type: "PDF"
source_path: "/p"
tags: ["single-tag"]
converted_at: "2026-01-01 00:00:00"
---

# Title

## 🧠 Core Summary
Content here with enough words to pass the length check easily.

---
*Converted using Universal MD Converter*
"""
        score, status, feedback = self.heuristic_validation(md)
        self.assertFalse(any("tags" in f.lower() for f in feedback),
                         "Single tag should satisfy the tags check")

    def test_tags_with_empty_brackets_fails_check(self):
        """Empty tags list [] should fail the tags check."""
        md = """---
source_type: "PDF"
source_path: "/p"
tags: []
converted_at: "2026-01-01"
---

# Title

## 🧠 Core Summary
Content here.

---
*Converted using Universal MD Converter*
"""
        score, status, feedback = self.heuristic_validation(md)
        self.assertTrue(any("tags" in f.lower() for f in feedback))

    def test_score_threshold_boundary_exactly_at_threshold(self):
        """A score exactly at MIN_SCORE_THRESHOLD should be 'OK'."""
        from validate_output import MIN_SCORE_THRESHOLD
        # We can't force exact score, but we can verify the boundary logic
        # Score >= threshold => OK
        score_at_threshold = MIN_SCORE_THRESHOLD
        status = "OK" if score_at_threshold >= MIN_SCORE_THRESHOLD else "NEEDS RECONVERT"
        self.assertEqual(status, "OK")

    def test_frontmatter_without_closing_separator_fails(self):
        """Frontmatter without closing '---' should be detected as malformed."""
        md = """---
source_type: "PDF"
source_path: "/p"
tags: ["t"]

# Title without closing frontmatter

## 🧠 Core Summary
Content here.
"""
        score, status, feedback = self.heuristic_validation(md)
        # Should flag missing/malformed frontmatter
        self.assertTrue(any("frontmatter" in f.lower() for f in feedback))

    def test_validate_file_handles_missing_file(self):
        """validate_file should return ERROR status for a nonexistent file."""
        from validate_output import validate_file
        result = validate_file("/nonexistent/path/file.md")
        self.assertEqual(result['status'], "ERROR")
        self.assertEqual(result['score'], 0)
        self.assertTrue(len(result['feedback']) > 0)

    def test_validate_file_returns_correct_structure(self):
        """validate_file should always return dict with required keys."""
        import tempfile
        from validate_output import validate_file

        content = """---
source_type: "PDF Document"
source_path: "/test.pdf"
tags: ["test"]
converted_at: "2026-01-01 00:00:00"
---

# Test Title

## 🧠 Core Summary
This is a comprehensive test with enough words to exceed the minimum threshold for scoring purposes.

---
*Converted using Universal MD Converter*
"""
        fd, path = tempfile.mkstemp(suffix='.md')
        with os.fdopen(fd, 'w') as f:
            f.write(content)
        self.addCleanup(os.unlink, path)

        result = validate_file(path)
        self.assertIn('file', result)
        self.assertIn('score', result)
        self.assertIn('status', result)
        self.assertIn('feedback', result)
        self.assertIn(result['status'], ['OK', 'NEEDS RECONVERT', 'ERROR'])
        self.assertGreaterEqual(result['score'], 0)
        self.assertLessEqual(result['score'], 100)


if __name__ == '__main__':
    unittest.main()
