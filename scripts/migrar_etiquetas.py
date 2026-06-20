#!/usr/bin/env python3
"""One-shot migration: add etiquetas field to all existing records."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from catalog.storage import carregar_todos_registros, reescrever_registros


def main() -> None:
    registros = carregar_todos_registros()
    if not registros:
        print("Nenhum registro encontrado.")
        return

    atualizados = 0
    for r in registros:
        if "etiquetas" not in r:
            r["etiquetas"] = ""
            atualizados += 1

    if atualizados:
        reescrever_registros(registros)
        print(f"{atualizados} registro(s) migrado(s) — campo etiquetas adicionado.")
    else:
        print("Todos os registros já têm o campo etiquetas. Nada a migrar.")


if __name__ == "__main__":
    main()
