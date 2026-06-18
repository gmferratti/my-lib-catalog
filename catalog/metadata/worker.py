import queue
import threading
from collections.abc import Callable

from .api import buscar_capa, buscar_metadados
from ..storage.persistence import remover_pendente, salvar


def worker(
    fila: queue.Queue,
    parar_evento: threading.Event,
    on_result: Callable[[dict], None] | None = None,
) -> None:
    """Consome ISBNs da fila e busca os metadados em background.

    on_result é chamado com o registro salvo (sucesso) ou com
    {"isbn": ..., "_erro": ...} em caso de exceção inesperada.
    """
    while not parar_evento.is_set():
        try:
            isbn = fila.get(timeout=0.5)
        except queue.Empty:
            continue
        if isbn is None:
            fila.task_done()
            break

        try:
            registro = buscar_metadados(isbn)
            metadata_capa = registro.get("capa_url", "")
            capa_dedicada, capa_fonte = buscar_capa(
                isbn, registro.get("titulo", ""), registro.get("autores", "")
            )
            if capa_dedicada:
                registro["capa_url"] = capa_dedicada
                registro["capa_fonte"] = capa_fonte
            else:
                registro["capa_url"] = metadata_capa
                registro["capa_fonte"] = ""
            salvar(registro)
            remover_pendente(isbn)
            if on_result is not None:
                on_result(registro)
        except Exception as e:
            # ISBN permanece em pendentes.txt para retry na próxima execução
            if on_result is not None:
                on_result({"isbn": isbn, "_erro": str(e)})
        finally:
            fila.task_done()
