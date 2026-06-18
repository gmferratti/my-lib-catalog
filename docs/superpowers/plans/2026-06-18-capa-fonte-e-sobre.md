# capa_fonte + Aba Sobre Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `capa_fonte` field to track which service provided each book cover image, and add a "Sobre" tab to the Streamlit UI.

**Architecture:** `buscar_capa()` changes from returning `str` to `tuple[str, str]` — `(capa_url, capa_fonte)`. The existing `capas_cache.json` is migrated inline via a compat shim in `_get_cache()` (old string values → `{"url": ..., "fonte": "legado"}`). A one-shot migration script (`migrar_capa_fonte.py`) adds `capa_fonte` to all JSONL + CSV records. The UI renders a second badge on each card showing the cover source, and a new "Sobre" tab is added.

**Tech Stack:** Python 3.11, requests, Streamlit, csv, json, pytest, pytest-mock.

---

## File map

| File | Change |
|---|---|
| `catalog/config.py` | Add `"capa_fonte"` to `CSV_HEADERS` after `"capa_url"` |
| `catalog/metadata/api.py` | Compat shim in `_get_cache()`; `buscar_capa()` + `_buscar_capa_rede()` return `tuple[str, str]` |
| `catalog/metadata/worker.py` | Destructure tuple; save `capa_fonte` to registro |
| `scripts/main.py` | Destructure tuple in `_atualizar_capas()` |
| `scripts/migrar_capa_fonte.py` | New one-shot migration script |
| `ui/app.py` | `CAPA_FONTE_CORES`, `CAPA_FONTE_LABELS`, `_badge_capa()`; second badge in cards; `capa_fonte` in table + edit dialog; third tab "📖 Sobre"; `_render_sobre()` |
| `tests/test_api.py` | Add `import json`; new compat shim test; update all `buscar_capa()` assertions to unpack tuple |

---

## Task 1: Schema + cache compat shim

**Files:**
- Modify: `catalog/config.py`
- Modify: `catalog/metadata/api.py` (only `_get_cache`)
- Modify: `tests/test_api.py` (add import + new test)

- [ ] **Step 1: Add `import json` to the test file**

Open `tests/test_api.py` and add `import json` below `import requests`:

```python
import pytest
import requests
import json

import catalog.metadata.api as api_module
```

- [ ] **Step 2: Write the failing test for the compat shim**

Add this test at the end of the `buscar_capa` section of `tests/test_api.py` (after `test_buscar_capa_override_vazio_suprime_rede`):

```python
def test_get_cache_compat_shim_converte_string_para_dict(mocker, tmp_path):
    """Old cache format {isbn: url_string} is converted on load to {isbn: {"url": ..., "fonte": "legado"}}."""
    old_cache = {ISBN: "https://exemplo.com/capa.jpg"}
    cache_file = tmp_path / "capas_cache.json"
    cache_file.write_text(json.dumps(old_cache), encoding="utf-8")
    mocker.patch.object(api_module, "_capas_cache", None)
    mocker.patch.object(api_module, "CAPAS_CACHE_FILE", str(cache_file))
    from catalog.metadata.api import _get_cache
    cache = _get_cache()
    assert cache[ISBN] == {"url": "https://exemplo.com/capa.jpg", "fonte": "legado"}
```

- [ ] **Step 3: Run the new test to confirm it fails**

```bash
cd /home/gustavo-ferratti/Documentos/projetos/my-lib-catalog
pytest tests/test_api.py::test_get_cache_compat_shim_converte_string_para_dict -v
```

Expected: FAIL — `assert "https://exemplo.com/capa.jpg" == {"url": ..., "fonte": "legado"}`

- [ ] **Step 4: Add `"capa_fonte"` to `CSV_HEADERS` in `catalog/config.py`**

```python
CSV_HEADERS = [
    "isbn", "titulo", "autores", "editora", "ano",
    "paginas", "idioma", "assuntos", "capa_url", "capa_fonte", "fonte", "data_cadastro",
]
```

- [ ] **Step 5: Add the compat shim to `_get_cache()` in `catalog/metadata/api.py`**

Replace the current `_get_cache` function (lines 143–150) with:

```python
def _get_cache() -> dict:
    global _capas_cache
    if _capas_cache is None:
        try:
            raw = json.loads(Path(CAPAS_CACHE_FILE).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            raw = {}
        # Compat shim: old format was {isbn: url_string}; new format is {isbn: {"url": ..., "fonte": ...}}
        _capas_cache = {
            k: v if isinstance(v, dict) else {"url": v, "fonte": "legado"}
            for k, v in raw.items()
        }
    return _capas_cache
```

