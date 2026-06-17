import time
from datetime import datetime

import requests

from ..config import CSV_HEADERS, GOOGLE_BOOKS_API_KEY, ISBNDB_API_KEY


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


def buscar_capa(isbn: str) -> str:
    """Busca capa de alta resolução. Retorna URL validada ou '' se nada disponível."""
    # Estágio 1 — Open Library por ISBN (Large depois Medium)
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
            )
            if r.status_code == 200:
                return f"https://covers.openlibrary.org/b/id/{cover_i}-L.jpg"
    except requests.RequestException:
        pass

    # Estágio 3 — Google Books zoom=0
    try:
        url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
        if GOOGLE_BOOKS_API_KEY:
            url += f"&key={GOOGLE_BOOKS_API_KEY}"
        data = _get_json(url, tentativas=1, timeout=5)
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
