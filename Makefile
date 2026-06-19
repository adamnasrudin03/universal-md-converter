.PHONY: setup run-ig run-web run-file validate validate-llm clean

# Default directory for validation if not specified
DIR ?= output_notes/

setup:
	@echo "=> Membuat virtual environment dan menginstal requirements..."
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt
	@echo "=> Selesai! Anda bisa menjalankan perintah lain sekarang."

run-ig:
	@if [ -z "$(URL)" ]; then echo "ERROR: Harap berikan URL. Contoh: make run-ig URL='https://www.instagram.com/p/...'"; exit 1; fi
	@echo "=> Memproses link Instagram..."
	./venv/bin/python main.py "$(URL)" -o output_notes_ig

run-web:
	@if [ -z "$(URL)" ]; then echo "ERROR: Harap berikan URL. Contoh: make run-web URL='https://www.cnbc.com/...'"; exit 1; fi
	@echo "=> Memproses link Website..."
	./venv/bin/python main.py "$(URL)" -o output_notes_web

run-file:
	@if [ -z "$(FILE)" ]; then echo "ERROR: Harap berikan path file. Contoh: make run-file FILE='/path/ke/file.pdf'"; exit 1; fi
	@echo "=> Memproses file lokal..."
	./venv/bin/python main.py "$(FILE)" -o output_notes

validate:
	@echo "=> Menjalankan validasi Heuristic (Cepat) pada direktori: $(DIR)"
	./venv/bin/python validate_output.py "$(DIR)"

validate-llm:
	@echo "=> Menjalankan validasi LLM (Mendalam) pada direktori: $(DIR)"
	./venv/bin/python validate_output.py "$(DIR)" --llm

clean:
	@echo "=> Menghapus seluruh file output..."
	rm -rf output_notes/* output_notes_ig/* output_notes_web/*
