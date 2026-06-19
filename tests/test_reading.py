import pytest
import catalog.config as cfg
import catalog.reading.storage as storage


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    leitura_file = str(tmp_path / "data" / "lista_leitura.json")
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(cfg, "LEITURA_FILE", leitura_file)


def test_carregar_vazio():
    assert storage.carregar() == []


def test_adicionar_cria_item_na_fila():
    storage.adicionar("9781098115784")
    itens = storage.carregar()
    assert len(itens) == 1
    assert itens[0]["isbn"] == "9781098115784"
    assert itens[0]["status"] == "na_fila"
    assert itens[0]["ordem"] == 1
    assert itens[0]["progresso_paginas"] == 0


def test_adicionar_duplicado_levanta_value_error():
    storage.adicionar("9781098115784")
    with pytest.raises(ValueError, match="já está na lista"):
        storage.adicionar("9781098115784")


def test_adicionar_multiplos_incrementa_ordem():
    storage.adicionar("9781098115784")
    storage.adicionar("9780201633610")
    itens = storage.carregar()
    na_fila = sorted(
        [i for i in itens if i["status"] == "na_fila"], key=lambda i: i["ordem"]
    )
    assert na_fila[0]["isbn"] == "9781098115784"
    assert na_fila[1]["isbn"] == "9780201633610"
    assert na_fila[1]["ordem"] == 2


def test_atualizar_status_para_lendo_preenche_data_inicio():
    storage.adicionar("9781098115784")
    storage.atualizar_status("9781098115784", "lendo")
    item = storage.carregar()[0]
    assert item["status"] == "lendo"
    assert item["data_inicio"] is not None


def test_atualizar_status_para_lido_preenche_data_conclusao():
    storage.adicionar("9781098115784")
    storage.atualizar_status("9781098115784", "lendo")
    storage.atualizar_status("9781098115784", "lido")
    item = storage.carregar()[0]
    assert item["status"] == "lido"
    assert item["data_conclusao"] is not None


def test_atualizar_status_para_abandonado_preenche_data_abandono():
    storage.adicionar("9781098115784")
    storage.atualizar_status("9781098115784", "lendo")
    storage.atualizar_status("9781098115784", "abandonado")
    item = storage.carregar()[0]
    assert item["status"] == "abandonado"
    assert item["data_abandono"] is not None


def test_atualizar_status_retorno_para_na_fila_mantem_progresso():
    storage.adicionar("9781098115784")
    storage.atualizar_status("9781098115784", "lendo")
    storage.atualizar_progresso("9781098115784", 80)
    storage.atualizar_status("9781098115784", "na_fila")
    item = storage.carregar()[0]
    assert item["status"] == "na_fila"
    assert item["progresso_paginas"] == 80


def test_atualizar_status_compacta_ordem_ao_sair_da_fila():
    storage.adicionar("9781098115784")
    storage.adicionar("9780201633610")
    storage.adicionar("9780596516178")
    storage.atualizar_status("9781098115784", "lendo")
    itens = storage.carregar()
    na_fila = sorted(
        [i for i in itens if i["status"] == "na_fila"], key=lambda i: i["ordem"]
    )
    assert na_fila[0]["isbn"] == "9780201633610"
    assert na_fila[0]["ordem"] == 1
    assert na_fila[1]["isbn"] == "9780596516178"
    assert na_fila[1]["ordem"] == 2


def test_atualizar_progresso():
    storage.adicionar("9781098115784")
    storage.atualizar_status("9781098115784", "lendo")
    storage.atualizar_progresso("9781098115784", 150)
    item = storage.carregar()[0]
    assert item["progresso_paginas"] == 150


def test_reordenar_cima():
    storage.adicionar("9781098115784")
    storage.adicionar("9780201633610")
    storage.reordenar("9780201633610", "cima")
    na_fila = sorted(
        [i for i in storage.carregar() if i["status"] == "na_fila"],
        key=lambda i: i["ordem"],
    )
    assert na_fila[0]["isbn"] == "9780201633610"
    assert na_fila[1]["isbn"] == "9781098115784"


def test_reordenar_baixo():
    storage.adicionar("9781098115784")
    storage.adicionar("9780201633610")
    storage.reordenar("9781098115784", "baixo")
    na_fila = sorted(
        [i for i in storage.carregar() if i["status"] == "na_fila"],
        key=lambda i: i["ordem"],
    )
    assert na_fila[0]["isbn"] == "9780201633610"
    assert na_fila[1]["isbn"] == "9781098115784"


def test_reordenar_sem_efeito_no_topo():
    storage.adicionar("9781098115784")
    storage.adicionar("9780201633610")
    storage.reordenar("9781098115784", "cima")
    na_fila = sorted(
        [i for i in storage.carregar() if i["status"] == "na_fila"],
        key=lambda i: i["ordem"],
    )
    assert na_fila[0]["isbn"] == "9781098115784"


def test_reordenar_sem_efeito_no_final():
    storage.adicionar("9781098115784")
    storage.adicionar("9780201633610")
    storage.reordenar("9780201633610", "baixo")
    na_fila = sorted(
        [i for i in storage.carregar() if i["status"] == "na_fila"],
        key=lambda i: i["ordem"],
    )
    assert na_fila[1]["isbn"] == "9780201633610"


def test_remover():
    storage.adicionar("9781098115784")
    storage.adicionar("9780201633610")
    storage.remover("9781098115784")
    itens = storage.carregar()
    assert len(itens) == 1
    assert itens[0]["isbn"] == "9780201633610"


def test_remover_compacta_ordem():
    storage.adicionar("9781098115784")
    storage.adicionar("9780201633610")
    storage.adicionar("9780596516178")
    storage.remover("9780201633610")
    na_fila = sorted(
        [i for i in storage.carregar() if i["status"] == "na_fila"],
        key=lambda i: i["ordem"],
    )
    assert na_fila[0]["isbn"] == "9781098115784"
    assert na_fila[0]["ordem"] == 1
    assert na_fila[1]["isbn"] == "9780596516178"
    assert na_fila[1]["ordem"] == 2
