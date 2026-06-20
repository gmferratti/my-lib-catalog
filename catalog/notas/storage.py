import json
import os
import threading
from datetime import datetime

import catalog.storage.git_sync as git_sync

_lock = threading.Lock()
_NOTAS_FILE = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "notas.json")
)


def _agora() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _carregar_raw() -> dict:
    try:
        with open(_NOTAS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, FileNotFoundError):
        return {"notas": {}}


def _salvar_raw(data: dict) -> None:
    os.makedirs(os.path.dirname(_NOTAS_FILE), exist_ok=True)
    with open(_NOTAS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def carregar(isbn: str) -> dict | None:
    return _carregar_raw()["notas"].get(isbn)


def salvar(isbn: str, anotacao: str, links: list[dict]) -> None:
    with _lock:
        data = _carregar_raw()
        data["notas"][isbn] = {
            "anotacao": anotacao,
            "links": links,
            "data_modificacao": _agora(),
        }
        _salvar_raw(data)
    git_sync.commit_se_houver_mudancas(
        f"notas: {isbn} – anotação atualizada", arquivos=[_NOTAS_FILE]
    )


def remover(isbn: str) -> None:
    modificado = False
    with _lock:
        data = _carregar_raw()
        if isbn in data["notas"]:
            del data["notas"][isbn]
            _salvar_raw(data)
            modificado = True
    if modificado:
        git_sync.commit_se_houver_mudancas(
            f"notas: {isbn} – nota removida", arquivos=[_NOTAS_FILE]
        )
