#!/usr/bin/env python3
"""One-shot migration: normalize series titles to canonical format."""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from catalog.series import compor_titulo, detectar_serie
from catalog.storage import carregar_todos_registros, reescrever_registros


def main() -> None:
    registros = carregar_todos_registros()
    if not registros:
        print("Nenhum registro encontrado.")
        return

    normalizados = 0
    titulos_sem_padrao = []

    for r in registros:
        titulo = r.get("titulo", "")
        detectado = detectar_serie(titulo)
        if detectado:
            novo = compor_titulo(**detectado)
            if novo != titulo:
                print(f"  ANTES: {titulo!r}")
                print(f"  DEPOIS: {novo!r}")
                print()
                r["titulo"] = novo
                normalizados += 1
        else:
            titulos_sem_padrao.append(titulo)

    if normalizados:
        reescrever_registros(registros)
        print(f"{normalizados} título(s) normalizado(s).")
    else:
        print("Nenhum título a normalizar.")

    # Avisa sobre possíveis séries sem número de volume
    freq = Counter(titulos_sem_padrao)
    dups = [(t, c) for t, c in freq.items() if c > 1 and t]
    if dups:
        print("\nPossíveis séries sem número de volume (corrigir manualmente via dialog):")
        for titulo, count in sorted(dups, key=lambda x: -x[1]):
            print(f"  {count}x  {titulo!r}")


if __name__ == "__main__":
    main()
