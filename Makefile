-include .env
export

.PHONY: install run ui reprocessar capas capas-fix sync test test-v clean help

UV := uv

help:           ## Mostra esta ajuda
	@grep -E '^[a-zA-Z_-]+:.*##' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*##"}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install:        ## Cria .venv e instala todas as dependências (incluindo dev)
	$(UV) sync --group dev

run:            ## Inicia o scanner interativo (CLI)
	PYTHONPATH=. $(UV) run python scripts/main.py

ui:             ## Abre a interface de consulta no navegador
	$(UV) run streamlit run ui/app.py

batch:          ## Processa ISBNs passados em ISBNS="isbn1 isbn2 ..." sem abrir o scanner
	PYTHONPATH=. $(UV) run python scripts/main.py --isbns $(ISBNS)

reprocessar:    ## Rebusca metadados para livros cadastrados com fonte=nao_encontrado
	PYTHONPATH=. $(UV) run python scripts/main.py --reprocessar

capas:          ## Busca capas de alta qualidade para todos os livros do acervo
	PYTHONPATH=. $(UV) run python scripts/main.py --capas

capas-fix:      ## Verifica URLs quebradas e rebusca capas ausentes
	PYTHONPATH=. $(UV) run python scripts/main.py --capas --fix

sync:           ## Sincroniza o acervo com o GitHub (commit + push dos dados)
	git add data/
	git diff --cached --quiet || git commit -m "chore(data): sincronizar acervo"
	git push

test:           ## Roda a suite de testes
	$(UV) run pytest

test-v:         ## Roda os testes em modo verbose
	$(UV) run pytest -v

clean:          ## Remove caches Python e artefatos de build
	find . -type d -name __pycache__ -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -not -path './.venv/*' -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name '*.egg-info' -exec rm -rf {} + 2>/dev/null || true
