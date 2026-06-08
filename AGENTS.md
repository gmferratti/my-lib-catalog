# my-lib-catalog

## Quick start

```bash
pip install -r requirements.txt   # only dep: requests>=2.31.0
python main.py                     # run the CLI app
```

## Repo overview

Plain Python 3.10+ project (uses `str | None` syntax). Not pip-installable. Single entrypoint: `main.py`.

| Path | Purpose |
|------|---------|
| `catalog/` | App package: ISBN validation, API clients, persistence, worker |
| `main.py` | CLI entrypoint (event loop, user input) |
| `tests/` | Empty — no test framework configured yet |

## Architecture

- **Async via `threading` + `queue.Queue`**, not asyncio. Worker daemon thread processes ISBNs in background while main thread accepts input.
- **Thread-safe file I/O** — `threading.Lock()` guards all CSV/JSONL writes in `catalog/persistence.py`.
- **API fallback chain** in `catalog/api.py`: Open Library → Google Books → Mercado Livre → ISBNdb. Each step tries only if previous failed.
- **Pending ISBNs persist** between sessions in `tmp/pendentes.txt` (`tmp/*` is gitignored). Re-enqueued on startup.
- **Retry with exponential backoff**: `_get_json()` retries up to 3 times (2s → 4s → 8s, capped 30s), respects `Retry-After` on 429.

## Config

`catalog/config.py` — file paths, CSV headers, `ISBNDB_API_KEY` (set for ISBNdb; free at isbndb.com).

## Data files

`data/biblioteca.csv` and `data/biblioteca.jsonl` are **committed to git** (append mode). Outputs are always written to both formats simultaneously.

## Outdated README

`README.md` references `biblioteca_isbn.py` as the entrypoint — that file does not exist. The real entrypoint is `main.py`.

## Commands (runtime)

| Input | Action |
|-------|--------|
| Scan/type ISBN | Normalizes and enqueues for async lookup |
| `fila` | Show pending queue size |
| `reprocessar` | Retry failed lookups (only when queue empty) |
| `sair` / `exit` / `quit` | Drain queue, save pending, exit |

## No tooling configured

No linter, formatter, type checker, or test runner configured (though `.gitignore` has entries for `pytest`, `ruff`, `mypy` caches — suggests they may be added later).
