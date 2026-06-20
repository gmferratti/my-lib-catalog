# tests/test_ui_utils.py
from pathlib import Path
import json
import pytest


def test_ler_tema_default_quando_sem_arquivo(tmp_path, monkeypatch):
    """Sem arquivo de prefs, retorna 'escuro'."""
    import ui.utils as utils
    monkeypatch.setattr(utils, "_PREFS_PATH", tmp_path / "ui_prefs.json")
    assert utils._ler_tema() == "escuro"


def test_ler_tema_retorna_valor_salvo(tmp_path, monkeypatch):
    import ui.utils as utils
    path = tmp_path / "ui_prefs.json"
    path.write_text(json.dumps({"tema": "claro"}), encoding="utf-8")
    monkeypatch.setattr(utils, "_PREFS_PATH", path)
    assert utils._ler_tema() == "claro"


def test_ler_tema_json_invalido_retorna_default(tmp_path, monkeypatch):
    import ui.utils as utils
    path = tmp_path / "ui_prefs.json"
    path.write_text("NOT JSON", encoding="utf-8")
    monkeypatch.setattr(utils, "_PREFS_PATH", path)
    assert utils._ler_tema() == "escuro"


def test_salvar_tema_cria_arquivo(tmp_path, monkeypatch):
    import ui.utils as utils
    path = tmp_path / "ui_prefs.json"
    monkeypatch.setattr(utils, "_PREFS_PATH", path)
    utils._salvar_tema("claro")
    assert json.loads(path.read_text()) == {"tema": "claro"}


def test_salvar_tema_sobrescreve_valor_anterior(tmp_path, monkeypatch):
    import ui.utils as utils
    path = tmp_path / "ui_prefs.json"
    path.write_text(json.dumps({"tema": "claro"}), encoding="utf-8")
    monkeypatch.setattr(utils, "_PREFS_PATH", path)
    utils._salvar_tema("escuro")
    assert json.loads(path.read_text()) == {"tema": "escuro"}


def test_badge_etiqueta_usa_classe_css():
    """Badge deve usar class="badge-etiqueta" sem inline style de cor."""
    import ui.utils as utils
    html = utils._badge_etiqueta("doutorado")
    assert 'class="badge-etiqueta"' in html
    assert "background:#ede7f6" not in html
    assert "color:#6a1b9a" not in html
    assert "doutorado" in html


def test_css_tema_dark_contem_badge_escuro():
    import ui.utils as utils
    css = utils._css_tema(dark=True)
    assert ".badge-etiqueta" in css
    assert "#2d1b4e" in css


def test_css_tema_dark_contem_capa_placeholder_escuro():
    import ui.utils as utils
    css = utils._css_tema(dark=True)
    assert ".capa-placeholder" in css
    assert "#2d2d2d" in css


def test_css_tema_dark_contem_botao_titulo_claro():
    import ui.utils as utils
    css = utils._css_tema(dark=True)
    assert "#fafafa" in css


def test_css_tema_light_contem_badge_claro():
    import ui.utils as utils
    css = utils._css_tema(dark=False)
    assert "#ede7f6" in css
    assert "#6a1b9a" in css


def test_css_tema_light_contem_override_stapp():
    import ui.utils as utils
    css = utils._css_tema(dark=False)
    assert ".stApp" in css
    assert "#ffffff" in css


def test_css_tema_light_contem_sidebar():
    import ui.utils as utils
    css = utils._css_tema(dark=False)
    assert "stSidebar" in css
    assert "#f0f2f6" in css


def test_css_tema_dark_capa_img_fundo_escuro():
    import ui.utils as utils
    css = utils._css_tema(dark=True)
    assert ".capa-img" in css
    assert "#1e1e1e" in css


def test_css_tema_light_capa_img_fundo_branco():
    import ui.utils as utils
    css = utils._css_tema(dark=False)
    assert ".capa-img" in css
    assert "#ffffff" in css


def test_css_tema_light_botao_titulo_cobre_filhos():
    """Seletor * deve garantir que elementos filhos do botão recebam a cor."""
    import ui.utils as utils
    css = utils._css_tema(dark=False)
    assert 'button[kind="secondary"] *' in css
