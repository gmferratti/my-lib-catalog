import importlib
import queue
import sys
import threading

import pytest

from catalog.metadata.worker import worker

# importlib.import_module retorna o módulo (não a função), contornando a
# colisão de nomes causada pelo "from .worker import worker" no __init__.py
_worker_mod = importlib.import_module("catalog.metadata.worker")


@pytest.fixture(autouse=True)
def _isolate(tmp_data_dir):
    pass


def _run_worker(fila, on_result=None, timeout=2):
    """Inicia o worker em thread separada e aguarda conclusão."""
    parar = threading.Event()
    t = threading.Thread(target=worker, args=(fila, parar), kwargs={"on_result": on_result})
    t.start()
    fila.join()
    parar.set()
    fila.put(None)
    t.join(timeout=timeout)


def test_worker_chama_buscar_e_salvar(mocker, sample_isbn, sample_record):
    mock_buscar = mocker.patch.object(
        _worker_mod, "buscar_metadados", return_value=sample_record
    )
    mock_salvar = mocker.patch.object(_worker_mod, "salvar")
    mocker.patch.object(_worker_mod, "remover_pendente")

    fila = queue.Queue()
    fila.put(sample_isbn)
    _run_worker(fila)

    mock_buscar.assert_called_once_with(sample_isbn)
    mock_salvar.assert_called_once_with(sample_record)


def test_worker_chama_on_result_com_registro(mocker, sample_isbn, sample_record):
    mocker.patch.object(_worker_mod, "buscar_metadados", return_value=sample_record)
    mocker.patch.object(_worker_mod, "salvar")
    mocker.patch.object(_worker_mod, "remover_pendente")

    resultados = []
    fila = queue.Queue()
    fila.put(sample_isbn)
    _run_worker(fila, on_result=resultados.append)

    assert len(resultados) == 1
    assert resultados[0] == sample_record


def test_worker_para_no_sentinel():
    fila = queue.Queue()
    parar = threading.Event()
    fila.put(None)
    t = threading.Thread(target=worker, args=(fila, parar))
    t.start()
    t.join(timeout=2)
    assert not t.is_alive()


def test_worker_excecao_nao_derruba_worker(mocker, sample_isbn, sample_record):
    isbn2 = "9780201633610"
    mocker.patch.object(
        _worker_mod, "buscar_metadados",
        side_effect=[RuntimeError("falha"), sample_record],
    )
    mocker.patch.object(_worker_mod, "salvar")
    mocker.patch.object(_worker_mod, "remover_pendente")

    erros = []
    sucessos = []

    def on_result(r):
        if "_erro" in r:
            erros.append(r)
        else:
            sucessos.append(r)

    fila = queue.Queue()
    fila.put(sample_isbn)
    fila.put(isbn2)
    _run_worker(fila, on_result=on_result)

    assert len(erros) == 1
    assert erros[0]["isbn"] == sample_isbn
    assert len(sucessos) == 1


def test_worker_on_result_none_nao_falha(mocker, sample_isbn, sample_record):
    mocker.patch.object(_worker_mod, "buscar_metadados", return_value=sample_record)
    mocker.patch.object(_worker_mod, "salvar")
    mocker.patch.object(_worker_mod, "remover_pendente")

    fila = queue.Queue()
    fila.put(sample_isbn)
    _run_worker(fila, on_result=None)  # não deve lançar exceção
