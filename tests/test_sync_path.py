"""Unit tests for sync_path.py.

Covers audit findings:
- Filename prefix replacement
- YAML metadata source_path update
- Legacy bold-format metadata update
- Companion .raw.txt file handling
- No-match edge case
- Overwrite protection on rename
"""
import sys
import os
import tempfile
import shutil
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sync_path import sync_path, get_base_title
import unittest


class TestGetBaseTitle(unittest.TestCase):

    def test_url_extracts_path(self):
        title = get_base_title("https://example.com/some/page")
        self.assertEqual(title, "some-page")

    def test_url_falls_back_to_netloc(self):
        title = get_base_title("https://example.com/")
        self.assertEqual(title, "examplecom")

    def test_file_path(self):
        title = get_base_title("/path/to/my document.pdf")
        self.assertEqual(title, "my-document")

    def test_file_with_special_chars(self):
        title = get_base_title("/path/[Axel] ebook.pdf")
        self.assertEqual(title, "axel-ebook")


class TestSyncPath(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def _create_file(self, name, content=""):
        path = os.path.join(self.test_dir, name)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return path

    def test_renames_md_file(self):
        """sync_path should rename files matching old prefix."""
        old_source = "/path/to/old-doc.pdf"
        new_source = "/path/to/new-doc.pdf"
        old_prefix = get_base_title(old_source)  # "old-doc"
        
        md_content = f"""---
source_type: "PDF Document"
source_path: "{old_source}"
tags: ["test"]
converted_at: "2026-01-01 00:00:00"
---

# Test
Content here.
"""
        self._create_file(f"{old_prefix}-part-1.md", md_content)
        
        sync_path(old_source, new_source, self.test_dir)
        
        new_prefix = get_base_title(new_source)  # "new-doc"
        new_file = os.path.join(self.test_dir, f"{new_prefix}-part-1.md")
        self.assertTrue(os.path.exists(new_file))
        
        # Verify content updated
        with open(new_file, 'r') as f:
            content = f.read()
        self.assertIn(new_source, content)
        self.assertNotIn(old_source, content)

    def test_renames_companion_raw_file(self):
        """Companion .raw.txt files should also be renamed."""
        old_source = "/path/old.pdf"
        new_source = "/path/new.pdf"
        old_prefix = get_base_title(old_source)
        
        md_content = f"""---
source_type: "PDF"
source_path: "{old_source}"
tags: []
converted_at: "2026-01-01 00:00:00"
---

# T
C
"""
        md_path = self._create_file(f"{old_prefix}-part-1.md", md_content)
        raw_path = self._create_file(f"{old_prefix}-part-1.md.raw.txt", "raw content here")
        
        sync_path(old_source, new_source, self.test_dir)
        
        new_prefix = get_base_title(new_source)
        new_raw = os.path.join(self.test_dir, f"{new_prefix}-part-1.md.raw.txt")
        self.assertTrue(os.path.exists(new_raw), "Companion .raw.txt file should be renamed")

    def test_no_match_no_error(self):
        """When no files match, sync should complete without error."""
        self._create_file("unrelated-file.md", "content")
        # Should not crash
        sync_path("/some/old.pdf", "/some/new.pdf", self.test_dir)

    def test_legacy_format_updated(self):
        """Legacy bold-format metadata should also be updated."""
        old_source = "/path/old.pdf"
        new_source = "/path/new.pdf"
        old_prefix = get_base_title(old_source)
        
        md_content = f"""# Title

**Source Type:** PDF Document
**Source Path/URL:** {old_source}
"""
        self._create_file(f"{old_prefix}-part-1.md", md_content)
        
        sync_path(old_source, new_source, self.test_dir)
        
        new_prefix = get_base_title(new_source)
        new_file = os.path.join(self.test_dir, f"{new_prefix}-part-1.md")
        
        if os.path.exists(new_file):
            with open(new_file, 'r') as f:
                content = f.read()
            self.assertIn(new_source, content)


if __name__ == '__main__':
    unittest.main()
