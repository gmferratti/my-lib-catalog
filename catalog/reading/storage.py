import json
import threading
from datetime import datetime
from pathlib import Path

_lock = threading.Lock()
_LEITURA_FILE = "data/lista_leitura.json"


def _agora() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _carregar_raw() -> dict:
    path = Path(_LEITURA_FILE)
    if not path.exists():
        return {"itens": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _salvar_raw(data: dict) -> None:
    path = Path(_LEITURA_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _compactar_ordem(itens: list) -> None:
    na_fila = sorted(
        [i for i in itens if i["status"] == "na_fila"],
        key=lambda i: i["ordem"],
    )
    for idx, item in enumerate(na_fila, start=1):
        item["ordem"] = idx


def carregar() -> list:
    return _carregar_raw()["itens"]


def adicionar(isbn: str) -> None:
    with _lock:
        data = _carregar_raw()
        itens = data["itens"]
        if any(item["isbn"] == isbn for item in itens):
            raise ValueError(f"ISBN {isbn} já está na lista de leitura")
        na_fila = [item for item in itens if item["status"] == "na_fila"]
        itens.append({
            "isbn": isbn,
            "status": "na_fila",
            "ordem": len(na_fila) + 1,
            "progresso_paginas": 0,
            "data_adicao": _agora(),
            "data_inicio": None,
            "data_conclusao": None,
            "data_abandono": None,
        })
        _salvar_raw(data)


def atualizar_status(isbn: str, novo_status: str) -> None:
    with _lock:
        data = _carregar_raw()
        item = next((i for i in data["itens"] if i["isbn"] == isbn), None)
        if item is None:
            raise ValueError(f"ISBN {isbn} não encontrado na lista de leitura")
        saiu_da_fila = item["status"] == "na_fila" and novo_status != "na_fila"
        item["status"] = novo_status
        agora = _agora()
        if novo_status == "lendo" and item["data_inicio"] is None:
            item["data_inicio"] = agora
        elif novo_status == "lido":
            item["data_conclusao"] = agora
        elif novo_status == "abandonado":
            item["data_abandono"] = agora
        if saiu_da_fila:
            _compactar_ordem(data["itens"])
        _salvar_raw(data)


def atualizar_progresso(isbn: str, pagina: int) -> None:
    with _lock:
        data = _carregar_raw()
        item = next((i for i in data["itens"] if i["isbn"] == isbn), None)
        if item is None:
            raise ValueError(f"ISBN {isbn} não encontrado na lista de leitura")
        item["progresso_paginas"] = pagina
        _salvar_raw(data)


def reordenar(isbn: str, direcao: str) -> None:
    with _lock:
        data = _carregar_raw()
        na_fila = sorted(
            [i for i in data["itens"] if i["status"] == "na_fila"],
            key=lambda i: i["ordem"],
        )
        idx = next(
            (i for i, item in enumerate(na_fila) if item["isbn"] == isbn), None
        )
        if idx is None:
            return
        if direcao == "cima" and idx > 0:
            na_fila[idx]["ordem"], na_fila[idx - 1]["ordem"] = (
                na_fila[idx - 1]["ordem"],
                na_fila[idx]["ordem"],
            )
        elif direcao == "baixo" and idx < len(na_fila) - 1:
            na_fila[idx]["ordem"], na_fila[idx + 1]["ordem"] = (
                na_fila[idx + 1]["ordem"],
                na_fila[idx]["ordem"],
            )
        _salvar_raw(data)


def remover(isbn: str) -> None:
    with _lock:
        data = _carregar_raw()
        data["itens"] = [i for i in data["itens"] if i["isbn"] != isbn]
        _compactar_ordem(data["itens"])
        _salvar_raw(data)
