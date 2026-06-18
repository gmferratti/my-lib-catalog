# my-lib-catalog — Guia para Agentes

Catalogador pessoal de biblioteca via leitor de código de barras. O usuário escaneia ISBNs pela CLI; um worker em background busca metadados em 4 APIs e persiste em CSV + JSONL. A UI Streamlit serve para consulta/edição do acervo e organização física das estantes.

---

## Arquitetura

```
main.py  (CLI + orquestração)
    │
    ├─→ catalog.scanning.normalizar_isbn()
    │         (valida e normaliza o ISBN)
    │
    ├─→ queue.Queue  (fila thread-safe)
    │         │
    │         └─→ catalog.metadata.worker()  [thread background]
    │                   │
    │                   ├─→ catalog.metadata.buscar_metadados()
    │                   │         Open Library → Google Books → BrasilAPI → ISBNdb
    │                   │
    │                   └─→ catalog.storage.salvar()
    │
    └─→ catalog.storage.*  (leitura direta para reprocessar e duplicatas)

ui/app.py  (Streamlit — processo separado)
    ├─→ catalog.storage.carregar_todos_registros()   [tab Acervo]
    └─→ catalog.organizer.*                          [tab Estantes]
```

---

## Schema de dados

**Imutável** — há dados reais gravados em `data/`. Qualquer alteração quebra registros existentes.

| Campo | Tipo | Exemplo | Notas |
|---|---|---|---|
| `isbn` | str | `"9781098115784"` | 10 ou 13 dígitos |
| `titulo` | str | `"Machine Learning Design Patterns"` | vazio se não encontrado |
| `autores` | str | `"Sara Robinson, Valliappa Lakshmanan"` | separados por vírgula |
| `editora` | str | `"O'Reilly Media"` | |
| `ano` | str | `"2020"` | 4 dígitos |
| `paginas` | int ou str | `400` | int no JSONL, str no CSV |
| `idioma` | str | `"en"`, `"pt"` | código ISO 639-1 ou vazio |
| `assuntos` | str | `"Science, Mathematics"` | máx. 5, separados por vírgula |
| `capa_url` | str | `"https://..."` | URL ou vazio |
| `fonte` | str | ver abaixo | qual API encontrou o livro |
| `data_cadastro` | str | `"2026-05-25T14:44:06"` | ISO 8601, segundos |

**Valores válidos de `fonte`:** `openlibrary`, `googlebooks`, `brasilapi`, `isbndb`, `nao_encontrado`, `manual`

---

## Arquivos de dados

| Arquivo | Propósito |
|---|---|
| `data/biblioteca.csv` | Planilha; abre direto no Excel/LibreOffice |
| `data/biblioteca.jsonl` | JSON Lines; fonte de verdade para a UI e para `reprocessar` |
| `data/estantes.json` | Configuração persistida das estantes (num estantes, prateleiras, largura_cm, espessura_media_cm) |
| `tmp/pendentes.txt` | Fila durável; ISBNs enfileirados mas não processados; recarregado na próxima sessão |

Os diretórios `data/` e `tmp/` são criados automaticamente ao importar `catalog.storage`.

---

## Modelo de threads

- **Thread principal** (`main.py`): lê input do usuário, enfileira ISBNs, lê dados para `reprocessar`.
- **Thread worker** (`catalog.metadata.worker`): única consumidora da fila; única escritora de dados.
- **Lock**: `catalog.storage.persistence._io_lock` protege todas as escritas em arquivo. Nunca chamar `salvar()` ou `remover_pendente()` fora do worker.

---

## Cascata de APIs

**Ordem fixa — não reordenar:**

1. **Open Library** — gratuita, sem auth; usa endpoint `/search.json`
2. **Google Books** — usa `GOOGLE_BOOKS_API_KEY` quando configurada (1000 req/dia); sem chave usa cota anônima compartilhada que esgota facilmente
3. **BrasilAPI** — agrega CBL e outras fontes brasileiras; gratuita, sem auth; retorna 400 para ISBNs não brasileiros (tratado como None)
4. **ISBNdb** — cobertura ampla incluindo editoras brasileiras; requer chave gratuita (500 req/mês)

