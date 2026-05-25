import time
from datetime import datetime

import requests

from .config import CSV_HEADERS


def _get_json(url: str, tentativas: int = 3, timeout: int = 20) -> dict | None:
    """GET com retry em timeouts e 429. Honra Retry-After quando presente."""
    espera = 2
    for tentativa in range(1, tentativas + 1):
        try:
            r = requests.get(url, timeout=timeout)
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
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}&format=json&jscmd=data"
    try:
        data = _get_json(url)
    except (requests.RequestException, ValueError):
        return None
    if not data:
        return None
    chave = f"ISBN:{isbn}"
    if chave not in data:
        return None
    livro = data[chave]
    return {
        "titulo": livro.get("title", ""),
        "autores": ", ".join(a.get("name", "") for a in livro.get("authors", [])),
        "editora": ", ".join(p.get("name", "") for p in livro.get("publishers", [])),
        "ano": (livro.get("publish_date") or "")[-4:],
        "paginas": livro.get("number_of_pages", ""),
        "idioma": "",
        "assuntos": ", ".join(s.get("name", "") for s in livro.get("subjects", [])[:5]),
        "capa_url": livro.get("cover", {}).get("medium", ""),
        "fonte": "openlibrary",
    }


def buscar_google_books(isbn: str) -> dict | None:
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
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


def buscar_mercado_livre(isbn: str) -> dict | None:
    """Fallback para livros nacionais não indexados em Open Library/Google Books."""
    url = f"https://api.mercadolibre.com/sites/MLB/search?q={isbn}"
    try:
        data = _get_json(url)
    except (requests.RequestException, ValueError):
        return None
    if not data or not data.get("results"):
        return None
    item = data["results"][0]
    titulo = item.get("title", "")
    if not titulo:
        return None
    attrs = {a["id"]: a.get("value_name", "") for a in item.get("attributes", [])}
    return {
        "titulo": titulo,
        "autores": attrs.get("AUTHOR", ""),
        "editora": attrs.get("PUBLISHER", ""),
        "ano": attrs.get("PUBLICATION_YEAR", ""),
        "paginas": attrs.get("NUMBER_OF_PAGES", ""),
        "idioma": attrs.get("LANGUAGE", "pt"),
        "assuntos": "",
        "capa_url": item.get("thumbnail", ""),
        "fonte": "mercadolivre",
    }


def buscar_metadados(isbn: str) -> dict:
    """Open Library → Google Books → Mercado Livre como fallback."""
    dados = buscar_open_library(isbn)
    if not dados or not dados.get("titulo"):
        dados_gb = buscar_google_books(isbn)
        if dados_gb and dados_gb.get("titulo"):
            dados = dados_gb
        else:
            dados_ml = buscar_mercado_livre(isbn)
            if dados_ml:
                dados = dados_ml
    if not dados:
        dados = {k: "" for k in CSV_HEADERS}
        dados["fonte"] = "nao_encontrado"
    dados["isbn"] = isbn
    dados["data_cadastro"] = datetime.now().isoformat(timespec="seconds")
    return dados
