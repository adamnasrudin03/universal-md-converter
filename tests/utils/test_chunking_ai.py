import json
from unittest.mock import patch, MagicMock
from src.utils.chunking import extract_global_context, recursive_markdown_split, chunk_text_intelligently, process_chunk_with_ai

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
        chunks = recursive_markdown_split(text, max_words=10, overlap_words=2)
        # 15 words, split into 10-word chunks with 2 word overlap
        assert len(chunks) == 2
        assert len(chunks[0].split()) == 10
        # Wait, the second chunk will have 7 words (15 - 8)
        assert len(chunks[1].split()) == 7

    def test_recursive_markdown_split_with_headers(self):
        text = "Some text\n# Header 1\nMore text here.\n## Subheader\nFinal part."
        chunks = recursive_markdown_split(text, max_words=5)
        assert len(chunks) >= 2
        assert any("Header 1" in c for c in chunks)

    def test_chunk_text_intelligently_empty(self):
        res = chunk_text_intelligently("   ")
        assert res == []

    @patch('src.utils.chunking.ollama.chat')
    def test_process_chunk_with_ai_success(self, mock_chat):
        mock_chat.return_value = {"message": {"content": json.dumps({
            "filename_slug": "test-slug",
            "source_context": "Page 1",
            "rag_content": "Extracted RAG content",
            "tags": ["tag1", "Tag 2", None, "t a g"]
        })}}

        res = process_chunk_with_ai("Raw text", 0, 1, "ctx", "base", "llama3")
        
        assert res["filename"] == "base-test-slug.md"
        assert res["content"] == "Extracted RAG content"
        assert res["raw_chunk"] == "Raw text"
        assert res["source_context"] == "Bagian 1 dari 1 | Page 1"
        assert "tag1" in res["tags"]
        assert "tag-2" in res["tags"]
        assert "t-a-g" in res["tags"]

    @patch('src.utils.chunking.ollama.chat')
    def test_process_chunk_with_ai_exception_fallback(self, mock_chat):
        mock_chat.side_effect = Exception("AI Error")

        res = process_chunk_with_ai("Raw text", 0, 1, "ctx", "base", "llama3")
        
        assert res["filename"] == "base-part-1.md"
        assert res["content"] == "Raw text"
        assert res["tags"] == []
        assert res["source_context"] == ""
