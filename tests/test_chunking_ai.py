import json
from unittest.mock import patch, MagicMock
from src.utils.chunking import extract_global_context, recursive_markdown_split, chunk_text_intelligently

class TestChunkingAI:

    @patch('src.utils.chunking.ollama.chat')
    def test_extract_global_context_success_dict(self, mock_chat):
        mock_chat.return_value = {"message": {"content": "This is a summary."}}
        res = extract_global_context("Some long text")
        assert res == "This is a summary."

    @patch('src.utils.chunking.ollama.chat')
    def test_extract_global_context_success_obj(self, mock_chat):
        class MockMsg:
            content = "This is an object summary."
        class MockResponse:
            message = MockMsg()
        mock_chat.return_value = MockResponse()
        res = extract_global_context("Some text")
        assert res == "This is an object summary."

    @patch('src.utils.chunking.ollama.chat')
    def test_extract_global_context_exception(self, mock_chat):
        mock_chat.side_effect = Exception("Ollama offline")
        res = extract_global_context("Some text")
        assert res == ""

    def test_recursive_markdown_split_short(self):
        text = "Just a short text."
        chunks = recursive_markdown_split(text, max_words=10)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_recursive_markdown_split_long_no_headers(self):
        text = " ".join(["word"] * 15)
        chunks = recursive_markdown_split(text, max_words=10)
        assert len(chunks) == 2
        assert len(chunks[0].split()) == 10
        assert len(chunks[1].split()) == 5

    def test_recursive_markdown_split_with_headers(self):
        text = "Some text\n# Header 1\nMore text here.\n## Subheader\nFinal part."
        # Should split by headers
        chunks = recursive_markdown_split(text, max_words=5)
        # Because we split by max_words=5, it might split the parts further, but we at least want to ensure it works
        assert len(chunks) >= 2
        assert any("Header 1" in c for c in chunks)

    @patch('src.utils.chunking.extract_global_context')
    @patch('src.utils.chunking.ollama.chat')
    def test_chunk_text_intelligently_empty(self, mock_chat, mock_global):
        res = chunk_text_intelligently("   ", "test_base")
        assert res == []
        mock_chat.assert_not_called()

    @patch('src.utils.chunking.extract_global_context')
    @patch('src.utils.chunking.ollama.chat')
    def test_chunk_text_intelligently_success(self, mock_chat, mock_global):
        mock_global.return_value = "Global ctx"
        
        # Simulate ollama stream response
        mock_resp = [{"message": {"content": json.dumps({
            "filename_slug": "test-slug",
            "rag_content": "Extracted RAG content",
            "tags": ["tag1", "Tag 2", None, "t a g"]
        })}}]
        mock_chat.return_value = mock_resp

        res = chunk_text_intelligently("This is the raw text to be chunked.", "base", max_words=10)
        
        assert len(res) == 1
        assert res[0]["filename"] == "base-test-slug.md"
        assert res[0]["content"] == "Extracted RAG content"
        assert res[0]["raw_chunk"] == "This is the raw text to be chunked."
        assert "tag1" in res[0]["tags"]
        assert "tag-2" in res[0]["tags"]
        assert "t-a-g" in res[0]["tags"]

    @patch('src.utils.chunking.extract_global_context')
    @patch('src.utils.chunking.ollama.chat')
    def test_chunk_text_intelligently_fallback_regex(self, mock_chat, mock_global):
        mock_global.return_value = ""
        # Simulate wrapped JSON
        invalid_json_str = "```json\n" + json.dumps({
            "filename_slug": "slug-only",
            "rag_content": {"Core": "nested value"}
        }) + "\n```"
        
        class MockMsg:
            content = invalid_json_str
        class MockObj:
            message = MockMsg()
            
        mock_chat.return_value = [MockObj()]

        res = chunk_text_intelligently("Some text", "base")
        
        assert len(res) == 1
        assert res[0]["filename"] == "base-slug-only.md"
        assert "Core\nnested value" in res[0]["content"]

    @patch('src.utils.chunking.extract_global_context')
    @patch('src.utils.chunking.ollama.chat')
    def test_chunk_text_intelligently_exception_fallback(self, mock_chat, mock_global):
        mock_global.return_value = ""
        mock_chat.side_effect = Exception("AI Error")

        res = chunk_text_intelligently("Raw text here.", "base")
        
        assert len(res) == 1
        assert res[0]["filename"] == "base-part-1.md"
        assert res[0]["content"] == "Raw text here."
        assert res[0]["tags"] == []

    @patch('src.utils.chunking.extract_global_context')
    @patch('src.utils.chunking.ollama.chat')
    def test_chunk_text_intelligently_collision(self, mock_chat, mock_global):
        mock_global.return_value = ""
        
        # 3 chunks, all return the same slug
        mock_resp = [{"message": {"content": json.dumps({"filename_slug": "same-slug", "rag_content": "C"})}}]
        mock_chat.return_value = mock_resp
        
        # Make it split into 3 chunks
        res = chunk_text_intelligently("A B C D E F G H I J K L M", "base", max_words=4)
        
        assert len(res) == 4
        assert res[0]["filename"] == "base-same-slug.md"
        assert res[1]["filename"] == "base-same-slug-1.md"
        assert res[2]["filename"] == "base-same-slug-2.md"
        assert res[3]["filename"] == "base-same-slug-3.md"