- [ ] **Step 6: Run all tests to confirm pass**

```bash
pytest tests/test_api.py -v
```

Expected: All 43 tests pass (42 original + 1 new).

- [ ] **Step 7: Commit**

```bash
git add catalog/config.py catalog/metadata/api.py tests/test_api.py
git commit -m "feat(schema): add capa_fonte to CSV_HEADERS and cache compat shim"
```

---

## Task 2: `buscar_capa()` and `_buscar_capa_rede()` return `tuple[str, str]`

**Files:**
- Modify: `catalog/metadata/api.py` (two functions)
- Modify: `tests/test_api.py` (update 13 test assertions)

> **Context:** `buscar_capa()` currently returns `str`. After this task it returns `tuple[str, str]` — `(capa_url, capa_fonte)`. Each stage in `_buscar_capa_rede()` pairs its URL with its source name. A miss returns `("", "")`. The compat shim from Task 1 ensures the cache always serves a dict.

- [ ] **Step 1: Update all `buscar_capa()` test assertions to expect a tuple**

In `tests/test_api.py`, replace the test bodies as shown below. Each change unpacks the tuple and adds a `fonte` assertion.

**`test_buscar_capa_ol_happy_path`:**
```python
def test_buscar_capa_ol_happy_path(mocker):
    _reset_cache(mocker)
    mocker.patch("requests.head", return_value=_mock_head(mocker, status=200))
    from catalog.metadata.api import buscar_capa
    url, fonte = buscar_capa(ISBN)
    assert url == f"https://covers.openlibrary.org/b/isbn/{ISBN}-L.jpg"
    assert fonte == "openlibrary_isbn"
```

**`test_buscar_capa_ol_cover_id_sucesso`:**
```python
def test_buscar_capa_ol_cover_id_sucesso(mocker):
    _reset_cache(mocker)
    ol_isbn_resp = _mock_head(mocker, status=404)
    ol_id_head = _mock_head(mocker, status=200)

    ol_search_resp = mocker.Mock()
    ol_search_resp.status_code = 200
    ol_search_resp.json.return_value = {"docs": [{"cover_i": 99999}]}
    ol_search_resp.raise_for_status = mocker.Mock()

    mocker.patch("requests.head", side_effect=[ol_isbn_resp, ol_isbn_resp, ol_id_head])
    mocker.patch("requests.get", return_value=ol_search_resp)

    from catalog.metadata.api import buscar_capa
    url, fonte = buscar_capa(ISBN)
    assert "covers.openlibrary.org/b/id/99999" in url
    assert url.endswith("-L.jpg")
    assert fonte == "openlibrary_cover_i"
```

**`test_buscar_capa_ol_cover_id_usa_allow_redirects`:**
```python
def test_buscar_capa_ol_cover_id_usa_allow_redirects(mocker):
    _reset_cache(mocker)
    ol_isbn_resp = _mock_head(mocker, status=404)
    ol_id_head = _mock_head(mocker, status=200)

    ol_search_resp = mocker.Mock()
    ol_search_resp.status_code = 200
    ol_search_resp.json.return_value = {"docs": [{"cover_i": 77777}]}
    ol_search_resp.raise_for_status = mocker.Mock()

    mock_head = mocker.patch(
        "requests.head", side_effect=[ol_isbn_resp, ol_isbn_resp, ol_id_head]
    )
    mocker.patch("requests.get", return_value=ol_search_resp)

    from catalog.metadata.api import buscar_capa
    url, fonte = buscar_capa(ISBN)
    assert "covers.openlibrary.org/b/id/77777" in url
    assert fonte == "openlibrary_cover_i"

    cover_i_call = mock_head.call_args_list[2]
    assert cover_i_call.kwargs.get("allow_redirects") is True, (
        "Stage 2 HEAD request must pass allow_redirects=True to follow OL 302 redirects"
    )
```

**`test_buscar_capa_ol_404_fallback_gb`:**
```python
def test_buscar_capa_ol_404_fallback_gb(mocker):
    _reset_cache(mocker)
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

    mocker.patch("requests.head", side_effect=[ol_resp, ol_resp, gb_head])
    mocker.patch("requests.get", side_effect=[_mock_get_sem_cover(mocker), gb_resp])

    from catalog.metadata.api import buscar_capa
    url, fonte = buscar_capa(ISBN)
    assert "books.google.com" in url
    assert "vol123" in url
    assert fonte == "googlebooks_isbn"
```

