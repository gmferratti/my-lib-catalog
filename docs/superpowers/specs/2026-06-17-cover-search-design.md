# Design: busca de capas de alta qualidade

**Data:** 2026-06-17
**Status:** aprovado

---

## Problema

56 de 64 livros no acervo estão sem capa. Os 8 que têm usam OL-medium (~200 px) ou
GB-thumbnail (~128 px) — resolução insuficiente para um catálogo digital de qualidade.
A BrasilAPI, fonte principal para ISBNs brasileiros, raramente retorna `cover_url`.

A regra de negócio é: **capa de alta qualidade ou nada** — thumbnails de baixa
resolução não devem ser salvos.

---

## Solução

### Componentes novos

| Componente | Arquivo | Responsabilidade |
|---|---|---|
| `buscar_capa(isbn)` | `catalog/metadata/api.py` | Encontra e valida a melhor URL de capa disponível |
| Worker atualizado | `catalog/metadata/worker.py` | Chama `buscar_capa()` após `buscar_metadados()` |
| `--capas` flag | `scripts/main.py` | Modo batch: atualiza capas de todos os registros existentes |
| `make capas` | `Makefile` | Atalho para o modo batch |

---

## `buscar_capa(isbn: str) -> str`

Função independente da cascata de metadados. Retorna uma URL validada ou `""`.

### Cascata

**Estágio 1 — Open Library por ISBN (Large)**

```
HEAD https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false
```

- Timeout: 10 s
- `?default=false` → OL retorna 404 quando não há capa (em vez do placeholder cinza)
- HTTP 200 → retorna `https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg`
- HTTP 404 ou erro de rede → passa para estágio 2

Resolução típica: 300–500 px de largura.

**Estágio 2 — Google Books (zoom=0)**

```
GET https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}&key={GOOGLE_BOOKS_API_KEY}
```

1. Extrai `items[0].id` (volumeId) e confirma que `imageLinks` existe
2. Monta URL de alta resolução:
   `https://books.google.com/books/content?id={volumeId}&printsec=frontcover&img=1&zoom=0`
3. `HEAD` nessa URL + verifica `Content-Length > 5 000 bytes`
   - Válido → retorna URL
   - `Content-Length ≤ 5 000` ou erro → retorna `""`
   - Se o header `Content-Length` estiver ausente → assume válido (default `10_000`)

O check de Content-Length filtra os placeholders que o GB retorna como HTTP 200 mesmo
sem ter imagem disponível. Resolução típica: 400–800 px.

**Sem resultado:** retorna `""` — `capa_url` fica vazio no registro.

### Tratamento de erros

Qualquer `requests.RequestException` em qualquer estágio é capturada e o estágio
seguinte é tentado. A função nunca lança exceção.

---

## Integração no worker

```python
# catalog/metadata/worker.py — trecho do loop principal
registro = buscar_metadados(isbn)
registro["capa_url"] = buscar_capa(isbn)  # sempre sobrescreve — "" se nada de qualidade
salvar(registro)
```

A importação de `buscar_capa` vem do mesmo módulo `catalog.metadata.api`, sem nova
dependência.

---

## Modo batch (`--capas`)

Função `_atualizar_capas()` em `scripts/main.py`, acionada por `--capas`:

```
carregar_todos_registros()
para cada registro:
    isbn → buscar_capa(isbn)
    se URL nova ≠ URL atual → atualiza registro["capa_url"]
se houve mudanças → reescrever_registros()
```

Output no terminal:
- `✓  Título do livro` — capa encontrada
- `—  Título do livro` — nenhuma capa de qualidade disponível
- Resumo final: `N capa(s) atualizada(s) / M sem capa.`

---

## Makefile

```makefile
capas:  ## Busca capas de alta qualidade para todos os livros do acervo
    PYTHONPATH=. $(PYTHON) scripts/main.py --capas
```

Adicionado a `.PHONY`.

---

## Testes (`tests/test_api.py`)

| Teste | Cenário |
|---|---|
| `test_buscar_capa_ol_happy_path` | HEAD 200 → retorna URL OL-L |
| `test_buscar_capa_ol_404_fallback_gb` | HEAD 404 → GB API válido → retorna URL GB |
| `test_buscar_capa_sem_resultado` | OL 404 + GB falha → retorna `""` |
| `test_buscar_capa_gb_placeholder_rejeitado` | GB Content-Length ≤ 5 000 → retorna `""` |
| `test_buscar_capa_erro_de_rede_nao_lanca` | ConnectionError em OL → não propaga exceção |

---

## Arquivos modificados

| Arquivo | Mudança |
|---|---|
| `catalog/metadata/api.py` | + `buscar_capa()` |
| `catalog/metadata/__init__.py` | exportar `buscar_capa` |
| `catalog/metadata/worker.py` | chamar `buscar_capa()` após `buscar_metadados()` |
| `scripts/main.py` | + `--capas` flag + `_atualizar_capas()` |
| `Makefile` | + target `capas` |
| `tests/test_api.py` | + 5 novos testes |

---

## Verificação

```bash
# Testes
pytest tests/test_api.py -v

# Smoke test para um ISBN sem capa atual
PYTHONPATH=. python -c "
from catalog.metadata.api import buscar_capa
print(buscar_capa('9788592795788'))  # deve retornar URL não vazia
"

# Comando batch
make capas  # deve imprimir ✓ para a maioria dos 64 livros
```
