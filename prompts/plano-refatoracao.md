# Plano: Refatoração e Evolução do my-lib-catalog

## Context

O projeto é um catalogador pessoal de biblioteca: o usuário escaneia ISBNs com um leitor de código de barras, o sistema busca metadados em 4 APIs em cascata e persiste em CSV + JSONL. A arquitetura de fila produtor-consumidor já funciona e deve ser preservada integralmente. O objetivo é: (1) separar formalmente os módulos de scanning e metadados, (2) garantir cobertura de testes, (3) criar UI Streamlit para consulta, e (4) produzir CLAUDE.md completo para que agentes futuros possam trabalhar de forma autônoma e segura.

---

## Decisões arquiteturais a preservar

- Fila `queue.Queue` desacoplando scanning do processamento de metadados
- Persistência dual: `data/biblioteca.csv` + `data/biblioteca.jsonl` (não mudar schema)
- Cascata de APIs: Open Library → Google Books → Mercado Livre → ISBNdb (nessa ordem)
- Thread-safety via `_io_lock` em `persistence.py`
- `tmp/pendentes.txt` como fila durável entre sessões

**Schema de dados (11 campos — imutável, há dados reais gravados):**
```
isbn, titulo, autores, editora, ano, paginas, idioma, assuntos, capa_url, fonte, data_cadastro
```
Valores válidos de `fonte`: `openlibrary`, `googlebooks`, `mercadolivre`, `isbndb`, `nao_encontrado`

---

## Fase 1 — Documentação (CLAUDE.md + pyproject.toml)

**Fazer primeiro** — serve de contrato para todas as fases seguintes.

### 1.1 Criar `CLAUDE.md` na raiz do projeto

Seções obrigatórias:
1. Propósito do projeto (1 parágrafo)
2. Diagrama ASCII da arquitetura: `main.py` → `scanning/` → `queue.Queue` → `metadata/` → `storage/`
3. Schema de dados — tabela com os 11 campos, tipos e notas
4. Arquivos de dados — o que são, que o schema não pode mudar
5. Modelo de threads — quem escreve, quem lê, onde está o lock
6. Cascata de APIs — ordem fixa, como adicionar nova fonte (sempre após ISBNdb)
7. Limites conhecidos — ISBNdb requer chave (500 req/mês grátis); Mercado Livre é marketplace, qualidade de dados inferior
8. Fronteiras de módulo — o que cada sub-pacote pode importar de outro
9. Como executar — CLI (`python main.py`), UI (`streamlit run ui/app.py`), testes (`pytest`)
10. Como estender — nova fonte de API, novo filtro na UI, novo formato de saída

### 1.2 Criar `pyproject.toml`

```toml
[project]
name = "my-lib-catalog"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["requests>=2.31.0"]

[project.optional-dependencies]
ui = ["streamlit>=1.35.0"]
dev = ["pytest>=8.0", "pytest-mock>=3.14"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-v"
```

---

## Fase 2 — Reestruturação de módulos (sem mudança de lógica)

### Nova estrutura de diretórios

```
catalog/
├── __init__.py
├── config.py              # mantido; adicionar os.environ.get("ISBNDB_API_KEY", "")
├── scanning/
│   ├── __init__.py        # exporta: normalizar_isbn
│   └── isbn.py            # conteúdo de catalog/isbn.py (inalterado)
├── metadata/
│   ├── __init__.py        # exporta: buscar_metadados, worker
│   ├── api.py             # conteúdo de catalog/api.py (inalterado)
│   └── worker.py          # conteúdo de catalog/worker.py + callback on_result
└── storage/
    ├── __init__.py        # exporta todas as funções de persistence.py
    └── persistence.py     # conteúdo de catalog/persistence.py (inalterado)
ui/
├── __init__.py
└── app.py                 # Streamlit (novo)
```

### Mudança chave em `catalog/metadata/worker.py`

Adicionar parâmetro `on_result` para desacoplar o print do terminal da lógica do worker:

```python
def worker(
    fila: queue.Queue,
    parar_evento: threading.Event,
    on_result: Callable[[dict], None] | None = None,
) -> None:
```

Em `main.py`, passar lambda que faz o `print()`. O worker deixa de ter efeito colateral de I/O.

