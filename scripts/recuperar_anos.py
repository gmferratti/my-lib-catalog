#!/usr/bin/env python3
"""Recupera anos ausentes (gravados como 'None') para registros do acervo.

Re-consulta as APIs para cada livro com ano inválido e atualiza apenas
o campo 'ano' se um valor for encontrado. Mantém todos os outros campos.

Uso:
    python scripts/recuperar_anos.py
    python scripts/recuperar_anos.py --dry-run
    python scripts/recuperar_anos.py --apis openlibrary,googlebooks
    python scripts/recuperar_anos.py --apis brasilapi,googlebooks --dry-run
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from catalog.metadata.api import FONTES_METADADOS, buscar_metadados
from catalog.storage import carregar_todos_registros, reescrever_registros

DRY_RUN = "--dry-run" in sys.argv
CHECKPOINT = 20
PAUSA_S = 0.5

# --apis openlibrary,googlebooks  (None = usa config_apis.json ou padrão)
APIS: list[str] | None = None
for _i, _arg in enumerate(sys.argv):
    if _arg == "--apis" and _i + 1 < len(sys.argv):
        APIS = [a.strip() for a in sys.argv[_i + 1].split(",")]
        break
    if _arg.startswith("--apis="):
        APIS = [a.strip() for a in _arg.split("=", 1)[1].split(",")]
        break

_IDS_VALIDOS = {f for f, _, _ in FONTES_METADADOS}
if APIS is not None:
    _invalidos = [a for a in APIS if a not in _IDS_VALIDOS]
    if _invalidos:
        print(f"ERRO: APIs desconhecidas: {', '.join(_invalidos)}")
        print(f"Válidas: {', '.join(f for f, _, _ in FONTES_METADADOS)}")
        sys.exit(1)


def _ano_invalido(r: dict) -> bool:
    v = str(r.get("ano") or "").strip()
    return not v or v.lower() == "none"


def main() -> None:
    if APIS is not None:
        print(f"APIs selecionadas: {', '.join(APIS)}")

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
            resultado = buscar_metadados(isbn, apis_metadados=APIS)
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