**`test_buscar_capa_sem_resultado`:**
```python
def test_buscar_capa_sem_resultado(mocker):
    _reset_cache(mocker)
    mocker.patch("requests.head", return_value=_mock_head(mocker, status=404))
    gb_no_results = mocker.Mock()
    gb_no_results.status_code = 200
    gb_no_results.json.return_value = {"totalItems": 0}
    gb_no_results.raise_for_status = mocker.Mock()
    mocker.patch("requests.get", side_effect=[_mock_get_sem_cover(mocker), gb_no_results, _mock_ddg_sem_vqd(mocker)])
    from catalog.metadata.api import buscar_capa
    url, fonte = buscar_capa(ISBN)
    assert url == ""
    assert fonte == ""
```

**`test_buscar_capa_gb_placeholder_rejeitado`:**
```python
def test_buscar_capa_gb_placeholder_rejeitado(mocker):
    _reset_cache(mocker)
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

    mocker.patch("requests.head", side_effect=[ol_resp, ol_resp, gb_head])
    mocker.patch("requests.get", side_effect=[_mock_get_sem_cover(mocker), gb_resp, _mock_ddg_sem_vqd(mocker)])

    from catalog.metadata.api import buscar_capa
    url, fonte = buscar_capa(ISBN)
    assert url == ""
    assert fonte == ""
```

**`test_buscar_capa_erro_de_rede_nao_lanca`:**
```python
def test_buscar_capa_erro_de_rede_nao_lanca(mocker):
    _reset_cache(mocker)
    mocker.patch("requests.head", side_effect=requests.ConnectionError)
    mocker.patch("requests.get", side_effect=requests.ConnectionError)
    from catalog.metadata.api import buscar_capa
    url, fonte = buscar_capa(ISBN)
    assert url == ""
    assert fonte == ""
```

**`test_buscar_capa_miss_nao_cacheia`:**
```python
def test_buscar_capa_miss_nao_cacheia(mocker):
    _reset_cache(mocker)
    mocker.patch("requests.head", return_value=_mock_head(mocker, status=404))
    mocker.patch("requests.get", side_effect=[_mock_get_sem_cover(mocker), _mock_get_sem_cover(mocker), _mock_ddg_sem_vqd(mocker)])
    from catalog.metadata.api import buscar_capa
    url, fonte = buscar_capa(ISBN)
    assert url == ""
    assert fonte == ""
    api_module._salvar_cache.assert_not_called()
```

**`test_buscar_capa_stage4_titulo_autor`:**
```python
def test_buscar_capa_stage4_titulo_autor(mocker):
    _reset_cache(mocker)
    ol_404 = _mock_head(mocker, status=404)
    gb_hit = _mock_head(mocker, status=200, content_length=50_000)
    mocker.patch("requests.head", side_effect=[ol_404, ol_404, ol_404, gb_hit])

    ol_search_vazio = _mock_get_sem_cover(mocker)
    gb_isbn_sem_resultados = mocker.Mock()
    gb_isbn_sem_resultados.status_code = 200
    gb_isbn_sem_resultados.json.return_value = {"totalItems": 0}
    gb_isbn_sem_resultados.raise_for_status = mocker.Mock()
    gb_titulo_resp = mocker.Mock()
    gb_titulo_resp.status_code = 200
    gb_titulo_resp.json.return_value = {
        "totalItems": 1,
        "items": [{"id": "vol999", "volumeInfo": {"imageLinks": {"thumbnail": "x"}}}],
    }
    gb_titulo_resp.raise_for_status = mocker.Mock()
    mocker.patch("requests.get", side_effect=[ol_search_vazio, gb_isbn_sem_resultados, gb_titulo_resp])

    from catalog.metadata.api import buscar_capa
    url, fonte = buscar_capa(ISBN, titulo="Livro Teste", autores="Autor Um")
    assert "books.google.com" in url
    assert "vol999" in url
    assert fonte == "googlebooks_titulo"
```

**`test_buscar_capa_retorna_cache_sem_requisicao`:**
```python
def test_buscar_capa_retorna_cache_sem_requisicao(mocker):
    mocker.patch.object(api_module, "_capas_cache", {ISBN: {"url": "https://cached.example.com/capa.jpg", "fonte": "legado"}})
    mocker.patch("catalog.metadata.api._salvar_cache")
    mock_head = mocker.patch("requests.head")
    mock_get = mocker.patch("requests.get")

    from catalog.metadata.api import buscar_capa
    url, fonte = buscar_capa(ISBN)
    assert url == "https://cached.example.com/capa.jpg"
    assert fonte == "legado"
    mock_head.assert_not_called()
    mock_get.assert_not_called()
```

