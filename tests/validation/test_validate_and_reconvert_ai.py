import os
import json
from unittest.mock import patch, MagicMock
from src.validate_output import llm_validation, validate_file

class TestValidateOutputAI:

    @patch('src.validate_output.OLLAMA_AVAILABLE', False)
    def test_llm_validation_no_ollama(self):
        score, status, feedback = llm_validation("Some content")
        assert score == 0
        assert status == "ERROR"
        assert "Ollama package is not installed." in feedback[0]

    @patch('src.validate_output.OLLAMA_AVAILABLE', True)
    @patch('src.validate_output.ollama.chat')
    def test_llm_validation_success_dict(self, mock_chat):
        mock_resp = {
            "message": {
                "content": json.dumps({
                    "score": 90,
                    "status": "OK",
                    "feedback": ["Good"]
                })
            }
        }
        mock_chat.return_value = mock_resp
        
        score, status, feedback = llm_validation("Content")
        assert score == 90
        assert status == "OK"
        assert feedback == ["Good"]

    @patch('src.validate_output.OLLAMA_AVAILABLE', True)
    @patch('src.validate_output.ollama.chat')
    def test_llm_validation_success_obj(self, mock_chat):
        class MockMsg:
            content = json.dumps({
                "score": 60,
                "status": "NEEDS RECONVERT",
                "feedback": "Needs more detail"
            })
        class MockObj:
            message = MockMsg()
        mock_chat.return_value = MockObj()
        
        score, status, feedback = llm_validation("Content")
        assert score == 60
        assert status == "NEEDS RECONVERT"
        assert feedback == ["Needs more detail"]

    @patch('src.validate_output.OLLAMA_AVAILABLE', True)
    @patch('src.validate_output.ollama.chat')
    @patch('src.validate_output.os.path.exists')
    @patch('builtins.open', new_callable=MagicMock)
    def test_llm_validation_with_raw_file(self, mock_open_file, mock_exists, mock_chat):
        mock_exists.return_value = True
        mock_open_file.return_value.__enter__.return_value.read.return_value = "Raw Content"
        
        mock_resp = {
            "message": {
                "content": json.dumps({
                    "score": 95,
                    "status": "OK",
                    "feedback": ["Excellent"]
                })
            }
        }
        mock_chat.return_value = mock_resp
        
        score, status, feedback = llm_validation("Content", file_path="dummy.md")
        assert score == 95
        assert status == "OK"

    @patch('src.validate_output.OLLAMA_AVAILABLE', True)
    @patch('src.validate_output.ollama.chat')
    def test_llm_validation_fallback_regex(self, mock_chat):
        mock_resp = {
            "message": {
                "content": "```json\n" + json.dumps({
                    "score": 88,
                    "status": "OK",
                    "feedback": []
                }) + "\n```"
            }
        }
        mock_chat.return_value = mock_resp
        
        score, status, feedback = llm_validation("Content")
        assert score == 88
        assert status == "OK"

    @patch('src.validate_output.OLLAMA_AVAILABLE', True)
    @patch('src.validate_output.ollama.chat')
    def test_llm_validation_invalid_json(self, mock_chat):
        mock_resp = {"message": {"content": "This is not JSON"}}
        mock_chat.return_value = mock_resp
        
        score, status, feedback = llm_validation("Content")
        assert score == 0
        assert status == "ERROR"
        assert "Valid JSON not found in LLM response" in feedback[0]

    @patch('src.validate_output.OLLAMA_AVAILABLE', True)
    @patch('src.validate_output.ollama.chat')
    def test_llm_validation_exception(self, mock_chat):
        mock_chat.side_effect = Exception("Ollama offline")
        
        score, status, feedback = llm_validation("Content")
        assert score == 0
        assert status == "ERROR"
        assert "Ollama offline" in feedback[0]

    @patch('src.validate_output.heuristic_validation')
    @patch('builtins.open', new_callable=MagicMock)
    def test_validate_file_heuristic(self, mock_open_file, mock_heuristic):
        mock_open_file.return_value.__enter__.return_value.read.return_value = "File content"
        mock_heuristic.return_value = (80, "NEEDS RECONVERT", ["Needs work"])
        
        res = validate_file("dummy.md", use_llm=False)
        assert res["file"] == "dummy.md"
        assert res["score"] == 80
        assert res["status"] == "NEEDS RECONVERT"

    @patch('src.validate_output.OLLAMA_AVAILABLE', True)
    @patch('src.validate_output.llm_validation')
    @patch('builtins.open', new_callable=MagicMock)
    def test_validate_file_llm(self, mock_open_file, mock_llm_val):
        mock_open_file.return_value.__enter__.return_value.read.return_value = "File content"
        mock_llm_val.return_value = (95, "OK", [])
        
        res = validate_file("dummy.md", use_llm=True)
        assert res["score"] == 95
        assert res["status"] == "OK"

    @patch('builtins.open', new_callable=MagicMock)
    def test_validate_file_exception(self, mock_open_file):
        mock_open_file.side_effect = Exception("File not found")
        
        res = validate_file("dummy.md")
        assert res["score"] == 0
        assert res["status"] == "ERROR"
        assert "File not found" in res["feedback"][0]
