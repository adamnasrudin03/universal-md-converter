import os
import json
import tempfile
import time
from unittest.mock import patch, MagicMock

import pytest

from validate_output import save_validation_report, validate_file

class TestValidationCache:
    
    def test_validate_file_includes_mtime(self):
        with tempfile.NamedTemporaryFile(suffix=".md", mode='w', delete=False) as f:
            f.write("---\ntags: [test]\n---\n## 🧠 Core Summary\n\n" + "word " * 50 + "\n*Converted using Universal MD Converter*")
            test_file = f.name
            
        try:
            res = validate_file(test_file, use_llm=False)
            assert "mtime" in res
            assert res["mtime"] > 0
            
            # File mtime should roughly match the OS reported mtime
            actual_mtime = os.path.getmtime(test_file)
            assert res["mtime"] == actual_mtime
        finally:
            os.unlink(test_file)

    def test_validate_file_missing_file_mtime_is_zero(self):
        res = validate_file("non_existent_file.md", use_llm=False)
        assert res["status"] == "ERROR"
        assert res["mtime"] == 0

    def test_save_validation_report_creates_and_updates_cache(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            file_path = os.path.join(temp_dir, "test1.md")
            report_file = os.path.join(temp_dir, "validation_report.json")
            
            res1 = {
                "file": "test1.md",
                "score": 100,
                "status": "OK",
                "feedback": [],
                "mtime": 1234567890.0
            }
            
            # Test creating a new cache
            save_validation_report(file_path, res1)
            
            assert os.path.exists(report_file)
            with open(report_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            assert "test1.md" in data
            assert data["test1.md"]["mtime"] == 1234567890.0
            
            # Test updating an existing cache with a new file
            file_path2 = os.path.join(temp_dir, "test2.md")
            res2 = {
                "file": "test2.md",
                "score": 50,
                "status": "NEEDS RECONVERT",
                "feedback": ["Missing summary"],
                "mtime": 1234567895.0
            }
            save_validation_report(file_path2, res2)
            
            with open(report_file, 'r', encoding='utf-8') as f:
                data2 = json.load(f)
                
            assert "test1.md" in data2
            assert "test2.md" in data2
            assert data2["test2.md"]["score"] == 50
            
            # Test updating an existing file in the cache
            res1_updated = {
                "file": "test1.md",
                "score": 90,
                "status": "OK",
                "feedback": ["Updated"],
                "mtime": 1234567999.0
            }
            save_validation_report(file_path, res1_updated)
            
            with open(report_file, 'r', encoding='utf-8') as f:
                data3 = json.load(f)
                
            assert data3["test1.md"]["mtime"] == 1234567999.0
            assert data3["test1.md"]["score"] == 90
            # Ensure test2.md is still there
            assert data3["test2.md"]["score"] == 50

    @patch('validate_output.json.dump')
    def test_save_validation_report_exception_handling(self, mock_json_dump):
        # Simulate a permission error or IO error during dump
        mock_json_dump.side_effect = IOError("Mocked IO Error")
        
        # This shouldn't raise an exception because of the try-except block
        # It should just print a warning message (which we ignore in tests or could capture)
        save_validation_report("fake/path/test.md", {"mtime": 1})
        
        # Test passes if no exception is raised
