"""Unit tests for heuristic_validation from validate_output.py.

Covers audit findings:
- YAML frontmatter detection
- Tags detection in YAML format
- Required section checks (Core Summary)
- Optional section bonus scoring
- Short content penalty
- Footer signature check
- Score clamping (0-100)
- MIN_SCORE_THRESHOLD status logic
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from validate_output import heuristic_validation, MIN_SCORE_THRESHOLD
import unittest
from unittest.mock import patch, MagicMock


def _make_valid_markdown(content_body="Some content here to pad word count " * 5,
                          tags='["test-tag"]',
                          has_core_summary=True,
                          has_footer=True):
    """Helper to generate valid markdown for testing."""
    sections = ""
    if has_core_summary:
        sections += "\n## 🧠 Core Summary\nThis is the core summary of the document.\n"
    
    footer = "\n---\n*Converted using Universal MD Converter*\n" if has_footer else ""
    
    return f"""---
source_type: "PDF Document"
source_path: "/path/to/file.pdf"
tags: {tags}
converted_at: "2026-06-20 12:00:00"
---

# Test Title

{sections}
{content_body}
{footer}"""


class TestHeuristicValidation(unittest.TestCase):

    def test_perfect_score(self):
        """A well-formed document should score high enough to pass."""
        md = _make_valid_markdown()
        score, status, feedback = heuristic_validation(md)
        self.assertGreaterEqual(score, MIN_SCORE_THRESHOLD)
        self.assertEqual(status, "OK")

    def test_missing_frontmatter(self):
        md = "# Title\nSome content here " * 10
        score, status, feedback = heuristic_validation(md)
        self.assertTrue(any("frontmatter" in f.lower() for f in feedback))

    def test_missing_tags(self):
        md = _make_valid_markdown(tags='[]')
        score, status, feedback = heuristic_validation(md)
        self.assertTrue(any("tags" in f.lower() for f in feedback))

    def test_missing_core_summary(self):
        md = _make_valid_markdown(has_core_summary=False)
        score, status, feedback = heuristic_validation(md)
        self.assertTrue(any("core summary" in f.lower() for f in feedback))

    def test_short_content_penalty(self):
        """Content under 50 words should get a penalty."""
        md = """---
source_type: "PDF"
source_path: "/p"
tags: ["t"]
converted_at: "2026-01-01 00:00:00"
---

# T

## 🧠 Core Summary
Short.

---
*Converted using Universal MD Converter*
"""
        score, status, feedback = heuristic_validation(md)
        self.assertTrue(any("short" in f.lower() for f in feedback))

    def test_missing_footer(self):
        md = _make_valid_markdown(has_footer=False)
        score, status, feedback = heuristic_validation(md)
        self.assertTrue(any("footer" in f.lower() for f in feedback))

    def test_score_never_negative(self):
        """Even the worst document should have score clamped to 0."""
        md = "bad"
        score, status, feedback = heuristic_validation(md)
        self.assertGreaterEqual(score, 0)

    def test_score_never_above_100(self):
        """Score should be clamped at 100 even with many bonuses."""
        md = _make_valid_markdown()
        # Add optional sections for bonus
        md += "\n## 💡 Key Concepts\nConcept 1\n## 📌 Important Details\nDetail 1\n## 📝 Original Context\nQuote 1\n"
        score, status, feedback = heuristic_validation(md)
        self.assertLessEqual(score, 100)

    def test_status_ok_when_above_threshold(self):
        md = _make_valid_markdown()
        score, status, feedback = heuristic_validation(md)
        if score >= MIN_SCORE_THRESHOLD:
            self.assertEqual(status, "OK")

    def test_status_needs_reconvert_when_below_threshold(self):
        md = "Just some random text"
        score, status, feedback = heuristic_validation(md)
        if score < MIN_SCORE_THRESHOLD:
            self.assertEqual(status, "NEEDS RECONVERT")

    def test_optional_sections_bonus(self):
        """Documents with optional sections should score higher."""
        md_without = _make_valid_markdown()
        md_with = _make_valid_markdown() + "\n## 💡 Key Concepts\nSome key concepts explained.\n## 📌 Important Details\nSome details.\n"
        score_without, _, _ = heuristic_validation(md_without)
        score_with, _, _ = heuristic_validation(md_with)
        self.assertGreaterEqual(score_with, score_without)

    @patch('src.validate_output.OLLAMA_AVAILABLE', False)
    def test_llm_validation_no_ollama(self):
        from src.validate_output import llm_validation
        score, status, feedback = llm_validation("content")
        self.assertEqual(status, "ERROR")
        self.assertEqual(score, 0)
        
    @patch('src.validate_output.ollama')
    def test_llm_validation_fallback_json_regex_fail(self, mock_ollama):
        from src.validate_output import llm_validation
        # Invalid JSON that matches regex but is still invalid JSON
        mock_ollama.chat.return_value = MagicMock(message=MagicMock(content='{ "score": unquoted_string }'))
        score, status, feedback = llm_validation("content")
        self.assertEqual(status, "ERROR")
        self.assertIn("still not valid JSON", feedback[0])
        
    @patch('src.validate_output.ollama')
    def test_llm_validation_score_not_numeric(self, mock_ollama):
        from src.validate_output import llm_validation
        # Score is returned as something that float() can't parse
        mock_ollama.chat.return_value = MagicMock(message=MagicMock(content='{"score": "eighty", "status": "NEEDS RECONVERT", "feedback": []}'))
        score, status, feedback = llm_validation("content")
        self.assertEqual(score, 0)

if __name__ == '__main__':
    unittest.main()
