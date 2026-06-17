import pytest
import requests

import catalog.metadata.api as api_module
from catalog.metadata.api import (
    buscar_brasil_api,
    buscar_google_books,
    buscar_isbndb,
    buscar_metadados,
    buscar_open_library,
)

ISBN = "9781098115784"
ISBN_BR = "9788551012239"


def _mock_resp(mocker, payload, status=200):
    resp = mocker.Mock()
    resp.status_code = status
    resp.json.return_value = payload
    resp.raise_for_status = mocker.Mock()
    return resp


# ──────────────────────────────────────────────
# buscar_open_library
# ──────────────────────────────────────────────

def test_open_library_happy_path(mocker):
    payload = {
        "docs": [{
            "title": "Machine Learning Design Patterns",
            "author_name": ["Valliappa Lakshmanan", "Sara Robinson"],
            "publisher": ["O'Reilly"],
            "first_publish_year": 2020,
            "number_of_pages_median": 400,
            "language": ["eng"],
            "subject": ["Science", "Mathematics"],
            "cover_i": 12345,
        }]
    }
    mocker.patch("requests.get", return_value=_mock_resp(mocker, payload))
    result = buscar_open_library(ISBN)
    assert result is not None
    assert result["titulo"] == "Machine Learning Design Patterns"
    assert result["fonte"] == "openlibrary"
    assert result["autores"] == "Valliappa Lakshmanan, Sara Robinson"
    assert result["ano"] == "2020"
    assert "covers.openlibrary.org" in result["capa_url"]


def test_open_library_sem_docs(mocker):
    mocker.patch("requests.get", return_value=_mock_resp(mocker, {"docs": []}))
    assert buscar_open_library(ISBN) is None


def test_open_library_connection_error(mocker):
    mocker.patch("requests.get", side_effect=requests.ConnectionError)
    assert buscar_open_library(ISBN) is None


# ──────────────────────────────────────────────
# buscar_google_books
# ──────────────────────────────────────────────

def test_google_books_happy_path(mocker):
    payload = {
        "totalItems": 1,
        "items": [{
            "volumeInfo": {
                "title": "Machine Learning Design Patterns",
                "authors": ["Sara Robinson"],
                "publisher": "O'Reilly",
                "publishedDate": "2020-11",
                "pageCount": 400,
                "language": "en",
                "categories": ["Computers"],
                "imageLinks": {"thumbnail": "https://example.com/thumb.jpg"},
            }
        }]
    }
    mocker.patch("requests.get", return_value=_mock_resp(mocker, payload))
    result = buscar_google_books(ISBN)
    assert result is not None
    assert result["titulo"] == "Machine Learning Design Patterns"
    assert result["fonte"] == "googlebooks"
    assert result["ano"] == "2020"


def test_google_books_sem_resultados(mocker):
    mocker.patch("requests.get", return_value=_mock_resp(mocker, {"totalItems": 0}))
    assert buscar_google_books(ISBN) is None


def test_google_books_connection_error(mocker):
    mocker.patch("requests.get", side_effect=requests.ConnectionError)
    assert buscar_google_books(ISBN) is None


# ──────────────────────────────────────────────
# buscar_brasil_api
# ──────────────────────────────────────────────

def test_brasil_api_happy_path(mocker):
    payload = {
        "isbn": ISBN_BR,
        "title": "Katábasis",
        "authors": ["R.F. Kuang", "Marina Vargas"],
        "publisher": "Intrínseca",
        "year": 2025,
        "page_count": 480,
        "subjects": ["Literatura americana", "Fantasia"],
        "cover_url": None,
    }
    mocker.patch("requests.get", return_value=_mock_resp(mocker, payload))
    result = buscar_brasil_api(ISBN_BR)
    assert result is not None
    assert result["titulo"] == "Katábasis"
    assert result["autores"] == "R.F. Kuang, Marina Vargas"
    assert result["fonte"] == "brasilapi"
    assert result["ano"] == "2025"
    assert result["idioma"] == "pt"


def test_brasil_api_sem_titulo(mocker):
    mocker.patch("requests.get", return_value=_mock_resp(mocker, {"isbn": ISBN_BR}))
    assert buscar_brasil_api(ISBN_BR) is None