**`test_buscar_capa_override_manual_sem_rede`:**
```python
def test_buscar_capa_override_manual_sem_rede(mocker):
    _reset_cache(mocker)
    mocker.patch.object(
        api_module,
        "_carregar_capas_manuais",
        return_value={ISBN: "https://manual.exemplo.com/capa.jpg"},
    )
    mock_head = mocker.patch("requests.head")
    mock_get = mocker.patch("requests.get")

    from catalog.metadata.api import buscar_capa
    url, fonte = buscar_capa(ISBN)
    assert url == "https://manual.exemplo.com/capa.jpg"
    assert fonte == "manual"
    mock_head.assert_not_called()
    mock_get.assert_not_called()
```

**`test_buscar_capa_override_vazio_suprime_rede`:**
```python
def test_buscar_capa_override_vazio_suprime_rede(mocker):
    """ISBN com '' em capas_manuais.json deve retornar ('', '') sem chamar a rede."""
    _reset_cache(mocker)
    mocker.patch.object(api_module, "_carregar_capas_manuais", return_value={ISBN: ""})
    mock_head = mocker.patch("requests.head")
    mock_get = mocker.patch("requests.get")

    from catalog.metadata.api import buscar_capa
    url, fonte = buscar_capa(ISBN)
    assert url == ""
    assert fonte == ""
    mock_head.assert_not_called()
    mock_get.assert_not_called()
```

**`test_capa_ol_titulo_autor_happy_path`:**
```python
def test_capa_ol_titulo_autor_happy_path(mocker):
    _reset_cache(mocker)
    ol_404 = _mock_head(mocker, status=404)
    ol_titulo_head = _mock_head(mocker, status=200)
    mocker.patch("requests.head", side_effect=[ol_404, ol_404, ol_titulo_head])

    ol_cover_i_vazio = _mock_get_sem_cover(mocker)
    gb_sem_resultado = mocker.Mock()
    gb_sem_resultado.status_code = 200
    gb_sem_resultado.json.return_value = {"totalItems": 0}
    gb_sem_resultado.raise_for_status = mocker.Mock()
    ol_titulo_resp = mocker.Mock()
    ol_titulo_resp.status_code = 200
    ol_titulo_resp.json.return_value = {"docs": [{"cover_i": 44444}]}
    ol_titulo_resp.raise_for_status = mocker.Mock()
    mocker.patch("requests.get", side_effect=[ol_cover_i_vazio, gb_sem_resultado, gb_sem_resultado, ol_titulo_resp])

    from catalog.metadata.api import buscar_capa
    url, fonte = buscar_capa(ISBN, titulo="Mefisto", autores="Klaus Mann")
    assert "covers.openlibrary.org/b/id/44444" in url
    assert fonte == "openlibrary_titulo"
```

- [ ] **Step 2: Run tests to confirm failures**

```bash
pytest tests/test_api.py -k "buscar_capa" -v
```

Expected: Multiple FAILs — tests returning string where tuple expected, or assertions on wrong value.

- [ ] **Step 3: Replace `buscar_capa()` in `catalog/metadata/api.py`**

Replace the full `buscar_capa` function (lines 192–217):

```python
def buscar_capa(isbn: str, titulo: str = "", autores: str = "") -> tuple[str, str]:
    """Returns (capa_url, capa_fonte). Both '' if no cover available.

    Misses are not cached — every call retries ISBNs without a cover,
    so improvements in logic or new API data are picked up automatically.
    """
    cache = _get_cache()
    cached = cache.get(isbn)
    if cached:
        return (cached.get("url", ""), cached.get("fonte", "legado"))

    manuais = _carregar_capas_manuais()
    if isbn in manuais:
        url = manuais[isbn]
        if url:
            cache[isbn] = {"url": url, "fonte": "manual"}
            _salvar_cache()
        return (url, "manual" if url else "")

    url, capa_fonte = _buscar_capa_rede(isbn, titulo, autores)
    if url:
        cache[isbn] = {"url": url, "fonte": capa_fonte}
        _salvar_cache()
    return (url, capa_fonte)
```

- [ ] **Step 4: Replace `_buscar_capa_rede()` in `catalog/metadata/api.py`**

Replace the full `_buscar_capa_rede` function (lines 310–408):

