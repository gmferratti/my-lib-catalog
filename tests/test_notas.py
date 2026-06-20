import pytest
import catalog.notas.storage as notas_storage


@pytest.fixture(autouse=True)
def tmp_notas_file(tmp_path, monkeypatch):
    tmp_file = tmp_path / "notas.json"
    monkeypatch.setattr(notas_storage, "_NOTAS_FILE", str(tmp_file))


def test_carregar_isbn_sem_nota():
    assert notas_storage.carregar("9781098115784") is None


def test_salvar_e_carregar():
    links = [{"url": "https://example.com", "rotulo": "Exemplo"}]
    notas_storage.salvar("9781098115784", "Boa leitura", links)
    nota = notas_storage.carregar("9781098115784")
    assert nota["anotacao"] == "Boa leitura"
    assert nota["links"] == links
    assert "data_modificacao" in nota


def test_salvar_atualiza_data_modificacao(monkeypatch):
    monkeypatch.setattr(notas_storage, "_agora", lambda: "2026-01-01T10:00:00")
    notas_storage.salvar("9781098115784", "v1", [])
    nota1 = notas_storage.carregar("9781098115784")

    monkeypatch.setattr(notas_storage, "_agora", lambda: "2026-01-01T10:00:01")
    notas_storage.salvar("9781098115784", "v2", [])
    nota2 = notas_storage.carregar("9781098115784")

    assert nota1["data_modificacao"] == "2026-01-01T10:00:00"
    assert nota2["data_modificacao"] == "2026-01-01T10:00:01"


def test_salvar_substitui_nota_existente():
    notas_storage.salvar("9781098115784", "versão 1", [])
    notas_storage.salvar(
        "9781098115784",
        "versão 2",
        [{"url": "https://x.com", "rotulo": "X"}],
    )
    nota = notas_storage.carregar("9781098115784")
    assert nota["anotacao"] == "versão 2"
    assert len(nota["links"]) == 1


def test_remover():
    notas_storage.salvar("9781098115784", "para remover", [])
    notas_storage.remover("9781098115784")
    assert notas_storage.carregar("9781098115784") is None


def test_remover_isbn_inexistente():
    notas_storage.remover("9999999999999")  # não deve lançar exceção