def test_brasil_api_connection_error(mocker):
    mocker.patch("requests.get", side_effect=requests.ConnectionError)
    assert buscar_brasil_api(ISBN_BR) is None


# ──────────────────────────────────────────────
# buscar_isbndb
# ──────────────────────────────────────────────

def test_isbndb_ignorado_sem_chave(mocker):
    mocker.patch.object(api_module, "ISBNDB_API_KEY", "")
    mock_get = mocker.patch("requests.get")
    result = buscar_isbndb(ISBN)
    assert result is None
    mock_get.assert_not_called()


def test_isbndb_happy_path(mocker):
    mocker.patch.object(api_module, "ISBNDB_API_KEY", "test-key-123")
    payload = {
        "book": {
            "title": "Machine Learning Design Patterns",
            "authors": ["Valliappa Lakshmanan"],
            "publisher": "O'Reilly",
            "date_published": "2020",
            "pages": 400,
            "language": "en",
            "subjects": ["Machine learning"],
            "image": "https://example.com/cover.jpg",
        }
    }
    mocker.patch("requests.get", return_value=_mock_resp(mocker, payload))
    result = buscar_isbndb(ISBN)
    assert result is not None
    assert result["titulo"] == "Machine Learning Design Patterns"
    assert result["fonte"] == "isbndb"


def test_isbndb_connection_error(mocker):
    mocker.patch.object(api_module, "ISBNDB_API_KEY", "test-key-123")
    mocker.patch("requests.get", side_effect=requests.ConnectionError)
    assert buscar_isbndb(ISBN) is None


# ──────────────────────────────────────────────
# buscar_metadados (orquestração)
# ──────────────────────────────────────────────

def test_cascata_para_no_primeiro_sucesso(mocker):
    sucesso = {"titulo": "Livro Teste", "fonte": "openlibrary"}
    mocker.patch.object(api_module, "buscar_open_library", return_value=sucesso)
    mock_gb = mocker.patch.object(api_module, "buscar_google_books")
    result = buscar_metadados(ISBN)
    assert result["titulo"] == "Livro Teste"
    mock_gb.assert_not_called()


def test_cascata_exaurida_retorna_nao_encontrado(mocker):
    mocker.patch.object(api_module, "buscar_open_library", return_value=None)
    mocker.patch.object(api_module, "buscar_google_books", return_value=None)
    mocker.patch.object(api_module, "buscar_brasil_api", return_value=None)
    mocker.patch.object(api_module, "buscar_isbndb", return_value=None)
    result = buscar_metadados(ISBN)
    assert result["fonte"] == "nao_encontrado"
    assert result["titulo"] == ""


def test_resultado_sempre_tem_isbn_e_data(mocker):
    mocker.patch.object(api_module, "buscar_open_library", return_value=None)
    mocker.patch.object(api_module, "buscar_google_books", return_value=None)
    mocker.patch.object(api_module, "buscar_brasil_api", return_value=None)
    mocker.patch.object(api_module, "buscar_isbndb", return_value=None)
    result = buscar_metadados(ISBN)
    assert result["isbn"] == ISBN
    assert result["data_cadastro"] != ""


def test_isbn_brasileiro_consulta_brasil_api_primeiro(mocker):
    sucesso = {"titulo": "Livro BR", "fonte": "brasilapi"}
    mock_br = mocker.patch.object(api_module, "buscar_brasil_api", return_value=sucesso)
    mock_ol = mocker.patch.object(api_module, "buscar_open_library")
    result = buscar_metadados(ISBN_BR)
    assert result["titulo"] == "Livro BR"
    mock_br.assert_called_once_with(ISBN_BR)
    mock_ol.assert_not_called()


def test_isbn_brasileiro_fallback_para_ol_quando_brasil_api_falha(mocker):
    mocker.patch.object(api_module, "buscar_brasil_api", return_value=None)
    sucesso_ol = {"titulo": "Livro via OL", "fonte": "openlibrary"}
    mocker.patch.object(api_module, "buscar_open_library", return_value=sucesso_ol)
    mocker.patch.object(api_module, "buscar_google_books", return_value=None)
    mocker.patch.object(api_module, "buscar_isbndb", return_value=None)
    result = buscar_metadados(ISBN_BR)
    assert result["titulo"] == "Livro via OL"
    assert result["fonte"] == "openlibrary"


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


