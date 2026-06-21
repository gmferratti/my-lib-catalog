import csv
import json
import logging
from unittest.mock import patch

import pytest

import catalog.storage.persistence as pers
from catalog.storage import (
    adicionar_pendente,
    carregar_isbns_cadastrados,
    carregar_pendentes,
    carregar_todos_registros,
    reescrever_registros,
    remover_pendente,
    salvar,
)


@pytest.fixture(autouse=True)
def _isolate(tmp_data_dir):
    """Garante isolamento de dados em todos os testes deste módulo."""
    pass


def test_salvar_cria_csv_e_jsonl(sample_record):
    salvar(sample_record)
    assert pers.Path(pers.CSV_FILE).exists()
    assert pers.Path(pers.JSON_FILE).exists()


def test_salvar_escreve_dados_corretos(sample_record):
    salvar(sample_record)
    registros = carregar_todos_registros()
    assert len(registros) == 1
    assert registros[0]["isbn"] == sample_record["isbn"]
    assert registros[0]["titulo"] == sample_record["titulo"]


def test_salvar_faz_append(sample_record):
    salvar(sample_record)
    segundo = {**sample_record, "isbn": "9780201633610", "titulo": "The Pragmatic Programmer"}
    salvar(segundo)
    registros = carregar_todos_registros()
    assert len(registros) == 2


def test_csv_header_escrito_uma_vez(sample_record):
    salvar(sample_record)
    salvar({**sample_record, "isbn": "9780201633610"})
    with open(pers.CSV_FILE, encoding="utf-8") as f:
        linhas = f.readlines()
    header_count = sum(1 for l in linhas if l.startswith("isbn,"))
    assert header_count == 1


def test_carregar_todos_registros_vazio():
    assert carregar_todos_registros() == []


def test_carregar_isbns_cadastrados_vazio():
    assert carregar_isbns_cadastrados() == set()


def test_carregar_isbns_cadastrados(sample_record):
    salvar(sample_record)
    isbns = carregar_isbns_cadastrados()
    assert sample_record["isbn"] in isbns


def test_adicionar_pendente(sample_isbn):
    adicionar_pendente(sample_isbn)
    pendentes = carregar_pendentes()
    assert sample_isbn in pendentes


def test_remover_pendente(sample_isbn):
    adicionar_pendente(sample_isbn)
    adicionar_pendente("9780201633610")
    remover_pendente(sample_isbn)
    pendentes = carregar_pendentes()
    assert sample_isbn not in pendentes
    assert "9780201633610" in pendentes


def test_carregar_pendentes_vazio():
    assert carregar_pendentes() == []


def test_reescrever_registros(sample_record):
    salvar(sample_record)
    atualizado = {**sample_record, "titulo": "Título Atualizado"}
    reescrever_registros([atualizado])
    registros = carregar_todos_registros()
    assert len(registros) == 1
    assert registros[0]["titulo"] == "Título Atualizado"


def test_reescrever_registros_atualiza_csv(sample_record):
    salvar(sample_record)
    atualizado = {**sample_record, "titulo": "Novo Título"}
    reescrever_registros([atualizado])
    with open(pers.CSV_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 1
    assert rows[0]["titulo"] == "Novo Título"


def test_reescrever_registros_commita(sample_record):
    salvar(sample_record)
    atualizado = {**sample_record, "titulo": "Novo"}
    with patch("catalog.storage.git_sync.commit_se_houver_mudancas") as mock_commit:
        reescrever_registros([atualizado])
    mock_commit.assert_called_once()
    mensagem = mock_commit.call_args.args[0]
    assert mensagem.startswith("edit:")


def test_salvar_etiquetas(sample_record):
    registro = {**sample_record, "etiquetas": "lazer, doutorado"}
    salvar(registro)

    # JSONL roundtrip
    registros = carregar_todos_registros()
    assert registros[0].get("etiquetas") == "lazer, doutorado"

    # CSV deve ter coluna etiquetas
    with open(pers.CSV_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert "etiquetas" in rows[0], "coluna etiquetas ausente no CSV"
    assert rows[0]["etiquetas"] == "lazer, doutorado"


def test_salvar_loga_debug(sample_record, tmp_data_dir, caplog):
    with caplog.at_level(logging.DEBUG, logger="catalog.storage.persistence"):
        salvar(sample_record)
    mensagens = [r.message for r in caplog.records]
    assert any("salvando" in m for m in mensagens)
    assert any(sample_record["isbn"] in m for m in mensagens)


def test_reescrever_registros_loga_debug(sample_record, tmp_data_dir, caplog):
    salvar(sample_record)
    registros = carregar_todos_registros()
    with caplog.at_level(logging.DEBUG, logger="catalog.storage.persistence"):
        reescrever_registros(registros)
    assert any("reescrevendo" in r.message for r in caplog.records)
