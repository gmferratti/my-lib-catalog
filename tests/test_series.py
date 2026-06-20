import pytest
from catalog.series import compor_titulo, detectar_serie


# --- detectar_serie ---

def test_detectar_vol_numerico_antes_subtitulo():
    r = detectar_serie("MIL PLATOS - VOL. 4 CAPITALISMO E ESQUIZOFRENIA")
    assert r == {"serie": "MIL PLATOS", "volume": 4, "subtitulo": "CAPITALISMO E ESQUIZOFRENIA"}


def test_detectar_v_ponto_ao_final():
    r = detectar_serie("MIL PLATOS - CAPITALISMO E ESQUIZOFRENIA / V. 03")
    assert r == {"serie": "MIL PLATOS", "volume": 3, "subtitulo": "CAPITALISMO E ESQUIZOFRENIA"}


def test_detectar_vol_com_subtitulo_separado_por_traco():
    r = detectar_serie("MIL PLATOS - VOL. 05 - CAPITALISMO E ESQUIZOFRENIA")
    assert r == {"serie": "MIL PLATOS", "volume": 5, "subtitulo": "CAPITALISMO E ESQUIZOFRENIA"}


def test_detectar_romano_sem_subtitulo():
    r = detectar_serie("Sociologia geral Vol.I")
    assert r == {"serie": "Sociologia geral", "volume": 1, "subtitulo": ""}


def test_detectar_romano_com_subtitulo_dois_pontos():
    r = detectar_serie("Sociologia geral - Vol. 2: Habitus e Campo")
    assert r == {"serie": "Sociologia geral", "volume": 2, "subtitulo": "Habitus e Campo"}


def test_detectar_volume_por_extenso():
    r = detectar_serie("Python Fluente, 2ª edição, volume 2 versao standard")
    assert r == {"serie": "Python Fluente, 2ª edição", "volume": 2, "subtitulo": "versao standard"}


def test_detectar_retorna_none_livro_normal():
    assert detectar_serie("Dom Casmurro") is None


def test_detectar_retorna_none_sem_numero_de_volume():
    assert detectar_serie("O Senhor dos Anéis") is None


def test_detectar_retorna_none_titulo_vazio():
    assert detectar_serie("") is None


# --- compor_titulo ---

def test_compor_com_subtitulo():
    assert compor_titulo("Mil Platôs", 4, "Capitalismo e Esquizofrenia") == \
        "Mil Platôs — Vol. 4: Capitalismo e Esquizofrenia"


def test_compor_sem_subtitulo():
    assert compor_titulo("Sociologia Geral", 1) == "Sociologia Geral — Vol. 1"


def test_compor_subtitulo_vazio():
    assert compor_titulo("Python Fluente, 2ª edição", 2, "") == \
        "Python Fluente, 2ª edição — Vol. 2"


# --- integração com salvar() ---

from catalog.storage import carregar_todos_registros, salvar


def test_salvar_normaliza_titulo_de_serie(tmp_data_dir):
    registro = {
        "isbn": "9788573260502",
        "titulo": "MIL PLATOS - VOL. 4 CAPITALISMO E ESQUIZOFRENIA",
        "autores": "Gilles Deleuze, Félix Guattari",
        "editora": "Editora 34",
        "ano": "2012",
        "paginas": "100",
        "idioma": "pt",
        "assuntos": "",
        "capa_url": "",
        "capa_fonte": "",
        "fonte": "manual",
        "data_cadastro": "2026-06-20T10:00:00",
        "estante": "",
        "prateleira": "",
        "etiquetas": "",
    }
    salvar(registro)
    registros = carregar_todos_registros()
    assert registros[0]["titulo"] == "MIL PLATOS — Vol. 4: CAPITALISMO E ESQUIZOFRENIA"


def test_salvar_nao_altera_titulo_sem_padrao_de_serie(tmp_data_dir):
    registro = {
        "isbn": "9781098115784",
        "titulo": "Machine Learning Design Patterns",
        "autores": "",
        "editora": "",
        "ano": "",
        "paginas": "",
        "idioma": "",
        "assuntos": "",
        "capa_url": "",
        "capa_fonte": "",
        "fonte": "manual",
        "data_cadastro": "2026-06-20T10:00:00",
        "estante": "",
        "prateleira": "",
        "etiquetas": "",
    }
    salvar(registro)
    registros = carregar_todos_registros()
    assert registros[0]["titulo"] == "Machine Learning Design Patterns"
