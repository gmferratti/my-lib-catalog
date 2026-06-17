# Covers & UI Metrics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add high-quality cover search (`buscar_capa`) and replace the 5 operational metrics in the Acervo tab with 3 meaningful numbers + a 2-column distribution panel (language + top subjects).

**Architecture:** `buscar_capa` is a standalone function in `catalog/metadata/api.py` that tries OL-Large via HEAD then GB via volumeId + Content-Length check. The worker calls it after `buscar_metadados`. A `--capas` batch mode in `scripts/main.py` retrofits covers for all existing records. The UI metrics refactor is entirely in `ui/app.py` with two new helper functions; no catalog module changes.

**Tech Stack:** Python 3.12, requests, Streamlit, pytest-mock

---

## File Map

| File | Change |
|---|---|
| `catalog/metadata/api.py` | + `buscar_capa(isbn)` |
| `catalog/metadata/__init__.py` | + export `buscar_capa` |
| `catalog/metadata/worker.py` | call `buscar_capa` after `buscar_metadados` |
| `scripts/main.py` | + `--capas` flag + `_atualizar_capas()` |
| `Makefile` | + `capas` in `.PHONY` + target |
| `tests/test_api.py` | + 5 tests for `buscar_capa` |
| `ui/app.py` | + `_estatisticas()`, + `_barra()`, refactor metrics in `_render_acervo()` |

---

## Task 1: `buscar_capa` — tests first

**Files:**
- Modify: `tests/test_api.py`
- Modify: `catalog/metadata/api.py`

- [ ] **Step 1: Add 5 failing tests to `tests/test_api.py`**

Add after the last test in the file (line 226):

```python
# ──────────────────────────────────────────────
# buscar_capa
# ──────────────────────────────────────────────

def _mock_head(mocker, status=200, content_length=None):
    resp = mocker.Mock()
    resp.status_code = status
    headers = {}
    if content_length is not None:
        headers["Content-Length"] = str(content_length)
    resp.headers = headers
    return resp


def test_buscar_capa_ol_happy_path(mocker):
    mocker.patch("requests.head", return_value=_mock_head(mocker, status=200))
    from catalog.metadata.api import buscar_capa
    url = buscar_capa(ISBN)
    assert url == f"https://covers.openlibrary.org/b/isbn/{ISBN}-L.jpg"


def test_buscar_capa_ol_404_fallback_gb(mocker):
    ol_resp = _mock_head(mocker, status=404)
    gb_data = {
        "totalItems": 1,
        "items": [{"id": "vol123", "volumeInfo": {"imageLinks": {"thumbnail": "x"}}}],
    }
    gb_resp = mocker.Mock()
    gb_resp.status_code = 200
    gb_resp.json.return_value = gb_data
    gb_resp.raise_for_status = mocker.Mock()

    gb_head = _mock_head(mocker, status=200, content_length=50000)

    mocker.patch("requests.head", side_effect=[ol_resp, gb_head])
    mocker.patch("requests.get", return_value=gb_resp)

    from catalog.metadata.api import buscar_capa
    url = buscar_capa(ISBN)
    assert "books.google.com" in url
    assert "vol123" in url


def test_buscar_capa_sem_resultado(mocker):
    mocker.patch("requests.head", return_value=_mock_head(mocker, status=404))
    mocker.patch("requests.get", return_value=mocker.Mock(
        status_code=200,
        json=lambda: {"totalItems": 0},
        raise_for_status=mocker.Mock(),
    ))
    from catalog.metadata.api import buscar_capa
    assert buscar_capa(ISBN) == ""


def test_buscar_capa_gb_placeholder_rejeitado(mocker):
    ol_resp = _mock_head(mocker, status=404)
    gb_data = {
        "totalItems": 1,
        "items": [{"id": "vol123", "volumeInfo": {"imageLinks": {"thumbnail": "x"}}}],
    }
    gb_resp = mocker.Mock()
    gb_resp.status_code = 200
    gb_resp.json.return_value = gb_data
    gb_resp.raise_for_status = mocker.Mock()

    gb_head = _mock_head(mocker, status=200, content_length=3000)

    mocker.patch("requests.head", side_effect=[ol_resp, gb_head])
    mocker.patch("requests.get", return_value=gb_resp)

    from catalog.metadata.api import buscar_capa
    assert buscar_capa(ISBN) == ""


def test_buscar_capa_erro_de_rede_nao_lanca(mocker):
    mocker.patch("requests.head", side_effect=requests.ConnectionError)
    from catalog.metadata.api import buscar_capa
    assert buscar_capa(ISBN) == ""
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_api.py -k "buscar_capa" -v
```

