.PHONY: setup run validate validate-llm reconvert reconvert-llm clean

# Default directory for validation if not specified
DIR ?= output_notes/

setup:
	@echo "=> Membuat virtual environment dan menginstal requirements..."
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt
	@echo "=> Selesai! Anda bisa menjalankan perintah lain sekarang."

run:
	@if [ -z "$(INPUT)" ]; then echo "ERROR: Harap berikan INPUT. Contoh: make run INPUT='https://...' atau make run INPUT='path/to/file'"; exit 1; fi; \
	if echo "$(INPUT)" | grep -q "instagram.com"; then \
		echo "=> Memproses link Instagram..."; \
		./venv/bin/python main.py "$(INPUT)" -o output_notes_ig; \
	elif echo "$(INPUT)" | grep -q "^http"; then \
		echo "=> Memproses link Website..."; \
		./venv/bin/python main.py "$(INPUT)" -o output_notes_web; \
	else \
		echo "=> Memproses file lokal..."; \
		./venv/bin/python main.py "$(INPUT)" -o output_notes; \
	fi

validate:
	@echo "=> Menjalankan validasi Heuristic (Cepat) pada direktori: $(DIR)"
	./venv/bin/python validate_output.py "$(DIR)"

validate-llm:
	@echo "=> Menjalankan validasi LLM (Mendalam) pada direktori: $(DIR)"
	./venv/bin/python validate_output.py "$(DIR)" --llm

reconvert:
	@echo "=> Mencari dan mereconvert file yang gagal (Heuristic) di direktori: $(DIR)"
	./venv/bin/python reconvert.py "$(DIR)"

reconvert-llm:
	@echo "=> Mencari dan mereconvert file yang gagal (LLM) di direktori: $(DIR)"
	./venv/bin/python reconvert.py "$(DIR)" --llm-validate


clean:
	@echo "=> Menghapus seluruh file output..."
	rm -rf output_notes/* output_notes_ig/* output_notes_web/*
