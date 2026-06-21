import pytest
import requests
import json

import catalog.metadata.api as api_module
from catalog.metadata.api import (
    buscar_brasil_api,
    buscar_google_books,
    buscar_isbndb,
    buscar_metadados,
    buscar_open_library,
    buscar_open_library_edicao,
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
    sucesso = {"titulo": "Livro Teste", "fonte": "openlibrary", "ano": "2020"}
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
    mocker.patch.object(api_module, "buscar_open_library_edicao", return_value=None)
    result = buscar_metadados(ISBN)
    assert result["fonte"] == "nao_encontrado"
    assert result["titulo"] == ""


def test_resultado_sempre_tem_isbn_e_data(mocker):
    mocker.patch.object(api_module, "buscar_open_library", return_value=None)
    mocker.patch.object(api_module, "buscar_google_books", return_value=None)
    mocker.patch.object(api_module, "buscar_brasil_api", return_value=None)
    mocker.patch.object(api_module, "buscar_isbndb", return_value=None)
    mocker.patch.object(api_module, "buscar_open_library_edicao", return_value=None)
    result = buscar_metadados(ISBN)
    assert result["isbn"] == ISBN
    assert result["data_cadastro"] != ""


def test_isbn_brasileiro_consulta_brasil_api_primeiro(mocker):
    sucesso = {"titulo": "Livro BR", "fonte": "brasilapi", "ano": "2025"}
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
    mocker.patch.object(api_module, "buscar_open_library_edicao", return_value=None)
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
    mocker.patch.object(api_module, "_carregar_capas_manuais", return_value={})


def test_buscar_capa_ol_happy_path(mocker):
    _reset_cache(mocker)
    mocker.patch("requests.head", return_value=_mock_head(mocker, status=200))
    from catalog.metadata.api import buscar_capa
    url, fonte = buscar_capa(ISBN)
    assert url == f"https://covers.openlibrary.org/b/isbn/{ISBN}-L.jpg"
    assert fonte == "openlibrary_isbn"


def _mock_get_sem_cover(mocker):
    resp = mocker.Mock()
    resp.status_code = 200
    resp.json.return_value = {"docs": []}
    resp.raise_for_status = mocker.Mock()
    return resp


def _mock_ddg_sem_vqd(mocker):
    """Stub para o primeiro GET do DuckDuckGo (Stage 6) que não contém token vqd.

    Faz Stage 6 retornar imediatamente sem disparar mais requisições.
    Necessário nos testes que passam side_effect com lista finita para requests.get
    e que não querem testar Stage 6.
    """
    resp = mocker.Mock()
    resp.status_code = 200
    resp.text = "sem token aqui"
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

    mocker.patch("requests.head", side_effect=[ol_isbn_resp, ol_isbn_resp, ol_id_head])
    mocker.patch("requests.get", return_value=ol_search_resp)

    from catalog.metadata.api import buscar_capa
    url, fonte = buscar_capa(ISBN)
    assert "covers.openlibrary.org/b/id/99999" in url
    assert url.endswith("-L.jpg")
    assert fonte == "openlibrary_cover_i"


def test_buscar_capa_ol_cover_id_usa_allow_redirects(mocker):
    """Regression: Stage 2 HEAD request must pass allow_redirects=True.

    OL cover-by-id URLs sometimes return 302. Without allow_redirects=True,
    requests.head() would NOT follow the redirect and status_code would be 302,
    causing the cover to be silently missed. With allow_redirects=True, the
    library follows the redirect internally and the resolved response has
    status_code=200, so the cover URL is returned correctly.

    We verify that requests.head is called with allow_redirects=True.
    """
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
    url, fonte = buscar_capa(ISBN)
    assert "books.google.com" in url
    assert "vol123" in url
    assert fonte == "googlebooks_isbn"


def test_buscar_capa_sem_resultado(mocker):
    _reset_cache(mocker)
    mocker.patch("requests.head", return_value=_mock_head(mocker, status=404))
    gb_no_results = mocker.Mock()
    gb_no_results.status_code = 200
    gb_no_results.json.return_value = {"totalItems": 0}
    gb_no_results.raise_for_status = mocker.Mock()
    # Stage 6 (DDG) recebe um stub sem vqd → retorna "" sem disparar mais GETs
    mocker.patch("requests.get", side_effect=[_mock_get_sem_cover(mocker), gb_no_results, _mock_ddg_sem_vqd(mocker)])
    from catalog.metadata.api import buscar_capa
    url, fonte = buscar_capa(ISBN)
    assert url == ""
    assert fonte == ""


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
    # Stage 6 (DDG) recebe um stub sem vqd → retorna "" sem disparar mais GETs
    mocker.patch("requests.get", side_effect=[_mock_get_sem_cover(mocker), gb_resp, _mock_ddg_sem_vqd(mocker)])

    from catalog.metadata.api import buscar_capa
    url, fonte = buscar_capa(ISBN)
    assert url == ""
    assert fonte == ""


def test_buscar_capa_erro_de_rede_nao_lanca(mocker):
    _reset_cache(mocker)
    mocker.patch("requests.head", side_effect=requests.ConnectionError)
    mocker.patch("requests.get", side_effect=requests.ConnectionError)
    from catalog.metadata.api import buscar_capa
    url, fonte = buscar_capa(ISBN)
    assert url == ""
    assert fonte == ""


def test_buscar_capa_miss_nao_cacheia(mocker):
    _reset_cache(mocker)
    mocker.patch("requests.head", return_value=_mock_head(mocker, status=404))
    # Stage 6 (DDG) recebe um stub sem vqd → retorna "" sem disparar mais GETs
    mocker.patch("requests.get", side_effect=[_mock_get_sem_cover(mocker), _mock_get_sem_cover(mocker), _mock_ddg_sem_vqd(mocker)])
    from catalog.metadata.api import buscar_capa
    url, fonte = buscar_capa(ISBN)
    assert url == ""
    assert fonte == ""
    api_module._salvar_cache.assert_not_called()


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


def test_carregar_capas_manuais_arquivo_ausente(mocker):
    mocker.patch.object(api_module, "_capas_manuais", None)  # resetar global para exercitar o branch
    mocker.patch.object(api_module, "CAPAS_MANUAIS_FILE", "/tmp/nao_existe_jamais_xyz.json")
    from catalog.metadata.api import _carregar_capas_manuais
    assert _carregar_capas_manuais() == {}


def test_buscar_capa_override_vazio_suprime_rede(mocker):
    """ISBN com '' em capas_manuais.json deve retornar '' sem chamar a rede."""
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


# ──────────────────────────────────────────────
# _capa_ol_titulo_autor (Stage 5)
# ──────────────────────────────────────────────

def test_capa_ol_titulo_autor_happy_path(mocker):
    _reset_cache(mocker)
    ol_404 = _mock_head(mocker, status=404)
    ol_titulo_head = _mock_head(mocker, status=200)
    # Stage 1: OL-L 404, OL-M 404; Stage 2: sem docs → sem HEAD; Stage 5: HEAD 200
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
    # GET order: OL cover_i (empty), GB ISBN (0), GB título (0), OL título+autor (hit)
    mocker.patch("requests.get", side_effect=[ol_cover_i_vazio, gb_sem_resultado, gb_sem_resultado, ol_titulo_resp])

    from catalog.metadata.api import buscar_capa
    url, fonte = buscar_capa(ISBN, titulo="Mefisto", autores="Klaus Mann")
    assert "covers.openlibrary.org/b/id/44444" in url
    assert fonte == "openlibrary_titulo"


def test_capa_ol_titulo_autor_sem_resultados(mocker):
    from catalog.metadata.api import _capa_ol_titulo_autor
    resp = mocker.Mock()
    resp.status_code = 200
    resp.json.return_value = {"docs": []}
    resp.raise_for_status = mocker.Mock()
    mocker.patch("requests.get", return_value=resp)
    assert _capa_ol_titulo_autor("Livro Inexistente Xyz", "") == ""


def test_capa_ol_titulo_autor_connection_error(mocker):
    from catalog.metadata.api import _capa_ol_titulo_autor
    mocker.patch("requests.get", side_effect=requests.ConnectionError)
    assert _capa_ol_titulo_autor("Qualquer Livro", "Qualquer Autor") == ""


def test_capa_ol_titulo_autor_cover_i_head_nao_200(mocker):
    """cover_i encontrado mas HEAD retorna não-200 → continua para próximo doc e retorna ''."""
    from catalog.metadata.api import _capa_ol_titulo_autor
    resp = mocker.Mock()
    resp.status_code = 200
    resp.json.return_value = {"docs": [{"cover_i": 11111}, {"cover_i": 22222}]}
    resp.raise_for_status = mocker.Mock()
    mocker.patch("requests.get", return_value=resp)
    mocker.patch("requests.head", return_value=_mock_head(mocker, status=404))
    assert _capa_ol_titulo_autor("Livro Raro", "Autor") == ""


# ──────────────────────────────────────────────
# _capa_duckduckgo (Stage 6)
# ──────────────────────────────────────────────

def test_capa_duckduckgo_happy_path(mocker):
    from catalog.metadata.api import _capa_duckduckgo

    vqd_resp = mocker.Mock()
    vqd_resp.status_code = 200
    vqd_resp.text = 'vqd="4-abc123xyz"'
    vqd_resp.raise_for_status = mocker.Mock()
    vqd_resp.json.return_value = {}  # não usado, mas evita AttributeError

    images_resp = mocker.Mock()
    images_resp.status_code = 200
    images_resp.json.return_value = {
        "results": [{"image": "https://example.com/capa.jpg"}]
    }
    images_resp.raise_for_status = mocker.Mock()

    head_resp = _mock_head(mocker, status=200)
    head_resp.headers = {"Content-Type": "image/jpeg", "Content-Length": "60000"}

    mocker.patch("requests.get", side_effect=[vqd_resp, images_resp])
    mocker.patch("requests.head", return_value=head_resp)

    url = _capa_duckduckgo("9786555322569", "Harry Potter", "J.K. Rowling")
    assert url == "https://example.com/capa.jpg"


def test_capa_duckduckgo_sem_vqd(mocker):
    from catalog.metadata.api import _capa_duckduckgo
    resp = mocker.Mock()
    resp.status_code = 200
    resp.text = "sem token aqui"
    resp.raise_for_status = mocker.Mock()
    mocker.patch("requests.get", return_value=resp)
    assert _capa_duckduckgo("9786555322569", "Livro", "Autor") == ""


def test_capa_duckduckgo_rejeita_nao_imagem(mocker):
    from catalog.metadata.api import _capa_duckduckgo

    vqd_resp = mocker.Mock()
    vqd_resp.status_code = 200
    vqd_resp.text = 'vqd="4-xyz"'
    vqd_resp.raise_for_status = mocker.Mock()

    images_resp = mocker.Mock()
    images_resp.status_code = 200
    images_resp.json.return_value = {"results": [{"image": "https://bad.example.com/page"}]}
    images_resp.raise_for_status = mocker.Mock()

    head_resp = mocker.Mock()
    head_resp.status_code = 200
    head_resp.headers = {"Content-Type": "text/html", "Content-Length": "50000"}

    mocker.patch("requests.get", side_effect=[vqd_resp, images_resp])
    mocker.patch("requests.head", return_value=head_resp)

    assert _capa_duckduckgo("9786555322569", "Livro", "Autor") == ""


def test_capa_duckduckgo_connection_error(mocker):
    from catalog.metadata.api import _capa_duckduckgo
    mocker.patch("requests.get", side_effect=requests.ConnectionError)
    assert _capa_duckduckgo("9786555322569", "Livro", "Autor") == ""


def test_capa_duckduckgo_aceita_sem_content_length(mocker):
    """CDNs com chunked transfer não enviam Content-Length; deve aceitar a imagem."""
    from catalog.metadata.api import _capa_duckduckgo

    vqd_resp = mocker.Mock()
    vqd_resp.status_code = 200
    vqd_resp.text = 'vqd="4-xyz"'
    vqd_resp.raise_for_status = mocker.Mock()

    images_resp = mocker.Mock()
    images_resp.status_code = 200
    images_resp.json.return_value = {"results": [{"image": "https://cdn.exemplo.com/capa.jpg"}]}
    images_resp.raise_for_status = mocker.Mock()

    head_resp = mocker.Mock()
    head_resp.status_code = 200
    head_resp.headers = {"Content-Type": "image/jpeg"}  # sem Content-Length

    mocker.patch("requests.get", side_effect=[vqd_resp, images_resp])
    mocker.patch("requests.head", return_value=head_resp)

    url = _capa_duckduckgo("9786555322569", "Harry Potter", "J.K. Rowling")
    assert url == "https://cdn.exemplo.com/capa.jpg"


# ──────────────────────────────────────────────
# _capa_google_cse (Stage 7)
# ──────────────────────────────────────────────

def test_capa_google_cse_ignorado_sem_chave(mocker):
    mocker.patch.object(api_module, "GOOGLE_CUSTOM_SEARCH_KEY", "")
    mocker.patch.object(api_module, "GOOGLE_CUSTOM_SEARCH_CX", "fake-cx")
    mock_get = mocker.patch("requests.get")
    from catalog.metadata.api import _capa_google_cse
    assert _capa_google_cse(ISBN) == ""
    mock_get.assert_not_called()


def test_capa_google_cse_happy_path(mocker):
    mocker.patch.object(api_module, "GOOGLE_CUSTOM_SEARCH_KEY", "fake-key")
    mocker.patch.object(api_module, "GOOGLE_CUSTOM_SEARCH_CX", "fake-cx")
    payload = {"items": [{"link": "https://example.com/capa.jpg"}]}
    mocker.patch("requests.get", return_value=_mock_resp(mocker, payload))
    head_resp = mocker.Mock()
    head_resp.status_code = 200
    head_resp.headers = {"Content-Type": "image/jpeg", "Content-Length": "50000"}
    mocker.patch("requests.head", return_value=head_resp)
    from catalog.metadata.api import _capa_google_cse
    url = _capa_google_cse(ISBN, "Livro Teste", "Autor")
    assert url == "https://example.com/capa.jpg"


def test_capa_google_cse_connection_error(mocker):
    mocker.patch.object(api_module, "GOOGLE_CUSTOM_SEARCH_KEY", "fake-key")
    mocker.patch.object(api_module, "GOOGLE_CUSTOM_SEARCH_CX", "fake-cx")
    mocker.patch("requests.get", side_effect=requests.ConnectionError)
    from catalog.metadata.api import _capa_google_cse
    assert _capa_google_cse(ISBN) == ""


# ──────────────────────────────────────────────
# buscar_open_library_edicao
# ──────────────────────────────────────────────

def test_buscar_open_library_edicao_happy_path(mocker):
    payload = {
        "title": "Harry Potter e o Prisioneiro de Azkaban",
        "publishers": ["Rocco"],
        "publish_date": "2015",
        "number_of_pages": 448,
        "languages": [{"key": "/languages/por"}],
        "covers": [12345],
    }
    mocker.patch("requests.get", return_value=_mock_resp(mocker, payload))
    result = buscar_open_library_edicao(ISBN)
    assert result is not None
    assert result["titulo"] == "Harry Potter e o Prisioneiro de Azkaban"
    assert result["ano"] == "2015"
    assert result["editora"] == "Rocco"
    assert result["idioma"] == "por"
    assert result["fonte"] == "openlibrary_edicao"
    assert "covers.openlibrary.org/b/id/12345" in result["capa_url"]


def test_buscar_open_library_edicao_publish_date_verbose(mocker):
    payload = {"title": "Duna", "publish_date": "January 2018"}
    mocker.patch("requests.get", return_value=_mock_resp(mocker, payload))
    result = buscar_open_library_edicao(ISBN)
    assert result is not None
    assert result["ano"] == "2018"


def test_buscar_open_library_edicao_sem_titulo(mocker):
    mocker.patch("requests.get", return_value=_mock_resp(mocker, {"publishers": ["Rocco"]}))
    assert buscar_open_library_edicao(ISBN) is None


def test_buscar_open_library_edicao_connection_error(mocker):
    mocker.patch("requests.get", side_effect=requests.ConnectionError)
    assert buscar_open_library_edicao(ISBN) is None


# ──────────────────────────────────────────────
# buscar_metadados — suplemento de ano
# ──────────────────────────────────────────────

def test_cascata_suplementa_ano_de_fonte_secundaria(mocker):
    """Quando BrasilAPI tem título mas sem ano, o ano vem do Google Books."""
    br_sem_ano = {"titulo": "Duna", "autores": "Frank Herbert", "fonte": "brasilapi", "ano": ""}
    gb_com_ano = {"titulo": "Duna", "autores": "Frank Herbert", "fonte": "googlebooks", "ano": "2019"}
    mocker.patch.object(api_module, "buscar_brasil_api", return_value=br_sem_ano)
    mocker.patch.object(api_module, "buscar_open_library", return_value=None)
    mocker.patch.object(api_module, "buscar_google_books", return_value=gb_com_ano)
    mocker.patch.object(api_module, "buscar_isbndb", return_value=None)
    mocker.patch.object(api_module, "buscar_open_library_edicao", return_value=None)
    result = buscar_metadados(ISBN_BR)
    assert result["titulo"] == "Duna"
    assert result["fonte"] == "brasilapi"
    assert result["autores"] == "Frank Herbert"
    assert result["ano"] == "2019"


def test_cascata_preserva_dados_da_fonte_principal_ao_suplementar_ano(mocker):
    """Dados completos do BrasilAPI (autores, editora etc.) são preservados ao suplementar o ano."""
    br_sem_ano = {
        "titulo": "Código Limpo", "autores": "Robert C. Martin",
        "editora": "Alta Books", "paginas": 464,
        "fonte": "brasilapi", "ano": "",
    }
    ol_edicao_com_ano = {
        "titulo": "Clean Code", "autores": "", "editora": "OL Publisher",
        "fonte": "openlibrary_edicao", "ano": "2011",
    }
    mocker.patch.object(api_module, "buscar_brasil_api", return_value=br_sem_ano)
    mocker.patch.object(api_module, "buscar_open_library", return_value=None)
    mocker.patch.object(api_module, "buscar_google_books", return_value=None)
    mocker.patch.object(api_module, "buscar_isbndb", return_value=None)
    mocker.patch.object(api_module, "buscar_open_library_edicao", return_value=ol_edicao_com_ano)
    result = buscar_metadados(ISBN_BR)
    assert result["fonte"] == "brasilapi"
    assert result["autores"] == "Robert C. Martin"
    assert result["editora"] == "Alta Books"
    assert result["ano"] == "2011"


import logging


def test_buscar_metadados_loga_info_fonte_encontrada(mocker, caplog):
    payload = {
        "titulo": "Machine Learning Design Patterns",
        "autores": "Sara Robinson",
        "editora": "O'Reilly",
        "ano": "2020",
        "paginas": 400,
        "idioma": "en",
        "assuntos": "Computers",
        "capa_url": "",
        "fonte": "openlibrary",
    }
    mocker.patch("catalog.metadata.api.buscar_brasil_api", return_value=None)
    mocker.patch("catalog.metadata.api.buscar_open_library", return_value=payload)
    mocker.patch("catalog.metadata.api.buscar_google_books", return_value=None)
    mocker.patch("catalog.metadata.api.buscar_isbndb", return_value=None)
    mocker.patch("catalog.metadata.api.buscar_open_library_edicao", return_value=None)

    with caplog.at_level(logging.INFO, logger="catalog.metadata.api"):
        buscar_metadados(ISBN)

    assert any("metadados obtidos via openlibrary" in r.message for r in caplog.records)


def test_buscar_metadados_loga_warning_nao_encontrado(mocker, caplog):
    for fn in ["buscar_brasil_api", "buscar_open_library", "buscar_google_books",
               "buscar_isbndb", "buscar_open_library_edicao"]:
        mocker.patch(f"catalog.metadata.api.{fn}", return_value=None)

    with caplog.at_level(logging.WARNING, logger="catalog.metadata.api"):
        buscar_metadados(ISBN)

    assert any("nenhuma fonte retornou metadados" in r.message for r in caplog.records)
