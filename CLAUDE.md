# my-lib-catalog — Guia para Agentes

Catalogador pessoal de biblioteca via leitor de código de barras. O usuário escaneia ISBNs pela CLI; um worker em background busca metadados em 4 APIs e persiste em CSV + JSONL. A UI Streamlit serve exclusivamente para consulta e navegação do acervo.

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
    │                   │         Open Library → Google Books → Mercado Livre → ISBNdb
    │                   │
    │                   └─→ catalog.storage.salvar()
    │
    └─→ catalog.storage.*  (leitura direta para reprocessar e duplicatas)

ui/app.py  (Streamlit — processo separado, só lê dados)
    └─→ catalog.storage.carregar_todos_registros()
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

**Valores válidos de `fonte`:** `openlibrary`, `googlebooks`, `mercadolivre`, `isbndb`, `nao_encontrado`

---

## Arquivos de dados

| Arquivo | Propósito |
|---|---|
| `data/biblioteca.csv` | Planilha; abre direto no Excel/LibreOffice |
| `data/biblioteca.jsonl` | JSON Lines; fonte de verdade para a UI e para `reprocessar` |
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

1. **Open Library** — gratuita, sem auth, boa cobertura em inglês
2. **Google Books** — sem chave, melhor cobertura internacional
3. **Mercado Livre** — marketplace brasileiro; fallback para ISBNs nacionais. Qualidade inferior (produto de usuário, não fonte bibliográfica). Existe porque recupera ISBNs brasileiros que OL/GB não indexam.
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
| `catalog.config` | stdlib (os) | qualquer outro módulo do projeto |
| `ui.app` | `catalog.storage`, streamlit | `catalog.metadata`, `catalog.scanning`, `main` |
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
| `ISBNDB_API_KEY` | `""` | Chave gratuita do ISBNdb. Sem ela, `buscar_isbndb` é ignorado. |

---

## Como estender

### Nova fonte de API

1. Adicionar função `buscar_<nome>(isbn: str) -> dict | None` em `catalog/metadata/api.py`
2. Inserir no final da lista em `buscar_metadados()`
3. Adicionar teste em `tests/test_api.py` (happy path + empty + ConnectionError)
4. Documentar aqui em "Cascata de APIs"

### Novo filtro na UI

Adicionar widget na sidebar de `ui/app.py`. Filtrar sobre a lista `registros` já carregada em memória — não ler o arquivo novamente.

### Novo campo no schema

**Atenção:** requer migração dos dados existentes em `data/`. Etapas:
1. Adicionar campo em `CSV_HEADERS` em `catalog/config.py`
2. Atualizar todas as funções em `catalog/metadata/api.py` para populá-lo
3. Escrever script de migração que lê o JSONL antigo, adiciona o campo vazio e reescreve
4. Atualizar testes
