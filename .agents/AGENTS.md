# Universal Markdown Converter - Agent Guidelines

## Context
This project is an automated file and web-link converter designed to extract text, images (via OCR), and media (via Whisper) and convert them into "Atomic Notes" formatted as Markdown.

## Core Directives
1. **Universal RAG-Ready Output**: The ultimate goal of this project is to feed the generated markdown into a Retrieval-Augmented Generation (RAG) system capable of handling any topic (e.g. trading, coding, cooking, books). Never output monolithic files. Always split content intelligently using `src/utils/chunking.py`.
2. **Local AI Chunking & Metadata**: The project uses a local Ollama LLM (auto-detects `llama3` or `llama3.2`) to format extracted texts into strict RAG structures (`Core Summary`, `Key Concepts & Definitions`, `Important Details / Application`, `Original Context & Quotes` + up to 3 dynamic context-specific headers). The output strictly enforces **YAML Frontmatter** for metadata (`source_type`, `source_path`, `tags`, `converted_at`) and uses a JSON response format containing `filename_slug`, `tags`, and `rag_content`.
3. **Instagram & YouTube Modules**: 
   - `src/converters/ig_converter.py` handles Instagram links by downloading slides using `instaloader`, running OCR on each slide using Tesseract, and combining the text. Always remember to clean up the temporary directory `temp_ig_*` after OCR.
   - `src/converters/youtube_converter.py` extracts transcripts using `youtube-transcript-api` using the `.list().find_transcript().fetch()` API.
4. **Batch Processing**: `src/main.py` supports converting whole directories. When passing a directory, it recursively traverses and converts all supported file types within it.
5. **Dependencies**: Prefer free and open-source libraries (e.g., `whisper` base model, `pytesseract`, `pdfplumber`, `youtube-transcript-api`).
6. **No Cat Command**: Agents editing this project must use native file writing tools, never `cat` via `run_command` to write files.
7. **AI Vibe Coding**: Always maintain a faithful AI coding vibe.
8. **Testing Requirement**: You must run `make test` to verify changes. Every new feature or enhancement MUST be accompanied by corresponding unit tests.
9. **Function Splitting**: If a function becomes too long, refactor and split it into separate files based on context.

## Python Environment
When testing or running the script, ensure you activate the virtual environment `source venv/bin/activate` before executing `python src/main.py`.

## Adding New Converters
If you add a new format converter:
1. Create `src/converters/your_new_converter.py`.
2. Export it in `src/converters/__init__.py`.
3. Call it in `src/main.py` routing logic.
4. Pass the extracted raw text to `chunk_text_intelligently()`.
