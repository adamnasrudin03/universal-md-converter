.PHONY: setup run validate validate-llm reconvert reconvert-llm clean sync-path test

# Default directory for validation if not specified
DIR ?= outputs/notes/

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
		./venv/bin/python src/main.py "$(INPUT)" -o outputs/notes_ig $$MODEL_ARG; \
	elif echo "$(INPUT)" | grep -q "^http"; then \
		echo "=> Memproses link Website..."; \
		./venv/bin/python src/main.py "$(INPUT)" -o outputs/notes_web $$MODEL_ARG; \
	else \
		echo "=> Memproses file lokal..."; \
		./venv/bin/python src/main.py "$(INPUT)" -o outputs/notes $$MODEL_ARG; \
	fi

validate:
	@echo "=> Menjalankan validasi Heuristic (Cepat) pada direktori: $(DIR)"
	./venv/bin/python src/validate_output.py "$(DIR)"

validate-llm:
	@echo "=> Menjalankan validasi LLM (Mendalam) pada direktori: $(DIR)"
	@MODEL_ARG=""; \
	if [ -n "$(MODEL)" ]; then MODEL_ARG="--model $(MODEL)"; fi; \
	./venv/bin/python src/validate_output.py "$(DIR)" --llm $$MODEL_ARG

reconvert:
	@echo "=> Mencari dan mereconvert file yang gagal (Heuristic) di direktori: $(DIR)"
	@MODEL_ARG=""; \
	if [ -n "$(MODEL)" ]; then MODEL_ARG="--model $(MODEL)"; fi; \
	./venv/bin/python src/reconvert.py "$(DIR)" $$MODEL_ARG

reconvert-llm:
	@echo "=> Mencari dan mereconvert file yang gagal (LLM) di direktori: $(DIR)"
	@MODEL_ARG=""; \
	if [ -n "$(MODEL)" ]; then MODEL_ARG="--model $(MODEL)"; fi; \
	./venv/bin/python src/reconvert.py "$(DIR)" --llm-validate $$MODEL_ARG


sync-path:
	@if [ -z "$(OLD)" ] || [ -z "$(NEW)" ]; then \
		echo "ERROR: Harap berikan OLD dan NEW. Contoh: make sync-path OLD='lama.pdf' NEW='baru.pdf'"; \
		exit 1; \
	fi
	./venv/bin/python src/sync_path.py --old "$(OLD)" --new "$(NEW)" --dir "$(DIR)"

clean:
	@echo "=> Menghapus seluruh file output..."
	rm -rf outputs/*/*

test:
	@echo "=> Menjalankan seluruh unit test..."
	./venv/bin/python -m pytest tests/ -v