def _reset_cache(mocker):
    mocker.patch.object(api_module, "_capas_cache", {})
    mocker.patch("catalog.metadata.api._salvar_cache")


def test_buscar_capa_ol_happy_path(mocker):
    _reset_cache(mocker)
    mocker.patch("requests.head", return_value=_mock_head(mocker, status=200))
    from catalog.metadata.api import buscar_capa
    url = buscar_capa(ISBN)
    assert url == f"https://covers.openlibrary.org/b/isbn/{ISBN}-L.jpg"


def _mock_get_sem_cover(mocker):
    resp = mocker.Mock()
    resp.status_code = 200
    resp.json.return_value = {"docs": []}
    resp.raise_for_status = mocker.Mock()
    return resp


def test_buscar_capa_ol_cover_id_sucesso(mocker):
    _reset_cache(mocker)
    ol_isbn_resp = _mock_head(mocker, status=404)
    ol_id_head = _mock_head(mocker, status=200)

    ol_search_resp = mocker.Mock()
    ol_search_resp.status_code = 200
    ol_search_resp.json.return_value = {"docs": [{"cover_i": 99999}]}
    ol_search_resp.raise_for_status = mocker.Mock()

    # OL-L 404, OL-M 404, cover_i HEAD 200
    mocker.patch("requests.head", side_effect=[ol_isbn_resp, ol_isbn_resp, ol_id_head])
    mocker.patch("requests.get", return_value=ol_search_resp)

    from catalog.metadata.api import buscar_capa
    url = buscar_capa(ISBN)
    assert "covers.openlibrary.org/b/id/99999" in url
    assert url.endswith("-L.jpg")


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

    # OL-L 404, OL-M 404, GB HEAD ok
    mocker.patch("requests.head", side_effect=[ol_resp, ol_resp, gb_head])
    # OL cover_i search (sem resultado), depois GB API
    mocker.patch("requests.get", side_effect=[_mock_get_sem_cover(mocker), gb_resp])

    from catalog.metadata.api import buscar_capa
    url = buscar_capa(ISBN)
    assert "books.google.com" in url
    assert "vol123" in url


def test_buscar_capa_sem_resultado(mocker):
    _reset_cache(mocker)
    mocker.patch("requests.head", return_value=_mock_head(mocker, status=404))
    gb_no_results = mocker.Mock()
    gb_no_results.status_code = 200
    gb_no_results.json.return_value = {"totalItems": 0}
    gb_no_results.raise_for_status = mocker.Mock()
    mocker.patch("requests.get", side_effect=[_mock_get_sem_cover(mocker), gb_no_results])
    from catalog.metadata.api import buscar_capa
    assert buscar_capa(ISBN) == ""


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

    # OL-L 404, OL-M 404, GB HEAD placeholder (≤5000 bytes)
    mocker.patch("requests.head", side_effect=[ol_resp, ol_resp, gb_head])
    mocker.patch("requests.get", side_effect=[_mock_get_sem_cover(mocker), gb_resp])

    from catalog.metadata.api import buscar_capa
    assert buscar_capa(ISBN) == ""


def test_buscar_capa_erro_de_rede_nao_lanca(mocker):
    _reset_cache(mocker)
    mocker.patch("requests.head", side_effect=requests.ConnectionError)
    mocker.patch("requests.get", side_effect=requests.ConnectionError)
    from catalog.metadata.api import buscar_capa
    assert buscar_capa(ISBN) == ""


def test_buscar_capa_retorna_cache_sem_requisicao(mocker):
    mocker.patch.object(api_module, "_capas_cache", {ISBN: "https://cached.example.com/capa.jpg"})
    mocker.patch("catalog.metadata.api._salvar_cache")
    mock_head = mocker.patch("requests.head")
    mock_get = mocker.patch("requests.get")

    from catalog.metadata.api import buscar_capa
    url = buscar_capa(ISBN)
    assert url == "https://cached.example.com/capa.jpg"
    mock_head.assert_not_called()
    mock_get.assert_not_called()
