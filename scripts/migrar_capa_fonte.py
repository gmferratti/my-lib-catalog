#!/usr/bin/env python3
"""One-shot migration: add capa_fonte to all existing records in biblioteca.jsonl / .csv."""

import sys
from pathlib import Path

# Add project root to path (one level up from scripts/)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from catalog.storage import carregar_todos_registros, reescrever_registros


def main() -> None:
    registros = carregar_todos_registros()
    if not registros:
        print("Nenhum registro encontrado.")
        return

    atualizados = 0
    for r in registros:
        if "capa_fonte" not in r:
            r["capa_fonte"] = "legado" if r.get("capa_url") else ""
            atualizados += 1

    if atualizados:
        reescrever_registros(registros)
        print(f"{atualizados} registro(s) migrado(s) — campo capa_fonte adicionado.")
    else:
        print("Todos os registros já têm capa_fonte. Nada a migrar.")


if __name__ == "__main__":
    main()
