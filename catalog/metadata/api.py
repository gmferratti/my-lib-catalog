import json
import time
from datetime import datetime
from pathlib import Path

import requests

from ..config import CAPAS_CACHE_FILE, CAPAS_MANUAIS_FILE, CSV_HEADERS, GOOGLE_BOOKS_API_KEY, ISBNDB_API_KEY


def _get_json(
    url: str,
    tentativas: int = 3,
    timeout: int = 20,
    headers: dict | None = None,
) -> dict | None:
    """GET com retry em timeouts e 429. Honra Retry-After quando presente."""
    espera = 2
    for tentativa in range(1, tentativas + 1):
        try:
            r = requests.get(url, timeout=timeout, headers=headers or {})
            if r.status_code == 429:
                pausa = int(r.headers.get("Retry-After", espera))
                time.sleep(pausa)
                espera = min(espera * 2, 30)
                continue
            r.raise_for_status()
            return r.json()
        except (requests.Timeout, requests.ConnectionError):
            if tentativa == tentativas:
                raise
            time.sleep(espera)
            espera = min(espera * 2, 30)
    return None


def buscar_open_library(isbn: str) -> dict | None:
    url = f"https://openlibrary.org/search.json?isbn={isbn}&fields=title,author_name,publisher,first_publish_year,number_of_pages_median,language,subject,cover_i"
    try:
        data = _get_json(url)
    except (requests.RequestException, ValueError):
        return None
    docs = (data or {}).get("docs", [])
    if not docs:
        return None
    livro = docs[0]
    cover_i = livro.get("cover_i")
    return {
        "titulo": livro.get("title", ""),
        "autores": ", ".join(livro.get("author_name", [])),
        "editora": ", ".join(livro.get("publisher", [])[:1]),
        "ano": str(livro.get("first_publish_year", "")),
        "paginas": livro.get("number_of_pages_median", ""),
        "idioma": ", ".join(livro.get("language", [])[:1]),
        "assuntos": ", ".join(livro.get("subject", [])[:5]),
        "capa_url": f"https://covers.openlibrary.org/b/id/{cover_i}-M.jpg" if cover_i else "",
        "fonte": "openlibrary",
    }


def buscar_google_books(isbn: str) -> dict | None:
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    if GOOGLE_BOOKS_API_KEY:
        url += f"&key={GOOGLE_BOOKS_API_KEY}"
    try:
        data = _get_json(url)
    except (requests.RequestException, ValueError):
        return None
    if not data or not data.get("totalItems"):
        return None
    info = data["items"][0]["volumeInfo"]
    return {
        "titulo": info.get("title", ""),
        "autores": ", ".join(info.get("authors", [])),
        "editora": info.get("publisher", ""),
        "ano": (info.get("publishedDate") or "")[:4],
        "paginas": info.get("pageCount", ""),
        "idioma": info.get("language", ""),
        "assuntos": ", ".join(info.get("categories", [])),
        "capa_url": info.get("imageLinks", {}).get("thumbnail", ""),
        "fonte": "googlebooks",
    }


def buscar_brasil_api(isbn: str) -> dict | None:
    """Fallback para livros nacionais via BrasilAPI (agrega CBL e outras fontes BR)."""
    try:
        data = _get_json(f"https://brasilapi.com.br/api/isbn/v1/{isbn}")
    except (requests.RequestException, ValueError):
        return None
    if not data or not data.get("title"):
        return None
    return {
        "titulo": data.get("title", ""),
        "autores": ", ".join(data.get("authors") or []),
        "editora": data.get("publisher", ""),
        "ano": str(data.get("year", "")),
        "paginas": data.get("page_count", ""),
        "idioma": "pt",
        "assuntos": ", ".join((data.get("subjects") or [])[:5]),
        "capa_url": data.get("cover_url") or "",
        "fonte": "brasilapi",
    }


