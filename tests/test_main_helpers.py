import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import main as main_module


def _registro_completo():
    return {
        "isbn": "9781098115784",
        "titulo": "Machine Learning Design Patterns",
        "autores": "Sara Robinson",
        "editora": "O'Reilly",
        "ano": "2020",
        "paginas": "400",
        "idioma": "en",
        "assuntos": "Computers",
        "capa_url": "https://example.com/capa.jpg",
        "capa_fonte": "openlibrary_isbn",
        "fonte": "openlibrary",
        "data_cadastro": "2026-06-21T10:00:00",
        "estante": "",
        "prateleira": "",
        "etiquetas": "",
    }


def test_resumo_campos_retorna_campos_presentes():
    resultado = main_module._resumo_campos(_registro_completo())
    assert "título" in resultado
    assert "autores" in resultado
    assert "páginas" in resultado
    assert "idioma" in resultado


def test_resumo_campos_exclui_campos_de_sistema():
    resultado = main_module._resumo_campos(_registro_completo())
    assert "isbn" not in resultado
    assert "fonte" not in resultado
    assert "data_cadastro" not in resultado
    assert "capa_url" not in resultado
    assert "estante" not in resultado


def test_resumo_campos_sem_nada_retorna_nenhum():
    vazio = {k: "" for k in _registro_completo()}
    resultado = main_module._resumo_campos(vazio)
    assert resultado == "nenhum"


def test_resumo_campos_com_etiquetas():
    r = {**_registro_completo(), "etiquetas": "doutorado, lazer"}
    resultado = main_module._resumo_campos(r)
    assert "etiquetas" in resultado
