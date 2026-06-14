import pytest

import catalog.storage.persistence as pers


@pytest.fixture
def sample_isbn():
    return "9781098115784"


@pytest.fixture
def sample_record(sample_isbn):
    return {
        "isbn": sample_isbn,
        "titulo": "Machine Learning Design Patterns",
        "autores": "Valliappa Lakshmanan, Sara Robinson, Michael Munn",
        "editora": "O'Reilly Media",
        "ano": "2020",
        "paginas": 400,
        "idioma": "en",
        "assuntos": "Science, Computers",
        "capa_url": "https://covers.openlibrary.org/b/id/123-M.jpg",
        "fonte": "openlibrary",
        "data_cadastro": "2026-05-25T14:44:06",
    }


@pytest.fixture(autouse=False)
def tmp_data_dir(tmp_path, monkeypatch):
    """Redireciona os caminhos de arquivo para um diretório temporário isolado."""
    data_dir = tmp_path / "data"
    tmp_dir = tmp_path / "tmp"
    data_dir.mkdir()
    tmp_dir.mkdir()

    csv_file = str(data_dir / "biblioteca.csv")
    json_file = str(data_dir / "biblioteca.jsonl")
    pending_file = str(tmp_dir / "pendentes.txt")

    monkeypatch.setattr(pers, "CSV_FILE", csv_file)
    monkeypatch.setattr(pers, "JSON_FILE", json_file)
    monkeypatch.setattr(pers, "PENDING_FILE", pending_file)

    # Também corrige o CSV_HEADERS para o módulo de persistência
    import catalog.config as cfg
    monkeypatch.setattr(cfg, "CSV_FILE", csv_file)
    monkeypatch.setattr(cfg, "JSON_FILE", json_file)
    monkeypatch.setattr(cfg, "PENDING_FILE", pending_file)

    return {"csv": csv_file, "json": json_file, "pending": pending_file}