```python
def _buscar_capa_rede(isbn: str, titulo: str = "", autores: str = "") -> tuple[str, str]:
    # Estágio 1 — Open Library por ISBN (Large depois Medium)
    # ?default=false faz o OL retornar 404 em vez de redirecionar para placeholder;
    # por isso allow_redirects não é necessário aqui (o Stage 2 precisa, pois /b/id/ redireciona para arquivo real).
    for size in ("L", "M"):
        try:
            r = requests.head(
                f"https://covers.openlibrary.org/b/isbn/{isbn}-{size}.jpg?default=false",
                timeout=5,
            )
            if r.status_code == 200:
                return (f"https://covers.openlibrary.org/b/isbn/{isbn}-{size}.jpg", "openlibrary_isbn")
        except requests.RequestException:
            pass

    # Estágio 2 — Open Library por cover_i (cobertura muito maior que por ISBN)
    try:
        data = _get_json(
            f"https://openlibrary.org/search.json?isbn={isbn}&fields=cover_i",
            tentativas=1, timeout=5,
        )
        docs = (data or {}).get("docs", [])
        cover_i = docs[0].get("cover_i") if docs else None
        if cover_i:
            r = requests.head(
                f"https://covers.openlibrary.org/b/id/{cover_i}-L.jpg",
                timeout=5,
                allow_redirects=True,
            )
            if r.status_code == 200:
                return (f"https://covers.openlibrary.org/b/id/{cover_i}-L.jpg", "openlibrary_cover_i")
    except requests.RequestException:
        pass

    # Estágio 3 — Google Books zoom=0 por ISBN
    try:
        url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
        if GOOGLE_BOOKS_API_KEY:
            url += f"&key={GOOGLE_BOOKS_API_KEY}"
        data = _get_json(url, tentativas=1, timeout=5)
        if data and data.get("totalItems"):
            item = data["items"][0]
            if item.get("volumeInfo", {}).get("imageLinks"):
                volume_id = item["id"]
                capa_url = (
                    f"https://books.google.com/books/content"
                    f"?id={volume_id}&printsec=frontcover&img=1&zoom=0"
                )
                head = requests.head(capa_url, timeout=5)
                tamanho = int(head.headers.get("Content-Length", 10_000))
                if tamanho > 5_000:
                    return (capa_url, "googlebooks_isbn")
    except requests.RequestException:
        pass

    # Estágio 4 — Google Books por título+autor (cobre ISBNs brasileiros sem indexação por ISBN)
    if titulo:
        try:
            autor_principal = (autores or "").split(",")[0].strip()
            query = f'intitle:"{titulo}"'
            if autor_principal:
                query += f' inauthor:"{autor_principal}"'
            url = f"https://www.googleapis.com/books/v1/volumes?q={requests.utils.quote(query)}"
            if GOOGLE_BOOKS_API_KEY:
                url += f"&key={GOOGLE_BOOKS_API_KEY}"
            data = _get_json(url, tentativas=1, timeout=5)
            if data and data.get("totalItems"):
                for item in data.get("items", []):
                    if not item.get("volumeInfo", {}).get("imageLinks"):
                        continue
                    volume_id = item["id"]
                    capa_url = (
                        f"https://books.google.com/books/content"
                        f"?id={volume_id}&printsec=frontcover&img=1&zoom=0"
                    )
                    head = requests.head(capa_url, timeout=5)
                    tamanho = int(head.headers.get("Content-Length", 10_000))
                    if tamanho > 5_000:
                        return (capa_url, "googlebooks_titulo")
        except requests.RequestException:
            pass

    # Estágio 5 — Open Library por título+autor (edições sem indexação por ISBN)
    if titulo:
        url = _capa_ol_titulo_autor(titulo, autores)
        if url:
            return (url, "openlibrary_titulo")

    # Estágio 6 — DuckDuckGo image search (fallback informal; sem chave, sem dependências)
    url = _capa_duckduckgo(isbn, titulo, autores)
    if url:
        return (url, "duckduckgo")

    # Estágio 7 — Google Custom Search Images (opcional; requer GOOGLE_CUSTOM_SEARCH_KEY + CX)
    url = _capa_google_cse(isbn, titulo, autores)
    if url:
        return (url, "google_cse")

    return ("", "")
```

- [ ] **Step 5: Run all tests to confirm pass**

```bash
pytest tests/test_api.py -v
```

Expected: All 44 tests pass.

- [ ] **Step 6: Commit**

```bash
git add catalog/metadata/api.py tests/test_api.py
git commit -m "feat(api): buscar_capa returns (url, capa_fonte) tuple"
```

---

## Task 3: Update callers

**Files:**
- Modify: `catalog/metadata/worker.py`
- Modify: `scripts/main.py`

> **Context:** Both files call `buscar_capa()` and assign the result directly to `registro["capa_url"]`. After Task 2, `buscar_capa()` returns a tuple — callers must destructure it and save `capa_fonte` separately.

