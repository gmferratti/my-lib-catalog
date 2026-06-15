.PHONY: install run ui test lint clean help

PYTHON  := .venv/bin/python
PIP     := .venv/bin/pip
PYTEST  := .venv/bin/pytest
STREAMLIT := .venv/bin/streamlit

help:           ## Mostra esta ajuda
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:        ## Cria .venv e instala todas as dependências
	python -m venv .venv
	$(PIP) install -e ".[ui,dev]" -q

run:            ## Inicia o scanner interativo (CLI)
	$(PYTHON) scripts/main.py

ui:             ## Abre a interface de consulta no navegador
	$(STREAMLIT) run ui/app.py

test:           ## Roda a suite de testes
	$(PYTEST)

test-v:         ## Roda os testes em modo verbose
	$(PYTEST) -v

clean:          ## Remove caches Python e artefatos de build
	find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
