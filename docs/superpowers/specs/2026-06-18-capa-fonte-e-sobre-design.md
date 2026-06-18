# Design: capa_fonte + aba Sobre

**Data:** 2026-06-18
**Status:** Aprovado

---

## Contexto

Duas melhorias independentes solicitadas após a implementação da cascata de 7 estágios de busca de capas:

1. Rastrear qual serviço forneceu a imagem de capa (análogo ao campo `fonte` para metadados).
2. Adicionar aba "Sobre" ao Streamlit com texto descritivo do projeto.

---

## Feature 1: campo `capa_fonte`

### Schema

Adicionar `"capa_fonte"` a `CSV_HEADERS` em `catalog/config.py`, imediatamente após `"capa_url"`.

Schema resultante:
```
isbn, titulo, autores, editora, ano, paginas, idioma, assuntos,
capa_url, capa_fonte, fonte, data_cadastro
```

**Valores válidos de `capa_fonte`:**

| Valor | Origem |
|---|---|
| `openlibrary_isbn` | Stage 1: OL direto por ISBN (L ou M) |
| `openlibrary_cover_i` | Stage 2: OL via cover_i ID |
| `googlebooks_isbn` | Stage 3: Google Books por ISBN |
| `googlebooks_titulo` | Stage 4: Google Books por título+autor |
| `openlibrary_titulo` | Stage 5: OL por título+autor |
| `duckduckgo` | Stage 6: DuckDuckGo image search |
| `google_cse` | Stage 7: Google Custom Search |
| `manual` | Override de `data/capas_manuais.json` |
| `legado` | Registros pré-existentes com capa mas sem rastreio |
| `""` | Sem capa |

### API: `buscar_capa()` e `_buscar_capa_rede()`

**Mudança de assinatura:**

```python
# Antes
def buscar_capa(isbn, titulo="", autores="") -> str:

# Depois
def buscar_capa(isbn, titulo="", autores="") -> tuple[str, str]:
    # retorna (capa_url, capa_fonte)
```

`_buscar_capa_rede()` também passa a retornar `tuple[str, str]`.

Cada estágio interno continua retornando `str` (só a URL), mas o estágio que tiver sucesso é identificado pelo bloco em `_buscar_capa_rede()` que o chamou, e a fonte é embutida no retorno da tupla.

**Cache `capas_cache.json`:**

Formato atual: `{ "isbn": "url_string" }`

Formato novo: `{ "isbn": {"url": "...", "fonte": "..."} }`

A migração do cache é feita no próprio `_get_cache()` na primeira leitura (compat shim inline): se o valor for uma string, converte para `{"url": value, "fonte": "legado"}`.

**Override manual (`capas_manuais.json`):** fonte é sempre `"manual"`.

### Callers a atualizar

| Arquivo | Mudança |
|---|---|
| `catalog/metadata/worker.py` | Desestruturar tupla; salvar `capa_fonte` no registro |
| `scripts/main.py` (`_atualizar_capas`) | Desestruturar tupla; atualizar `capa_fonte` no registro |

### Migração de dados

Script one-shot `scripts/migrar_capa_fonte.py`:

1. Lê `data/biblioteca.jsonl`
2. Para cada registro: se `capa_url` não vazio, adiciona `capa_fonte: "legado"`; se vazio, `capa_fonte: ""`
3. Reescreve `biblioteca.jsonl` e `biblioteca.csv` via `reescrever_registros()`

O script é executado uma única vez após o deploy.

### UI: badge de `capa_fonte` nos cards

Em `ui/app.py`, adicionar `CAPA_FONTE_CORES` e `CAPA_FONTE_LABELS` e uma função `_badge_capa(capa_fonte)`.

Registros com `capa_fonte` vazio ou `"legado"` não exibem badge (comportamento silencioso enquanto o acervo é re-buscado com `--capas`).

**Paleta:**

| `capa_fonte` | Label | Cor |
|---|---|---|
| `openlibrary_isbn` | OL ISBN | `#1b5e20` |
| `openlibrary_cover_i` | OL Cover ID | `#2e7d32` |
| `openlibrary_titulo` | OL Título | `#388e3c` |
| `googlebooks_isbn` | GB ISBN | `#0d47a1` |
| `googlebooks_titulo` | GB Título | `#1565c0` |
| `duckduckgo` | DuckDuckGo | `#e65100` |
| `google_cse` | Google CSE | `#4a148c` |
| `manual` | Manual | `#37474f` |

O badge aparece abaixo do badge de metadados no card, e o campo é incluído na tabela de dados e no modal de edição (somente leitura).

---

## Feature 2: aba "Sobre"

### Estrutura

Adicionar uma terceira aba ao `st.tabs()` em `ui/app.py`:

```python
tab_acervo, tab_estantes, tab_sobre = st.tabs(["📚 Acervo", "🗂️ Estantes", "📖 Sobre"])
```

Implementada como `_render_sobre()`.

### Conteúdo (texto aprovado pelo usuário)

```
My Lib Catalog nasceu de uma necessidade muito simples: Gustavo Ferratti, um apaixonado
por livros que mora em Araraquara, interior de São Paulo, precisava de uma forma de
organizar e consultar o próprio acervo pessoal de livros que crescia rapidamente.

O projeto foi construído inteiramente por ele (AI-assisted) com muito amor e carinho,
de forma gratuita, de bookworm para bookworm. Nada de algoritmos de recomendação, nada
de dados sendo vendidos. Só você, seus livros, uma interface que respeita o seu tempo
e o bom e velho open source.

Como funciona: você escaneia o código de barras do livro com um leitor de código de
barras pela CLI (rodar comando make run para entrar no loop principal); o sistema busca
os metadados automaticamente a partir do ISBN em múltiplas fontes (Open Library,
Google Books, BrasilAPI, ISBNdb) e organiza tudo para você consultar por autor, ano,
idioma, etc. Se algo não vier certo, há a possibilidade de ajuste manual.

Organização de estantes: a funcionalidade de organização física das estantes está em
desenvolvimento. Em breve você poderá distribuir seus livros pelas prateleiras de
forma otimizada.
```

---

## Arquivos modificados

| Arquivo | Mudança |
|---|---|
| `catalog/config.py` | Adicionar `"capa_fonte"` a `CSV_HEADERS` |
| `catalog/metadata/api.py` | `buscar_capa()` e `_buscar_capa_rede()` retornam tupla; compat shim no cache |
| `catalog/metadata/worker.py` | Desestruturar tupla, salvar `capa_fonte` |
| `scripts/main.py` | Desestruturar tupla no `_atualizar_capas()` |
| `scripts/migrar_capa_fonte.py` | Novo: migration one-shot |
| `ui/app.py` | Badge `capa_fonte`; aba Sobre |
| `tests/test_api.py` | Atualizar todos os asserts de `buscar_capa()` para tupla |

**Não muda:** `catalog/storage/`, `catalog/organizer/`, `catalog/scanning/`

---

## Sequência de implementação

1. Schema: `CSV_HEADERS` + compat shim no cache
2. API: `buscar_capa()` e `_buscar_capa_rede()` retornam tupla + atualizar testes
3. Callers: `worker.py` e `scripts/main.py`
4. Migration script
5. UI: badge `capa_fonte` + aba Sobre