- [ ] **Step 1: Update `catalog/metadata/worker.py`**

Replace the current `worker.py` content entirely with:

```python
import queue
import threading
from collections.abc import Callable

from .api import buscar_capa, buscar_metadados
from ..storage.persistence import remover_pendente, salvar


def worker(
    fila: queue.Queue,
    parar_evento: threading.Event,
    on_result: Callable[[dict], None] | None = None,
) -> None:
    """Consome ISBNs da fila e busca os metadados em background.

    on_result é chamado com o registro salvo (sucesso) ou com
    {"isbn": ..., "_erro": ...} em caso de exceção inesperada.
    """
    while not parar_evento.is_set():
        try:
            isbn = fila.get(timeout=0.5)
        except queue.Empty:
            continue
        if isbn is None:
            fila.task_done()
            break

        try:
            registro = buscar_metadados(isbn)
            metadata_capa = registro.get("capa_url", "")
            capa_dedicada, capa_fonte = buscar_capa(
                isbn, registro.get("titulo", ""), registro.get("autores", "")
            )
            if capa_dedicada:
                registro["capa_url"] = capa_dedicada
                registro["capa_fonte"] = capa_fonte
            else:
                registro["capa_url"] = metadata_capa
                registro["capa_fonte"] = ""
            salvar(registro)
            remover_pendente(isbn)
            if on_result is not None:
                on_result(registro)
        except Exception as e:
            # ISBN permanece em pendentes.txt para retry na próxima execução
            if on_result is not None:
                on_result({"isbn": isbn, "_erro": str(e)})
        finally:
            fila.task_done()
```

- [ ] **Step 2: Update `_atualizar_capas()` in `scripts/main.py`**

Replace the `_atualizar_capas` function (lines 83–125) with:

```python
def _atualizar_capas(fix: bool = False) -> None:
    registros = carregar_todos_registros()
    if not registros:
        print("  → Nenhum registro no acervo.\n")
        return

    if fix:
        com_capa = [r for r in registros if r.get("capa_url")]
        if com_capa:
            print(f"  → Verificando {len(com_capa)} URL(s) existente(s)...", flush=True)
            quebradas = 0
            for r in com_capa:
                if not verificar_capa(r["capa_url"]):
                    print(f"     ✗  {r.get('titulo') or r['isbn']}", flush=True)
                    r["capa_url"] = ""
                    r["capa_fonte"] = ""
                    limpar_cache_capa(r["isbn"])
                    quebradas += 1
            if quebradas:
                reescrever_registros(registros)
                print(f"  → {quebradas} URL(s) quebrada(s) removida(s).\n", flush=True)
            else:
                print("  → Todas as capas OK.\n", flush=True)

    total = len(registros)
    print(f"  → {total} livro(s) — cache: pula já buscados...", flush=True)
    atualizados = 0
    for i, r in enumerate(registros, 1):
        isbn = r["isbn"]
        titulo = r.get("titulo") or isbn
        em_cache = isbn in _get_cache()
        nova_url, nova_fonte = buscar_capa(isbn, r.get("titulo", ""), r.get("autores", ""))
        flag = "[cache]" if em_cache else "      "
        simbolo = "✓" if nova_url else "—"
        print(f"     [{i:>2}/{total}] {simbolo} {flag}  {titulo}", flush=True)
        if nova_url != r.get("capa_url", ""):
            r["capa_url"] = nova_url
            r["capa_fonte"] = nova_fonte
            atualizados += 1

    if atualizados:
        reescrever_registros(registros)
        print(f"\n  → {atualizados} registro(s) atualizado(s).\n")
    else:
        print("\n  → Nenhuma alteração.\n")
```

- [ ] **Step 3: Run all tests to confirm pass**

```bash
pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add catalog/metadata/worker.py scripts/main.py
git commit -m "feat(worker): store capa_fonte from buscar_capa tuple"
```

---

## Task 4: Migration script

**Files:**
- Create: `scripts/migrar_capa_fonte.py`

> **Context:** Existing records in `biblioteca.jsonl` and `biblioteca.csv` don't have the `capa_fonte` field. This one-shot script adds it: `"legado"` for records with a cover URL, `""` for records without. Run it once after deploying Task 1–3. Safe to re-run (skips records already migrated).

- [ ] **Step 1: Create the migration script**

