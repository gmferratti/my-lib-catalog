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
