import queue
import threading

from .api import buscar_metadados
from .persistence import remover_pendente, salvar


def worker(fila: queue.Queue, parar_evento: threading.Event) -> None:
    """Consome ISBNs da fila e busca os metadados em background."""
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
            salvar(registro)
            remover_pendente(isbn)
            if registro.get("titulo"):
                print(f"\n  ✓ [{isbn}] {registro['titulo']} — {registro['autores']}",
                      flush=True)
            else:
                print(f"\n  ⚠  [{isbn}] sem metadados — salvo só o ISBN",
                      flush=True)
        except Exception as e:
            # ISBN permanece em pendentes.txt para retry na próxima execução
            print(f"\n  ✗ [{isbn}] erro inesperado: {e}  (fica pendente)",
                  flush=True)
        finally:
            fila.task_done()
