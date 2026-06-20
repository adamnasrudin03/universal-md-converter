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
	MODEL_ARG=""; \
	if [ -n "$(MODEL)" ]; then MODEL_ARG="-m $(MODEL)"; fi; \
	if echo "$(INPUT)" | grep -q "instagram.com"; then \
		echo "=> Memproses link Instagram..."; \
		./venv/bin/python main.py "$(INPUT)" -o output_notes_ig $$MODEL_ARG; \
	elif echo "$(INPUT)" | grep -q "^http"; then \
		echo "=> Memproses link Website..."; \
		./venv/bin/python main.py "$(INPUT)" -o output_notes_web $$MODEL_ARG; \
	else \
		echo "=> Memproses file lokal..."; \
		./venv/bin/python main.py "$(INPUT)" -o output_notes $$MODEL_ARG; \
	fi

validate:
	@echo "=> Menjalankan validasi Heuristic (Cepat) pada direktori: $(DIR)"
	./venv/bin/python validate_output.py "$(DIR)"

validate-llm:
	@echo "=> Menjalankan validasi LLM (Mendalam) pada direktori: $(DIR)"
	@MODEL_ARG=""; \
	if [ -n "$(MODEL)" ]; then MODEL_ARG="--model $(MODEL)"; fi; \
	./venv/bin/python validate_output.py "$(DIR)" --llm $$MODEL_ARG

reconvert:
	@echo "=> Mencari dan mereconvert file yang gagal (Heuristic) di direktori: $(DIR)"
	@MODEL_ARG=""; \
	if [ -n "$(MODEL)" ]; then MODEL_ARG="--model $(MODEL)"; fi; \
	./venv/bin/python reconvert.py "$(DIR)" $$MODEL_ARG

reconvert-llm:
	@echo "=> Mencari dan mereconvert file yang gagal (LLM) di direktori: $(DIR)"
	@MODEL_ARG=""; \
	if [ -n "$(MODEL)" ]; then MODEL_ARG="--model $(MODEL)"; fi; \
	./venv/bin/python reconvert.py "$(DIR)" --llm-validate $$MODEL_ARG


sync-path:
	@if [ -z "$(OLD)" ] || [ -z "$(NEW)" ]; then \
		echo "ERROR: Harap berikan OLD dan NEW. Contoh: make sync-path OLD='lama.pdf' NEW='baru.pdf'"; \
		exit 1; \
	fi
	./venv/bin/python sync_path.py --old "$(OLD)" --new "$(NEW)" --dir "$(DIR)"

clean:
	@echo "=> Menghapus seluruh file output..."
	rm -rf output_notes/* output_notes_ig/* output_notes_web/*
