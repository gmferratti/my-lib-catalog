# my-lib-catalog

## Quick start

```bash
pip install requests
python scripts/main.py
```

## Repo overview

Plain Python 3.12+ project. Uses `src/` layout.

| Path | Purpose |
|------|---------|
| `src/catalog/` | App package: ISBN validation, API clients, persistence, worker |
| `scripts/main.py` | CLI entrypoint (event loop, user input) |
| `tests/` | Test suite |
| `data/` | Committed data files (CSV + JSONL, append mode) |
| `docs/` | Documentation |
| `notebooks/` | Jupyter notebooks / exploration |

## Architecture

- **Async via `threading` + `queue.Queue`**, not asyncio. Worker daemon thread processes ISBNs in background while main thread accepts input.
- **Thread-safe file I/O** — `threading.Lock()` guards all CSV/JSONL writes in `catalog/persistence.py`.
- **API fallback chain** in `catalog/api.py`: Open Library → Google Books → Mercado Livre → ISBNdb. Each step tries only if previous failed.
- **Pending ISBNs persist** between sessions in `tmp/pendentes.txt` (`tmp/*` is gitignored). Re-enqueued on startup.
- **Retry with exponential backoff**: `_get_json()` retries up to 3 times (2s → 4s → 8s, capped 30s), respects `Retry-After` on 429.

## Config

`src/catalog/config.py` — file paths, CSV headers, `ISBNDB_API_KEY` (set for ISBNdb; free at isbndb.com).

## Data files

`data/biblioteca.csv` and `data/biblioteca.jsonl` are **committed to git** (append mode). Outputs are always written to both formats simultaneously.

## Commands (runtime)

| Input | Action |
|-------|--------|
| Scan/type ISBN | Normalizes and enqueues for async lookup |
| `fila` | Show pending queue size |
| `reprocessar` | Retry failed lookups (only when queue empty) |
| `sair` / `exit` / `quit` | Drain queue, save pending, exit |

## Tooling

No linter, formatter, or type checker configured yet.