def buscar_isbndb(isbn: str) -> dict | None:
    """ISBNdb — cobertura ampla incluindo editoras brasileiras (chave gratuita)."""
    if not ISBNDB_API_KEY:
        return None
    try:
        data = _get_json(
            f"https://api2.isbndb.com/book/{isbn}",
            headers={"Authorization": ISBNDB_API_KEY},
        )
    except (requests.RequestException, ValueError):
        return None
    if not data:
        return None
    book = data.get("book")
    if not book or not book.get("title"):
        return None
    return {
        "titulo": book.get("title", ""),
        "autores": ", ".join(book.get("authors") or []),
        "editora": book.get("publisher", ""),
        "ano": (book.get("date_published") or "")[:4],
        "paginas": book.get("pages", ""),
        "idioma": book.get("language", ""),
        "assuntos": ", ".join((book.get("subjects") or [])[:5]),
        "capa_url": book.get("image", ""),
        "fonte": "isbndb",
    }


_capas_cache: dict | None = None


def _get_cache() -> dict:
    global _capas_cache
    if _capas_cache is None:
        try:
            _capas_cache = json.loads(Path(CAPAS_CACHE_FILE).read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            _capas_cache = {}
    return _capas_cache


def _salvar_cache() -> None:
    Path(CAPAS_CACHE_FILE).write_text(
        json.dumps(_get_cache(), indent=2, ensure_ascii=False), encoding="utf-8"
    )


def limpar_cache_capa(isbn: str) -> None:
    """Remove um ISBN do cache (ex: URL confirmada quebrada)."""
    cache = _get_cache()
    if isbn in cache:
        del cache[isbn]
        _salvar_cache()


def _carregar_capas_manuais() -> dict:
    try:
        return json.loads(Path(CAPAS_MANUAIS_FILE).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def verificar_capa(url: str) -> bool:
    """Retorna True se a URL responde HTTP 200."""
    try:
        return requests.head(url, timeout=5).status_code == 200
    except requests.RequestException:
        return False


def buscar_capa(isbn: str, titulo: str = "", autores: str = "") -> str:
    """Busca capa de alta resolução. Retorna URL validada ou '' se nada disponível.

    Misses não são cacheados — cada chamada a make capas retenta ISBNs sem capa,
    permitindo que melhorias na lógica ou novos dados nas APIs sejam aproveitados.
    """
    cache = _get_cache()
    cached = cache.get(isbn)
    if cached:                          # "" ou None → retenta; URL real → retorna
        return cached

    # Manual override — highest priority after cache
    manuais = _carregar_capas_manuais()
    if isbn in manuais:
        url = manuais[isbn]
        if url:
            cache[isbn] = url
            _salvar_cache()
        return url

    url = _buscar_capa_rede(isbn, titulo, autores)
    if url:                             # só persiste sucesso
        cache[isbn] = url
        _salvar_cache()
    return url


def _buscar_capa_rede(isbn: str, titulo: str = "", autores: str = "") -> str:
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
                return f"https://covers.openlibrary.org/b/isbn/{isbn}-{size}.jpg"
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
                return f"https://covers.openlibrary.org/b/id/{cover_i}-L.jpg"
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
                    return capa_url
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
                        return capa_url
        except requests.RequestException:
            pass

    return ""


def buscar_metadados(isbn: str) -> dict:
    """Cascata de APIs. ISBNs brasileiros (978-85/978-65) consultam BrasilAPI primeiro."""
    e_brasileiro = isbn.startswith("97885") or isbn.startswith("97865")
    if e_brasileiro:
        fontes = [buscar_brasil_api, buscar_open_library, buscar_google_books, buscar_isbndb]
    else:
        fontes = [buscar_open_library, buscar_google_books, buscar_brasil_api, buscar_isbndb]
    for buscar in fontes:
        dados = buscar(isbn)
        if dados and dados.get("titulo"):
            break
    else:
        dados = None
    if not dados:
        dados = {k: "" for k in CSV_HEADERS}
        dados["fonte"] = "nao_encontrado"
    dados["isbn"] = isbn
    dados["data_cadastro"] = datetime.now().isoformat(timespec="seconds")
    return dados