Expected: 5 failures — `ImportError: cannot import name 'buscar_capa'`

- [ ] **Step 3: Implement `buscar_capa` in `catalog/metadata/api.py`**

Add after `buscar_isbndb` and before `buscar_metadados` (around line 131):

```python
def buscar_capa(isbn: str) -> str:
    """Busca capa de alta resolução. Retorna URL validada ou '' se nada disponível."""
    # Estágio 1 — Open Library Large
    try:
        r = requests.head(
            f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false",
            timeout=10,
        )
        if r.status_code == 200:
            return f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg"
    except requests.RequestException:
        pass

    # Estágio 2 — Google Books zoom=0
    try:
        url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
        if GOOGLE_BOOKS_API_KEY:
            url += f"&key={GOOGLE_BOOKS_API_KEY}"
        data = _get_json(url)
        if not data or not data.get("totalItems"):
            return ""
        item = data["items"][0]
        if not item.get("volumeInfo", {}).get("imageLinks"):
            return ""
        volume_id = item["id"]
        capa_url = (
            f"https://books.google.com/books/content"
            f"?id={volume_id}&printsec=frontcover&img=1&zoom=0"
        )
        head = requests.head(capa_url, timeout=10)
        tamanho = int(head.headers.get("Content-Length", 10_000))
        if tamanho > 5_000:
            return capa_url
    except requests.RequestException:
        pass

    return ""
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_api.py -k "buscar_capa" -v
```

Expected: 5 passed

- [ ] **Step 5: Run full suite to confirm no regressions**

```bash
PYTHONPATH=. .venv/bin/pytest -v
```

Expected: all green

- [ ] **Step 6: Commit**

```bash
git add catalog/metadata/api.py tests/test_api.py
git commit -m "feat(metadata): adicionar buscar_capa com cascata OL-Large + GB zoom=0"
```

---

## Task 2: Export + worker integration

**Files:**
- Modify: `catalog/metadata/__init__.py`
- Modify: `catalog/metadata/worker.py`

- [ ] **Step 1: Export `buscar_capa` from `__init__.py`**

Replace the entire file content of `catalog/metadata/__init__.py`:

```python
from .api import buscar_capa, buscar_metadados
from .worker import worker

__all__ = ["buscar_capa", "buscar_metadados", "worker"]
```

- [ ] **Step 2: Update `worker.py` to call `buscar_capa` after `buscar_metadados`**

In `catalog/metadata/worker.py`, change line 5 from:
```python
from .api import buscar_metadados
```
to:
```python
from .api import buscar_capa, buscar_metadados
```

Then in the try block (after line 29 `registro = buscar_metadados(isbn)`), add:
```python
            registro["capa_url"] = buscar_capa(isbn)
```

Full updated try block:
```python
        try:
            registro = buscar_metadados(isbn)
            registro["capa_url"] = buscar_capa(isbn)
            salvar(registro)
            remover_pendente(isbn)
            if on_result is not None:
                on_result(registro)
```

- [ ] **Step 3: Run suite to confirm no regressions**

```bash
PYTHONPATH=. .venv/bin/pytest -v
```

Expected: all green

- [ ] **Step 4: Commit**

```bash
git add catalog/metadata/__init__.py catalog/metadata/worker.py
git commit -m "feat(worker): integrar buscar_capa no fluxo de escaneamento"
```

---

## Task 3: `--capas` batch mode + Makefile

