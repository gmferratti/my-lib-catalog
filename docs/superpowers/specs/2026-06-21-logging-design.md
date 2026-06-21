# Design: Logging estruturado — my-lib-catalog

**Data:** 2026-06-21  
**Status:** Aprovado

---

## Objetivo

Melhorar a observabilidade do projeto em dois eixos:

1. **Resumo de scanning no terminal** — após cada ISBN processado pelo worker, exibir de forma compacta a fonte dos metadados, a fonte da capa e os campos recuperados.
2. **Logging estruturado nos módulos** — substituir o silêncio atual dos módulos `catalog.*` por entradas de log com níveis semânticos, gravadas em arquivo de diagnóstico diário.

---

## Abordagem escolhida

**Python `logging` module + `on_result` enriquecido.**

- Módulos `catalog.*` usam `logging.getLogger(__name__)` — sem `print()`.
- `scripts/main.py` configura dois handlers na inicialização: StreamHandler(WARNING→terminal) e FileHandler(DEBUG→arquivo).
- O resumo compacto no terminal continua sendo exibido via `on_result` (callback do worker), calculado a partir dos campos já presentes no `registro`.
- Nenhuma alteração no schema de dados (`_diag` descartado — informação de diagnóstico vai só para o arquivo de log).

---

## Configuração central (scripts/main.py)

Função `_configurar_logging()` chamada uma vez no início de `main()`:

```python
import logging
from datetime import date
from pathlib import Path

LOG_DIR = Path("data/logs")

def _configurar_logging() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    raiz = logging.getLogger("catalog")
    raiz.setLevel(logging.DEBUG)

    sh = logging.StreamHandler()
    sh.setLevel(logging.WARNING)
    sh.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    fh = logging.FileHandler(LOG_DIR / f"{date.today()}.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "[%(asctime)s] [%(levelname)-7s] %(name)s — %(message)s",
        datefmt="%H:%M:%S"
    ))

    raiz.addHandler(sh)
    raiz.addHandler(fh)
```

Cada módulo declara `logger = logging.getLogger(__name__)` no topo. Como `__name__` começa com `catalog.`, todos herdam automaticamente os handlers de `catalog` via a hierarquia de loggers do Python.

---

## Instrumentação por módulo

### `catalog/metadata/api.py`

| Local | Nível | Mensagem |
|---|---|---|
| `_get_json()` — início de cada tentativa | DEBUG | `GET <url> (tentativa N/M)` |
| `_get_json()` — status 429 | WARNING | `Rate limit 429 em <url> — aguardando Xs` |
| `_get_json()` — falha final | ERROR | `Falha após N tentativas: <url>` |
| `buscar_metadados()` — início de cada fonte | DEBUG | `[<isbn>] tentando <fonte>` |
| `buscar_metadados()` — fonte encontrou título | DEBUG | `[<isbn>] <fonte> → encontrado (título: <titulo>)` |
| `buscar_metadados()` — fonte sem resultado | DEBUG | `[<isbn>] <fonte> → não encontrado` |
| `buscar_metadados()` — fonte suplementou ano | DEBUG | `[<isbn>] ano suplementado via <fonte>` |
| `buscar_metadados()` — conclusão | INFO | `[<isbn>] metadados obtidos via <fonte>` |
| `buscar_metadados()` — nao_encontrado | WARNING | `[<isbn>] nenhuma fonte retornou metadados` |

### `catalog/metadata/worker.py`

| Local | Nível | Mensagem |
|---|---|---|
| ISBN recebido da fila | DEBUG | `[<isbn>] recebido da fila` |
| Processamento concluído com título | INFO | `[<isbn>] processado — <titulo>` |
| Processamento concluído sem metadados | INFO | `[<isbn>] processado — sem metadados` |
| Exceção inesperada | ERROR | `[<isbn>] erro inesperado: <exception>` |

### `catalog/storage/persistence.py`

| Local | Nível | Mensagem |
|---|---|---|
| `salvar()` — início | DEBUG | `salvando <isbn> (<titulo>)` |
| `salvar()` — erro de I/O | WARNING | `erro de I/O ao salvar <isbn>: <e>` |
| `reescrever_registros()` — início | DEBUG | `reescrevendo <N> registros` |