```python
#!/usr/bin/env python3
"""One-shot migration: add capa_fonte to all existing records in biblioteca.jsonl / .csv."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from catalog.storage import carregar_todos_registros, reescrever_registros


def main() -> None:
    registros = carregar_todos_registros()
    if not registros:
        print("Nenhum registro encontrado.")
        return

    atualizados = 0
    for r in registros:
        if "capa_fonte" not in r:
            r["capa_fonte"] = "legado" if r.get("capa_url") else ""
            atualizados += 1

    if atualizados:
        reescrever_registros(registros)
        print(f"{atualizados} registro(s) migrado(s) — campo capa_fonte adicionado.")
    else:
        print("Todos os registros já têm capa_fonte. Nada a migrar.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Make the script executable and test it**

```bash
chmod +x scripts/migrar_capa_fonte.py
python scripts/migrar_capa_fonte.py
```

Expected output (example): `64 registro(s) migrado(s) — campo capa_fonte adicionado.`

- [ ] **Step 3: Verify a few records have capa_fonte**

```bash
python -c "
import json
records = [json.loads(l) for l in open('data/biblioteca.jsonl') if l.strip()]
with_fonte = sum(1 for r in records if 'capa_fonte' in r)
print(f'{with_fonte}/{len(records)} registros com capa_fonte')
samples = [(r.get('titulo','?')[:40], r.get('capa_fonte','MISSING')) for r in records[:3]]
for t, f in samples: print(f'  {t!r}: {f!r}')
"
```

Expected: all records have `capa_fonte`, values are either `"legado"` or `""`.

- [ ] **Step 4: Commit**

```bash
git add scripts/migrar_capa_fonte.py data/biblioteca.jsonl data/biblioteca.csv
git commit -m "feat(migration): add capa_fonte field to existing records"
```

---

## Task 5: UI — `capa_fonte` badge + aba Sobre

**Files:**
- Modify: `ui/app.py`

> **Context:** `ui/app.py` currently has 2 tabs (`Acervo`, `Estantes`). This task adds: (1) `CAPA_FONTE_CORES` + `CAPA_FONTE_LABELS` + `_badge_capa()` function, (2) a second badge below the metadata badge in every card (only for known non-legacy sources), (3) `capa_fonte` in the table view and in the edit dialog (read-only), (4) a third tab `📖 Sobre` with `_render_sobre()`. No test needed — UI changes require manual verification.

- [ ] **Step 1: Add `CAPA_FONTE_CORES` and `CAPA_FONTE_LABELS` dicts after `FONTE_LABELS` in `ui/app.py`**

After the `FONTE_LABELS` dict (line 41), add:

```python
CAPA_FONTE_CORES = {
    "openlibrary_isbn":    "#1b5e20",
    "openlibrary_cover_i": "#2e7d32",
    "openlibrary_titulo":  "#388e3c",
    "googlebooks_isbn":    "#0d47a1",
    "googlebooks_titulo":  "#1565c0",
    "duckduckgo":          "#e65100",
    "google_cse":          "#4a148c",
    "manual":              "#37474f",
}

CAPA_FONTE_LABELS = {
    "openlibrary_isbn":    "OL ISBN",
    "openlibrary_cover_i": "OL Cover ID",
    "openlibrary_titulo":  "OL Título",
    "googlebooks_isbn":    "GB ISBN",
    "googlebooks_titulo":  "GB Título",
    "duckduckgo":          "DuckDuckGo",
    "google_cse":          "Google CSE",
    "manual":              "Manual",
}
```

- [ ] **Step 2: Add `_badge_capa()` function after `_badge()` in `ui/app.py`**

After the `_badge` function (line ~118), add:

```python
def _badge_capa(capa_fonte: str) -> str:
    if not capa_fonte or capa_fonte == "legado":
        return ""
    cor = CAPA_FONTE_CORES.get(capa_fonte, "#78909c")
    label = CAPA_FONTE_LABELS.get(capa_fonte, capa_fonte)
    return (
        f'<span style="background:{cor};color:white;padding:2px 8px;'
        f'border-radius:4px;font-size:0.75rem">{label}</span>'
    )
```

- [ ] **Step 3: Show second badge in cards**

In `_render_acervo()`, in the card loop, after the line `st.markdown(_badge(r.get("fonte", "")), unsafe_allow_html=True)`, add:

```python
badge_capa = _badge_capa(r.get("capa_fonte", ""))
if badge_capa:
    st.markdown(badge_capa, unsafe_allow_html=True)
```

- [ ] **Step 4: Add `capa_fonte` to the table view**

In `_render_acervo()`, in the `st.dataframe` call inside `with st.expander("Ver tabela completa")`, update `column_order` to include `"capa_fonte"` after `"capa_url"`:

```python
st.dataframe(rows, width="stretch",
             column_order=["isbn", "titulo", "autores", "editora", "ano",
                           "paginas", "idioma", "assuntos", "capa_fonte", "fonte",
                           "data_cadastro", "capa_url"])
