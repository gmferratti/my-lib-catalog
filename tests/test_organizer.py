import json

import pytest

from catalog.organizer.algorithm import (
    _label,
    _ordenar,
    _sobrenome,
    capacidade_prateleira,
    organizar,
)
from catalog.organizer.models import ConfigEstantes, EstanteConfig, PrateleiraConfig
from catalog.organizer.storage import carregar_config, salvar_config


# ── Helpers ──────────────────────────────────────────────────────────────────

def _livro(isbn="0000000000", titulo="Título", autores="", assuntos="", ano="", fonte="openlibrary"):
    return {
        "isbn": isbn, "titulo": titulo, "autores": autores,
        "assuntos": assuntos, "ano": ano, "fonte": fonte,
        "editora": "", "paginas": "", "idioma": "", "capa_url": "",
        "data_cadastro": "2026-01-01T00:00:00",
    }


def _config(num_estantes=1, prateleiras=2, largura=80.0, espessura=2.5):
    estantes = [
        EstanteConfig(
            nome=f"Estante {i+1}",
            prateleiras=[
                PrateleiraConfig(nome=chr(65 + j), largura_cm=largura)
                for j in range(prateleiras)
            ],
        )
        for i in range(num_estantes)
    ]
    return ConfigEstantes(estantes=estantes, espessura_media_cm=espessura)


# ── capacidade_prateleira ─────────────────────────────────────────────────────

def test_capacidade_basica():
    assert capacidade_prateleira(80.0, 2.5) == 32


def test_capacidade_minima():
    assert capacidade_prateleira(2.0, 100.0) == 1


def test_capacidade_arredonda_para_baixo():
    assert capacidade_prateleira(81.0, 2.5) == 32  # 81/2.5 = 32.4 → 32


def test_capacidade_espessura_zero_retorna_um():
    assert capacidade_prateleira(80.0, 0.0) == 1


# ── _sobrenome ────────────────────────────────────────────────────────────────

def test_sobrenome_simples():
    assert _sobrenome("Isaac Asimov") == "ASIMOV"


def test_sobrenome_multiplos_autores():
    assert _sobrenome("Sara Robinson, Valliappa Lakshmanan") == "ROBINSON"


def test_sobrenome_vazio():
    assert _sobrenome("") == "ZZZZ"


def test_sobrenome_none_equivalente():
    assert _sobrenome("   ") == "ZZZZ"


# ── _ordenar ──────────────────────────────────────────────────────────────────

def test_ordenar_por_autor():
    livros = [
        _livro(autores="Zola, Émile"),
        _livro(autores="Asimov, Isaac"),
        _livro(autores="Clarke, Arthur C."),
    ]
    resultado = _ordenar(livros, "autor")
    sobrenomes = [_sobrenome(r["autores"]) for r in resultado]
    assert sobrenomes == sorted(sobrenomes)


def test_ordenar_por_assunto():
    livros = [
        _livro(autores="Z Author", assuntos="Ficção, Terror"),
        _livro(autores="A Author", assuntos="Ciência"),
        _livro(autores="B Author", assuntos="Ficção, Drama"),
    ]
    resultado = _ordenar(livros, "assunto")
    # Ciência < Ficção → A Author; dentro de Ficção, sobrenome "AUTHOR" igual →
    # tiebreaker por nome completo: "B Author" < "Z Author"
    assert resultado[0]["autores"] == "A Author"
    assert resultado[1]["autores"] == "B Author"
    assert resultado[2]["autores"] == "Z Author"


def test_ordenar_por_ano_mais_recente_primeiro():
    livros = [
        _livro(ano="1985"),
        _livro(ano="2020"),
        _livro(ano="2001"),
    ]
    resultado = _ordenar(livros, "ano")
    anos = [r["ano"] for r in resultado]
    assert anos == ["2020", "2001", "1985"]


def test_desconhecidos_ficam_no_fim_em_todos_os_estilos():
    livros = [
        _livro(autores="Asimov, Isaac", fonte="openlibrary"),
        _livro(autores="", fonte="nao_encontrado"),
        _livro(autores="Clarke, Arthur", fonte="googlebooks"),
    ]
    for estilo in ("autor", "assunto", "ano"):
        resultado = _ordenar(livros, estilo)
        assert resultado[-1]["fonte"] == "nao_encontrado", f"falhou para estilo={estilo}"


# ── _label ────────────────────────────────────────────────────────────────────

def test_label_autor():
    livros = [
        _livro(autores="Isaac Asimov"),
        _livro(autores="Arthur Clarke"),
    ]
    label = _label(livros, "autor")
    assert "ASI" in label.upper()
    assert "CLA" in label.upper()


