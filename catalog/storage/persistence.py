import csv
import json
import threading
from pathlib import Path

from ..config import CAPAS_MANUAIS_FILE, CSV_FILE, CSV_HEADERS, JSON_FILE, PENDING_FILE
from . import git_sync

_io_lock = threading.Lock()

# Garante que os diretórios de dados existam ao importar o módulo
Path(CSV_FILE).parent.mkdir(parents=True, exist_ok=True)
Path(PENDING_FILE).parent.mkdir(parents=True, exist_ok=True)


def carregar_isbns_cadastrados() -> set[str]:
    if not Path(CSV_FILE).exists():
        return set()
    with open(CSV_FILE, newline="", encoding="utf-8") as f:
        return {linha["isbn"] for linha in csv.DictReader(f) if linha.get("isbn")}


def carregar_pendentes() -> list[str]:
    if not Path(PENDING_FILE).exists():
        return []
    with open(PENDING_FILE, encoding="utf-8") as f:
        return [linha.strip() for linha in f if linha.strip()]


def adicionar_pendente(isbn: str) -> None:
    with _io_lock:
        with open(PENDING_FILE, "a", encoding="utf-8") as f:
            f.write(isbn + "\n")


def remover_pendente(isbn: str) -> None:
    with _io_lock:
        if not Path(PENDING_FILE).exists():
            return
        with open(PENDING_FILE, encoding="utf-8") as f:
            linhas = [l.strip() for l in f if l.strip()]
        linhas = [l for l in linhas if l != isbn]
        with open(PENDING_FILE, "w", encoding="utf-8") as f:
            for isbn_restante in linhas:
                f.write(isbn_restante + "\n")


def salvar(registro: dict) -> None:
    from ..series import compor_titulo, detectar_serie  # import local evita ciclo

    titulo = registro.get("titulo", "")
    if titulo:
        detectado = detectar_serie(titulo)
        if detectado:
            registro = {**registro, "titulo": compor_titulo(**detectado)}

    with _io_lock:
        novo = not Path(CSV_FILE).exists()
        with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            if novo:
                w.writeheader()
            w.writerow({k: registro.get(k, "") for k in CSV_HEADERS})
        with open(JSON_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")


def _capas_manuais() -> dict:
    try:
        return json.loads(Path(CAPAS_MANUAIS_FILE).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def carregar_todos_registros() -> list[dict]:
    if not Path(JSON_FILE).exists():
        return []
    with open(JSON_FILE, encoding="utf-8") as f:
        registros = [json.loads(linha) for linha in f if linha.strip()]
    manuais = _capas_manuais()
    if manuais:
        for r in registros:
            url = manuais.get(r.get("isbn", ""))
            if url:
                r["capa_url"] = url
                r["capa_fonte"] = "manual"
    return registros


def reescrever_registros(registros: list[dict]) -> None:
    with _io_lock:
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            for r in registros:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            w.writeheader()
            for r in registros:
                w.writerow({k: r.get(k, "") for k in CSV_HEADERS})
    if len(registros) == 1:
        titulo = registros[0].get("titulo") or registros[0].get("isbn", "?")
    else:
        titulo = f"{len(registros)} registros"
    git_sync.commit_se_houver_mudancas(f"edit: {titulo}", arquivos=[JSON_FILE, CSV_FILE])