**Para adicionar nova fonte:** inserir após ISBNdb na lista em `buscar_metadados()`. Retornar `None` em falha, dict com os campos do schema em sucesso. O campo `fonte` deve ser um identificador snake_case sem espaços.

**Retry:** `_get_json()` tenta 3 vezes com backoff exponencial (2s → 4s → 8s → max 30s). Honra `Retry-After` em respostas 429.

---

## Fronteiras de módulo

| Módulo | Pode importar de | Não pode importar de |
|---|---|---|
| `catalog.scanning` | stdlib | `catalog.metadata`, `catalog.storage` |
| `catalog.metadata` | `catalog.config`, `catalog.storage`, stdlib, requests | `catalog.scanning`, `main` |
| `catalog.storage` | `catalog.config`, stdlib | `catalog.scanning`, `catalog.metadata` |
| `catalog.organizer` | `catalog.config`, stdlib | `catalog.metadata`, `catalog.scanning` |
| `catalog.config` | stdlib (os) | qualquer outro módulo do projeto |
| `ui.app` | `catalog.storage`, `catalog.organizer`, streamlit | `catalog.metadata`, `catalog.scanning`, `main` |
| `main` | todos acima | — |

---

## Como executar

```bash
# CLI (escaneamento)
python main.py

# UI de consulta (processo separado)
streamlit run ui/app.py

# Testes
pytest

# Instalar dependências
pip install -e ".[ui,dev]"   # ou: pip install requests streamlit pytest pytest-mock
```

**Variáveis de ambiente:**

| Variável | Padrão | Uso |
|---|---|---|
| `GOOGLE_BOOKS_API_KEY` | `""` | Chave do Google Cloud (Books API). Sem ela usa cota anônima compartilhada, que esgota diariamente. |
| `ISBNDB_API_KEY` | `""` | Chave gratuita do ISBNdb. Sem ela, `buscar_isbndb` é ignorado. |
| `GOOGLE_CUSTOM_SEARCH_KEY` | `""` | Chave do Google Cloud (Custom Search API). Ativa o Stage 7 de busca de capas. 100 queries/dia grátis. |
| `GOOGLE_CUSTOM_SEARCH_CX` | `""` | ID do mecanismo de busca em programmablesearchengine.google.com. Requerido junto com a KEY acima. |

As chaves ficam em `.env` (já no `.gitignore`). O Makefile carrega o arquivo automaticamente via `-include .env`.

---

## Como estender

### Nova fonte de API

1. Adicionar função `buscar_<nome>(isbn: str) -> dict | None` em `catalog/metadata/api.py`
2. Inserir no final da lista em `buscar_metadados()`
3. Adicionar teste em `tests/test_api.py` (happy path + empty + ConnectionError)
4. Documentar aqui em "Cascata de APIs"

### Novo filtro na UI

Adicionar widget na sidebar de `ui/app.py`. Filtrar sobre a lista `registros` já carregada em memória — não ler o arquivo novamente.

### Novo estilo de organização de estantes

1. Adicionar a chave e o rótulo em `ESTILOS` em `ui/app.py`
2. Implementar o case correspondente em `_ordenar()` em `catalog/organizer/algorithm.py`
3. Implementar o label descritivo em `_label()` no mesmo arquivo
4. Adicionar testes em `tests/test_organizer.py`

### Novo campo no schema

**Atenção:** requer migração dos dados existentes em `data/`. Etapas:
1. Adicionar campo em `CSV_HEADERS` em `catalog/config.py`
2. Atualizar todas as funções em `catalog/metadata/api.py` para populá-lo
3. Escrever script de migração que lê o JSONL antigo, adiciona o campo vazio e reescreve
4. Atualizar testes