def test_label_assunto():
    livros = [
        _livro(assuntos="Ficção Científica, Aventura"),
        _livro(assuntos="Fantasia"),
    ]
    label = _label(livros, "assunto")
    assert label  # não vazio
    assert "Ficção" in label or "FICÇÃO" in label.upper()


def test_label_ano():
    livros = [_livro(ano="2020"), _livro(ano="1985"), _livro(ano="2010")]
    label = _label(livros, "ano")
    assert "1985" in label
    assert "2020" in label


def test_label_prateleira_vazia():
    assert _label([], "autor") == "(vazia)"


# ── organizar ─────────────────────────────────────────────────────────────────

def test_distribuir_prateleiras_sem_overflow():
    livros = [_livro(isbn=str(i), autores=f"Autor {i}") for i in range(50)]
    cfg = _config(num_estantes=1, prateleiras=2, largura=80.0, espessura=2.5)
    # capacidade por prateleira = 32, total = 64
    resultados, sem_lugar = organizar(livros, cfg, "autor")
    assert len(sem_lugar) == 0
    total_distribuidos = sum(len(r.livros) for r in resultados)
    assert total_distribuidos == 50


def test_overflow():
    livros = [_livro(isbn=str(i), autores=f"Autor {i}") for i in range(100)]
    cfg = _config(num_estantes=1, prateleiras=2, largura=80.0, espessura=2.5)
    # capacidade total = 64, livros = 100
    resultados, sem_lugar = organizar(livros, cfg, "autor")
    assert len(sem_lugar) == 36
    total_distribuidos = sum(len(r.livros) for r in resultados)
    assert total_distribuidos == 64


def test_prateleiras_preenchidas_em_ordem():
    livros = [_livro(isbn=str(i), autores=f"Autor {i}") for i in range(70)]
    cfg = _config(num_estantes=1, prateleiras=3, largura=80.0, espessura=2.5)
    # capacidade por prateleira = 32
    resultados, _ = organizar(livros, cfg, "autor")
    assert len(resultados[0].livros) == 32
    assert len(resultados[1].livros) == 32
    assert len(resultados[2].livros) == 6


def test_organizar_config_vazia_retorna_overflow():
    livros = [_livro(isbn=str(i)) for i in range(5)]
    cfg = ConfigEstantes(estantes=[], espessura_media_cm=2.5)
    resultados, sem_lugar = organizar(livros, cfg, "autor")
    assert resultados == []
    assert len(sem_lugar) == 5


# ── storage roundtrip ─────────────────────────────────────────────────────────

def test_salvar_e_carregar_config(tmp_path):
    path = str(tmp_path / "estantes.json")
    cfg = ConfigEstantes(
        estantes=[
            EstanteConfig(
                nome="Estante 1",
                prateleiras=[
                    PrateleiraConfig(nome="A", largura_cm=80.0),
                    PrateleiraConfig(nome="B", largura_cm=100.0),
                ],
            )
        ],
        espessura_media_cm=3.0,
    )
    salvar_config(cfg, path)
    carregado = carregar_config(path)

    assert carregado.espessura_media_cm == 3.0
    assert len(carregado.estantes) == 1
    assert carregado.estantes[0].nome == "Estante 1"
    assert len(carregado.estantes[0].prateleiras) == 2
    assert carregado.estantes[0].prateleiras[1].largura_cm == 100.0


def test_carregar_config_arquivo_inexistente(tmp_path):
    cfg = carregar_config(str(tmp_path / "nao_existe.json"))
    assert cfg.estantes == []
    assert cfg.espessura_media_cm == 2.5


def test_config_json_valido(tmp_path):
    path = str(tmp_path / "estantes.json")
    cfg = _config(num_estantes=2, prateleiras=3, largura=90.0)
    salvar_config(cfg, path)
    with open(path) as f:
        data = json.load(f)
    assert "estantes" in data
    assert len(data["estantes"]) == 2
    assert data["estantes"][0]["prateleiras"][0]["largura_cm"] == 90.0


def test_salvar_config_commita(tmp_path):
    from unittest.mock import patch
    from catalog.organizer.storage import salvar_config
    from catalog.organizer.models import ConfigEstantes
    config = ConfigEstantes(estantes=[], espessura_media_cm=2.5)
    path = str(tmp_path / "estantes.json")
    with patch("catalog.storage.git_sync.commit_se_houver_mudancas") as mock_commit:
        salvar_config(config, path=path)
    mock_commit.assert_called_once()
    assert mock_commit.call_args.args[0] == "estantes: configuração atualizada"