### Imports em `main.py` atualizados para:

```python
from catalog.scanning import normalizar_isbn
from catalog.metadata import buscar_metadados, worker
from catalog.storage import adicionar_pendente, carregar_isbns_cadastrados, ...
```

### Arquivos antigos

Remover `catalog/isbn.py`, `catalog/api.py`, `catalog/persistence.py`, `catalog/worker.py` após mover conteúdo. Projeto pessoal sem dependentes externos — não criar shims.

### `catalog/config.py` — única mudança de lógica

```python
import os
ISBNDB_API_KEY = os.environ.get("ISBNDB_API_KEY", "")
```

---

## Fase 3 — Testes

Instalar: `pip install pytest pytest-mock`

### Arquivos a criar

**`tests/conftest.py`**
- Fixture `sample_isbn` → `"9781098115784"`
- Fixture `sample_record` → dict completo com os 11 campos
- Fixture `tmp_data_dir(tmp_path, monkeypatch)` → redireciona `CSV_FILE`, `JSON_FILE`, `PENDING_FILE` para diretório temporário

**`tests/test_isbn.py`** — puro, sem mock
- ISBN-13 válido, ISBN-10 válido, com hífens, ISBN-10 com X, curto demais, longo demais, string vazia

**`tests/test_api.py`** — mockar `requests.get` com `pytest-mock`

Por fonte:
- Happy path: retorna dict com campos corretos e `fonte` correto
- Resultado vazio: retorna `None`
- `ConnectionError`: retorna `None` (não lança)

Para `buscar_metadados`:
- Cascata para no primeiro sucesso (Open Library retorna dado → Google Books não é chamado)
- Cascata exaurida → `fonte == "nao_encontrado"`, demais campos vazios
- Resultado sempre tem `isbn` e `data_cadastro`
- `buscar_isbndb` ignorada quando `ISBNDB_API_KEY` vazio

**`tests/test_persistence.py`** — usa `tmp_data_dir`
- `salvar` cria CSV e JSONL; append na segunda chamada; header escrito uma só vez
- `carregar_todos_registros`, `adicionar_pendente`, `remover_pendente`, `reescrever_registros`

**`tests/test_worker.py`** — mockar `buscar_metadados` e `salvar`
- Worker chama as funções certas, para no sentinel `None`
- Callback `on_result` é chamado com o registro
- Exceção não derruba o worker

---

## Fase 4 — UI Streamlit

**`ui/app.py`** — lê exclusivamente de `catalog.storage.carregar_todos_registros()`, nunca escreve.

### Funcionalidades
- **Sidebar com filtros**: busca por título/autor (text_input), idioma (selectbox), fonte (selectbox), checkbox "Ocultar sem metadados"
- **Métricas no topo**: total de livros, livros com capa, livros sem metadados
- **Grid de cards** (4 colunas): capa (ou placeholder 📖), título, autores, ano, badge de fonte
- **Tabela completa** (expander): `st.dataframe` com todos os 11 campos
- **Botão "Recarregar dados"**: chama `st.cache_data.clear()`

### Notas de implementação
- `@st.cache_data(ttl=60)` na função de carga
- Filtros operam em memória sobre a lista carregada
- A UI é processo separado do `main.py` — não há estado compartilhado

---

## Sequência de execução recomendada para o agente

1. Criar `CLAUDE.md`
2. Criar `pyproject.toml`
3. Criar sub-pacotes (`catalog/scanning/`, `catalog/metadata/`, `catalog/storage/`)
4. Mover arquivos com ajuste de imports relativos
5. Atualizar `catalog/config.py` (os.environ)
6. Atualizar `main.py` — novos imports + `on_result` lambda
7. Remover arquivos antigos
8. Criar suite de testes (`tests/conftest.py` + 4 arquivos)
9. Rodar `pytest` — todos devem passar antes de continuar
10. Criar `ui/__init__.py` e `ui/app.py`
11. Smoke test: `streamlit run ui/app.py`

---

## Verificação final

- `python main.py` funciona igual ao atual
- `pytest` passa sem warnings
- `streamlit run ui/app.py` mostra os livros já cadastrados com filtros funcionando
- `data/biblioteca.csv` e `data/biblioteca.jsonl` não são modificados pela refatoração
