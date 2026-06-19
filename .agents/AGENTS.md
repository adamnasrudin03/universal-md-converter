# Universal Markdown Converter - Agent Guidelines

## Context
This project is an automated file and web-link converter designed to extract text, images (via OCR), and media (via Whisper) and convert them into "Atomic Notes" formatted as Markdown.

## Core Directives
1. **Universal RAG-Ready Output**: The ultimate goal of this project is to feed the generated markdown into a Retrieval-Augmented Generation (RAG) system capable of handling any topic (e.g. trading, coding, cooking, books). Never output monolithic files. Always split content intelligently using `utils/chunking.py`.
2. **Local AI Chunking**: The project uses a local Ollama LLM (`llama3`) to format extracted texts into specific RAG structures (`Core Summary`, `Key Concepts`, `Important Details`, `Original Context` + dynamic context-specific headers). If you modify the chunking logic, ensure the prompt strictly demands a JSON output containing `filename_slug`, `tags`, and `rag_content`.
3. **Instagram Module**: `ig_converter.py` handles Instagram links by downloading slides using `instaloader`, running OCR on each slide using Tesseract, and combining the text. Always remember to clean up the temporary directory `temp_ig_*` after OCR.
4. **Dependencies**: Prefer free and open-source libraries (e.g., `whisper` base model, `pytesseract`, `pdfplumber`).
5. **No Cat Command**: Agents editing this project must use native file writing tools, never `cat` via `run_command` to write files.

## Python Environment
When testing or running the script, ensure you activate the virtual environment `source venv/bin/activate` before executing `python main.py`.

## Adding New Converters
If you add a new format converter:
1. Create `converters/your_new_converter.py`.
2. Export it in `converters/__init__.py`.
3. Call it in `main.py` routing logic.
4. Pass the extracted raw text to `chunk_text_intelligently()`.