**Files:**
- Modify: `scripts/main.py`
- Modify: `Makefile`

- [ ] **Step 1: Add `--capas` flag and `_atualizar_capas()` to `scripts/main.py`**

Add the import at top of `scripts/main.py` — change line 32:
```python
from catalog.metadata import buscar_metadados, worker
```
to:
```python
from catalog.metadata import buscar_capa, buscar_metadados, worker
```

Add `_atualizar_capas()` after `_reprocessar_nao_encontrados()` (before `def main()`):

```python
def _atualizar_capas() -> None:
    registros = carregar_todos_registros()
    if not registros:
        print("  → Nenhum registro no acervo.\n")
        return
    print(f"  → Buscando capas para {len(registros)} livro(s)...")
    atualizados = 0
    for r in registros:
        isbn = r["isbn"]
        titulo = r.get("titulo") or isbn
        nova_url = buscar_capa(isbn)
        if nova_url != r.get("capa_url", ""):
            r["capa_url"] = nova_url
            atualizados += 1
        simbolo = "✓" if nova_url else "—"
        print(f"     {simbolo}  {titulo}")
    if atualizados:
        reescrever_registros(registros)
        print(f"\n  → {atualizados} capa(s) atualizada(s).\n")
    else:
        print("\n  → Nenhuma capa nova encontrada.\n")
```

Update the entry block at the bottom of the file (lines 159–166):

```python
if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--reprocessar", action="store_true")
    parser.add_argument("--capas", action="store_true")
    args, _ = parser.parse_known_args()
    if args.reprocessar:
        _reprocessar_nao_encontrados()
    elif args.capas:
        _atualizar_capas()
    else:
        main()
```

- [ ] **Step 2: Add `capas` target to `Makefile`**

In `Makefile`, add `capas` to `.PHONY` and add the target:

Change `.PHONY` line from:
```makefile
.PHONY: install run ui reprocessar sync test test-v clean help
```
to:
```makefile
.PHONY: install run ui reprocessar capas sync test test-v clean help
```

Add after the `reprocessar` target:
```makefile
capas:          ## Busca capas de alta qualidade para todos os livros do acervo
	PYTHONPATH=. $(PYTHON) scripts/main.py --capas
```

- [ ] **Step 3: Smoke test**

```bash
PYTHONPATH=. .venv/bin/python -c "
from catalog.metadata.api import buscar_capa
url = buscar_capa('9788592795788')
print('OK:', url if url else '(sem capa)')
"
```

Expected: prints a URL or `(sem capa)` — no exception.

- [ ] **Step 4: Commit**

```bash
git add scripts/main.py Makefile
git commit -m "feat(cli): adicionar --capas e make capas para atualização em lote"
```

---

## Task 4: UI metrics refactor

**Files:**
- Modify: `ui/app.py`

- [ ] **Step 1: Add language normalization map and `_estatisticas()` helper**

Add after the `ESTILOS` dict (after line 47 in `ui/app.py`), before the Cache helpers section:

```python
_IDIOMA_NORM = {
    "pt": "Português", "por": "Português", "pt-br": "Português", "pt-BR": "Português",
    "en": "Inglês", "eng": "Inglês",
    "es": "Espanhol", "spa": "Espanhol",
    "fr": "Francês", "fra": "Francês",
    "de": "Alemão", "deu": "Alemão", "ger": "Alemão",
    "ja": "Japonês", "jpn": "Japonês",
}


def _estatisticas(registros: list[dict]) -> dict:
    total = len(registros)
    total_paginas = sum(
        int(r["paginas"]) for r in registros
        if str(r.get("paginas", "")).isdigit()
    )
    com_capa = sum(1 for r in registros if r.get("capa_url"))

    contagem_idioma: dict[str, int] = {}
    for r in registros:
        cod = (r.get("idioma") or "").strip()
        if not cod:
            continue
        nome = _IDIOMA_NORM.get(cod, cod)
        contagem_idioma[nome] = contagem_idioma.get(nome, 0) + 1
    idiomas = sorted(contagem_idioma.items(), key=lambda x: -x[1])

    contagem_assunto: dict[str, int] = {}
    for r in registros:
        for termo in (r.get("assuntos") or "").split(","):
            termo = termo.strip()
            if termo:
                contagem_assunto[termo] = contagem_assunto.get(termo, 0) + 1
    assuntos = sorted(contagem_assunto.items(), key=lambda x: -x[1])[:5]

    return {
        "total": total,
        "total_paginas": total_paginas,
        "com_capa": com_capa,
        "idiomas": idiomas,
        "assuntos": assuntos,
    }


def _barra(valor: int, maximo: int, largura: int = 20) -> str:
    preenchimento = round(valor / maximo * largura) if maximo else 0
    return "█" * preenchimento
```

