"""Unit tests for generate_markdown from utils/markdown_formatter.py.

Covers audit findings:
- YAML frontmatter integrity
- YAML injection prevention (quotes, newlines in metadata)
- Tags serialization
- Footer signature presence
- Title injection prevention
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from utils.markdown_formatter import generate_markdown
import unittest
import re
import json


class TestGenerateMarkdown(unittest.TestCase):

    def _parse_frontmatter(self, md_text):
        """Extract YAML frontmatter as a dict from markdown text."""
        match = re.match(r'^---\s*\n(.*?)^---\s*$', md_text, re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(match, "Frontmatter block not found")
        yaml_block = match.group(1)
        # Simple key: "value" parser for testing (not a full YAML parser)
        result = {}
        for line in yaml_block.strip().splitlines():
            key, _, value = line.partition(':')
            result[key.strip()] = value.strip()
        return result

    def test_basic_output_structure(self):
        md = generate_markdown("Test Title", "Some content", "PDF Document", "/path/to/file.pdf", ["tag1", "tag2"])
        # Has frontmatter
        self.assertTrue(md.strip().startswith("---"))
        # Has title
        self.assertIn("# Test Title", md)
        # Has content
        self.assertIn("Some content", md)
        # Has footer
        self.assertIn("*Converted using Universal MD Converter*", md)

    def test_frontmatter_has_required_fields(self):
        md = generate_markdown("Title", "Content", "PDF Document", "/path/file.pdf", ["test"])
        fm = self._parse_frontmatter(md)
        self.assertIn("source_type", fm)
        self.assertIn("source_path", fm)
        self.assertIn("tags", fm)
        self.assertIn("converted_at", fm)

    def test_tags_serialized_as_json_array(self):
        md = generate_markdown("T", "C", "PDF", "/p", ["tag-a", "tag-b"])
        # Extract the tags line
        match = re.search(r'^tags:\s*(.+)$', md, re.MULTILINE)
        self.assertIsNotNone(match)
        tags = json.loads(match.group(1))
        self.assertEqual(tags, ["tag-a", "tag-b"])

    def test_empty_tags(self):
        md = generate_markdown("T", "C", "PDF", "/p")
        match = re.search(r'^tags:\s*(.+)$', md, re.MULTILINE)
        self.assertIsNotNone(match)
        tags = json.loads(match.group(1))
        self.assertEqual(tags, [])

    def test_none_tags(self):
        md = generate_markdown("T", "C", "PDF", "/p", None)
        match = re.search(r'^tags:\s*(.+)$', md, re.MULTILINE)
        self.assertIsNotNone(match)
        tags = json.loads(match.group(1))
        self.assertEqual(tags, [])

    def test_yaml_injection_quotes_in_source_path(self):
        """Source paths with quotes should be escaped to prevent YAML injection."""
        md = generate_markdown("Title", "Content", "PDF", '/path/with"quotes.pdf')
        # The frontmatter should still be valid — the quote should be escaped
        fm_match = re.match(r'^---\s*\n(.*?)^---\s*$', md, re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(fm_match, "Frontmatter block broken by quote injection")
        # The escaped quote should appear
        self.assertIn('\\"', md)

    def test_yaml_injection_newlines_in_source_type(self):
        """Newlines in source_type should be collapsed to prevent frontmatter breakout."""
        md = generate_markdown("Title", "Content", "PDF\ninjected: true", "/path")
        # Frontmatter should still be valid (no actual newline in the value)
        fm_match = re.match(r'^---\s*\n(.*?)^---\s*$', md, re.MULTILINE | re.DOTALL)
        self.assertIsNotNone(fm_match, "Frontmatter block broken by newline injection")
        # The source_type line should be on one line
        lines = fm_match.group(1).strip().splitlines()
        source_type_lines = [l for l in lines if l.startswith('source_type:')]
        self.assertEqual(len(source_type_lines), 1)

    def test_title_no_newline_injection(self):
        """Newlines in title should be collapsed to prevent heading injection."""
        md = generate_markdown("Title\n## Injected Heading", "Content", "PDF", "/path")
        # Count how many # Title headings exist — should be exactly one h1
        h1_matches = re.findall(r'^# .+$', md, re.MULTILINE)
        self.assertEqual(len(h1_matches), 1)

    def test_footer_always_present(self):
        md = generate_markdown("T", "C", "PDF", "/p")
        self.assertIn("*Converted using Universal MD Converter*", md)

    def test_converted_at_format(self):
        md = generate_markdown("T", "C", "PDF", "/p")
        match = re.search(r'converted_at:\s*"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})"', md)
        self.assertIsNotNone(match, "converted_at should be in YYYY-MM-DD HH:MM:SS format")


if __name__ == '__main__':
    unittest.main()