### `catalog/storage/git_sync.py` e `github_sync.py`

| Local | Nível | Mensagem |
|---|---|---|
| `garantir_branch_sessao()` — branch criado/reutilizado | INFO | `branch de sessão: <branch>` |
| `commit_se_houver_mudancas()` — commit realizado | INFO | `commit: <mensagem>` |
| `commit_se_houver_mudancas()` — sem mudanças | DEBUG | `nenhuma mudança para commitar` |
| `finalizar_sessao()` — PR aberta | INFO | `PR aberta: <url>` |
| Qualquer falha de sync | ERROR | `falha no sync: <e>` |

---

## Terminal enrichment — on_result (scripts/main.py)

O callback `_on_result` passa a exibir uma segunda linha de diagnóstico calculada a partir do `registro` retornado pelo worker.

**Campos exibidos:**
- `fonte` — API que forneceu os metadados
- `capa_fonte` — serviço que forneceu a capa (ou `"sem capa"`)
- Campos recuperados — lista dos campos não-vazios, excluindo `isbn`, `data_cadastro`, `fonte`, `capa_url`, `capa_fonte`, `estante`, `prateleira`

**Formato por caso:**

```
# Sucesso com metadados
✓ [9788575228104] Python Fluente — Luciano Ramalho
   → fonte: brasilapi | capa: openlibrary_isbn | campos: título, autores, editora, ano, páginas, idioma

# Sem metadados
⚠  [9788000000000] sem metadados — salvo só o ISBN
   → nenhuma fonte retornou dados

# Erro inesperado
✗ [9788583651277] erro inesperado: ConnectionError (fica pendente)
```

A contagem de itens na fila (restante) permanece na linha seguinte, sem alteração.

---

## Arquivo de log

**Caminho:** `data/logs/YYYY-MM-DD.log`  
**Criado:** automaticamente pelo `FileHandler`  
**Rotação:** um arquivo por dia (suficiente para uso pessoal)  
**Gitignore:** `data/logs/` deve ser adicionado ao `.gitignore`

Exemplo de saída:

```
[14:32:01] [DEBUG  ] catalog.metadata.api — [9788575228104] tentando brasilapi
[14:32:01] [DEBUG  ] catalog.metadata.api — [9788575228104] brasilapi → encontrado (título: Python Fluente)
[14:32:01] [INFO   ] catalog.metadata.api — [9788575228104] metadados obtidos via brasilapi
[14:32:02] [DEBUG  ] catalog.metadata.api — [9788575228104] tentando openlibrary_isbn (capa)
[14:32:02] [INFO   ] catalog.metadata.worker — [9788575228104] processado — Python Fluente
[14:32:02] [DEBUG  ] catalog.storage.persistence — salvando 9788575228104 (Python Fluente)
[14:32:02] [INFO   ] catalog.storage.git_sync — commit: adicionar Python Fluente
```

---

## Arquivos afetados

| Arquivo | Mudança |
|---|---|
| `scripts/main.py` | Adicionar `_configurar_logging()`, enriquecer `_on_result` |
| `catalog/metadata/api.py` | Adicionar logger, instrumentar `_get_json()` e `buscar_metadados()` |
| `catalog/metadata/worker.py` | Adicionar logger, instrumentar loop principal |
| `catalog/storage/persistence.py` | Adicionar logger, instrumentar `salvar()` e `reescrever_registros()` |
| `catalog/storage/git_sync.py` | Adicionar logger, instrumentar funções públicas |
| `catalog/storage/github_sync.py` | Adicionar logger, instrumentar funções públicas |
| `.gitignore` | Adicionar `data/logs/` |

---

## O que não muda

- Schema de dados (`data/biblioteca.csv`, `data/biblioteca.jsonl`) — inalterado.
- API pública de todos os módulos — nenhuma assinatura de função muda.
- Comportamento do terminal fora do scanning — apenas `_on_result` é alterado; o restante dos `print()` em `main.py` permanece como está.
- Testes existentes — o `mock_git_sync` em `conftest.py` já mocka o sync; os novos loggers não afetam os testes.
