#!/usr/bin/env python3
"""Recupera anos ausentes (gravados como 'None') para registros do acervo.

Re-consulta as APIs para cada livro com ano inválido e atualiza apenas
o campo 'ano' se um valor for encontrado. Mantém todos os outros campos.

Uso:
    python scripts/recuperar_anos.py
    python scripts/recuperar_anos.py --dry-run   # só mostra o que faria
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from catalog.metadata.api import buscar_metadados
from catalog.storage import carregar_todos_registros, reescrever_registros

DRY_RUN = "--dry-run" in sys.argv
CHECKPOINT = 20   # salva a cada N livros para não perder progresso
PAUSA_S = 0.5     # delay entre ISBNs para respeitar rate limits


def _ano_invalido(r: dict) -> bool:
    v = str(r.get("ano") or "").strip()
    return not v or v.lower() == "none"


def main() -> None:
    registros = carregar_todos_registros()
    indices = [i for i, r in enumerate(registros) if _ano_invalido(r)]
    total = len(indices)

    print(f"Registros com ano ausente ou inválido: {total}")
    if not total:
        print("Nada a recuperar.")
        return
    if DRY_RUN:
        print("(dry-run — nenhuma alteração será salva)\n")

    atualizados = 0
    nao_encontrados = 0

    for n, i in enumerate(indices, 1):
        r = registros[i]
        isbn = r["isbn"]
        titulo = (r.get("titulo") or isbn)[:60]
        print(f"[{n:>3}/{total}] {titulo}", end=" … ", flush=True)

        try:
            resultado = buscar_metadados(isbn)
            ano = str(resultado.get("ano") or "").strip()
            if ano and ano.lower() != "none":
                if not DRY_RUN:
                    r["ano"] = ano
                atualizados += 1
                print(f"✓ {ano}")
            else:
                if not DRY_RUN:
                    r["ano"] = ""
                nao_encontrados += 1
                print("– não encontrado nas APIs")
        except Exception as e:
            if not DRY_RUN:
                r["ano"] = ""
            print(f"ERRO: {e}")

        if not DRY_RUN and n % CHECKPOINT == 0:
            reescrever_registros(registros)
            print(f"  ↳ checkpoint: {n}/{total} processados, {atualizados} atualizados")

        if n < total:
            time.sleep(PAUSA_S)

    if not DRY_RUN:
        reescrever_registros(registros)

    print(f"\n{'[dry-run] ' if DRY_RUN else ''}Concluído:")
    print(f"  {atualizados}/{total} anos recuperados")
    print(f"  {nao_encontrados}/{total} não encontrados nas APIs")


if __name__ == "__main__":
    main()