```

- [ ] **Step 5: Add `capa_fonte` read-only display to the edit dialog**

In `_dialog_editar()`, in the `if capa_atual:` block where we show `col_info`, add a line after the `fonte original` line:

```python
with col_info:
    st.markdown(f"**ISBN:** `{isbn}`")
    st.markdown(f"**Fonte original:** {registro.get('fonte', '—')}")
    capa_fonte_label = CAPA_FONTE_LABELS.get(
        registro.get("capa_fonte", ""), registro.get("capa_fonte") or "—"
    )
    st.markdown(f"**Fonte da capa:** {capa_fonte_label}")
    st.markdown(f"**Cadastrado em:** {registro.get('data_cadastro', '—')}")
```

- [ ] **Step 6: Add "Sobre" tab and `_render_sobre()` function**

Replace the `main()` function in `ui/app.py`:

```python
def _render_sobre() -> None:
    st.header("Sobre o My Lib Catalog")

    col, _ = st.columns([2, 1])
    with col:
        st.markdown("""
My Lib Catalog nasceu de uma necessidade muito simples: Gustavo Ferratti, um apaixonado
por livros que mora em Araraquara, interior de São Paulo, precisava de uma forma de
organizar e consultar o próprio acervo pessoal de livros que crescia rapidamente.

O projeto foi construído inteiramente por ele (AI-assisted) com muito amor e carinho,
de forma gratuita, de bookworm para bookworm. Nada de algoritmos de recomendação, nada
de dados sendo vendidos. Só você, seus livros, uma interface que respeita o seu tempo
e o bom e velho open source.

**Como funciona:** você escaneia o código de barras do livro com um leitor de código de
barras pela CLI (rodar comando `make run` para entrar no loop principal); o sistema busca
os metadados automaticamente a partir do ISBN em múltiplas fontes (Open Library,
Google Books, BrasilAPI, ISBNdb) e organiza tudo para você consultar por autor, ano,
idioma, etc. Se algo não vier certo, há a possibilidade de ajuste manual.

**Organização de estantes:** a funcionalidade de organização física das estantes está em
desenvolvimento. Em breve você poderá distribuir seus livros pelas prateleiras de
forma otimizada.
""")


def main() -> None:
    st.title("📚 Minha Biblioteca")
    tab_acervo, tab_estantes, tab_sobre = st.tabs(["📚 Acervo", "🗂️ Estantes", "📖 Sobre"])

    with tab_acervo:
        _render_acervo()

    with tab_estantes:
        _render_estantes()

    with tab_sobre:
        _render_sobre()
```

- [ ] **Step 7: Run all tests to confirm nothing broke**

```bash
pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 8: Commit**

```bash
git add ui/app.py
git commit -m "feat(ui): add capa_fonte badge and Sobre tab"
```

---

## Self-Review

### Spec coverage

| Spec requirement | Task |
|---|---|
| `capa_fonte` field in `CSV_HEADERS` | Task 1 |
| Compat shim for old `capas_cache.json` string format | Task 1 |
| `buscar_capa()` returns `tuple[str, str]` | Task 2 |
| Each stage tagged with correct `capa_fonte` value | Task 2 |
| Manual override returns `"manual"` | Task 2 |
| Cache miss returns `("", "")` | Task 2 |
| `worker.py` stores `capa_fonte` | Task 3 |
| `_atualizar_capas` handles tuple | Task 3 |
| Migration script (`legado` / `""`) | Task 4 |
| UI `CAPA_FONTE_CORES` + `CAPA_FONTE_LABELS` | Task 5 |
| `_badge_capa()` — silent for `legado` / `""` | Task 5 |
| Second badge in cards | Task 5 |
| `capa_fonte` in table view | Task 5 |
| `capa_fonte` in edit dialog (read-only) | Task 5 |
| "📖 Sobre" third tab | Task 5 |
| `_render_sobre()` with approved text | Task 5 |

### Placeholder scan

No TBDs, no "similar to Task N", no vague steps — checked.

### Type consistency

- `buscar_capa()` returns `tuple[str, str]` — defined Task 2, consumed Task 3
- `_buscar_capa_rede()` returns `tuple[str, str]` — defined Task 2, internal only
- `CAPA_FONTE_LABELS` — defined Task 5 Step 1, used Task 5 Steps 2 + 5
- Cache format after shim: `{"url": str, "fonte": str}` — shim Task 1, read Task 2