- [ ] **Step 2: Replace the 5 `st.metric()` block with new metrics + distribution panel in `_render_acervo()`**

Locate the block in `_render_acervo()` (lines 197–209):

```python
    total = len(registros)
    com_capa = sum(1 for r in registros if r.get("capa_url"))
    sem_meta = sum(1 for r in registros if r.get("fonte") == "nao_encontrado")
    manuais  = sum(1 for r in registros if r.get("fonte") == "manual")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total no acervo", total)
    c2.metric("Exibindo", len(filtrados))
    c3.metric("Com capa", com_capa)
    c4.metric("Sem metadados", sem_meta)
    c5.metric("Editados", manuais)
```

Replace with:

```python
    stats = _estatisticas(registros)

    m1, m2, m3 = st.columns(3)
    m1.metric("Total no acervo", stats["total"])
    m2.metric("Total de páginas", f"{stats['total_paginas']:,}".replace(",", "."))
    m3.metric("Com capa", stats["com_capa"])

    if stats["idiomas"] or stats["assuntos"]:
        col_idioma, col_assunto = st.columns(2)
        with col_idioma:
            st.markdown("**📚 Por idioma**")
            if stats["idiomas"]:
                maximo_i = stats["idiomas"][0][1]
                for nome, qtd in stats["idiomas"]:
                    barra = _barra(qtd, maximo_i, largura=12)
                    st.markdown(f"`{nome:<12}` {qtd:>4}  {barra}")
            else:
                st.caption("Sem dados de idioma.")
        with col_assunto:
            st.markdown("**🏷️ Top assuntos**")
            if stats["assuntos"]:
                maximo_a = stats["assuntos"][0][1]
                for termo, qtd in stats["assuntos"]:
                    barra = _barra(qtd, maximo_a, largura=12)
                    st.markdown(f"`{termo:<20}` {qtd:>4}  {barra}")
            else:
                st.caption("Sem dados de assuntos.")
```

- [ ] **Step 3: Start the Streamlit UI and verify**

```bash
PYTHONPATH=. .venv/bin/streamlit run ui/app.py
```

In the Acervo tab, confirm:
- 3 metrics: "Total no acervo", "Total de páginas", "Com capa"
- 2-column distribution panel with idioma + assuntos
- No "Sem metadados", "Editados", or "Exibindo" metrics
- Filters and ordering still work normally

- [ ] **Step 4: Commit**

```bash
git add ui/app.py
git commit -m "feat(ui): substituir métricas operacionais por painel de distribuição do acervo"
```

---

## Task 5: Push to GitHub

- [ ] **Step 1: Switch to personal GitHub account**

```bash
gh auth switch --user gmferratti
```

- [ ] **Step 2: Push**

```bash
git push
```

- [ ] **Step 3: Switch back to corporate account**

```bash
gh auth switch --user gmferratti-asaas
```

---

## Verification checklist

```bash
# All tests pass
PYTHONPATH=. .venv/bin/pytest -v

# buscar_capa smoke test
PYTHONPATH=. .venv/bin/python -c "
from catalog.metadata.api import buscar_capa
print(buscar_capa('9788592795788'))
print(buscar_capa('9781098115784'))
"

# Batch cover update
make capas

# UI check
streamlit run ui/app.py
```
