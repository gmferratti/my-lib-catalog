#!/usr/bin/env python3
"""
Cadastro de biblioteca via leitor de código de barras (modo assíncrono).

Escaneamento e busca de metadados são desacoplados: o ISBN escaneado entra
em uma fila e um worker em background consulta as APIs (Open Library →
Google Books → Mercado Livre → ISBNdb). Você pode escanear o acervo
inteiro sem esperar a rede.

Arquivos gerados:
  - data/biblioteca.csv   : acervo (uma linha por livro, pronto pra planilha)
  - data/biblioteca.jsonl : mesmo conteúdo em JSON Lines
  - tmp/pendentes.txt     : ISBNs enfileirados ainda não processados
                            (re-enfileirados automaticamente na próxima execução)

Comandos durante a sessão:
  sair         : encerra após drenar a fila
  fila         : mostra quantos ISBNs ainda estão pendentes
  reprocessar  : re-tenta busca de metadados para ISBNs sem dados (fila deve estar vazia)
  Ctrl+C       : interrompe; ISBNs pendentes ficam pra próxima execução
"""

import argparse
import queue
import sys
import threading
from pathlib import Path

# Make src/ findable when running as `python scripts/main.py`
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from catalog.metadata import buscar_metadados, worker
from catalog.scanning import normalizar_isbn
from catalog.storage import (
    adicionar_pendente,
    carregar_isbns_cadastrados,
    carregar_pendentes,
    carregar_todos_registros,
    reescrever_registros,
)


def _on_result(registro: dict) -> None:
    if "_erro" in registro:
        print(f"\n  ✗ [{registro['isbn']}] erro inesperado: {registro['_erro']}  (fica pendente)",
              flush=True)
    elif registro.get("titulo"):
        print(f"\n  ✓ [{registro['isbn']}] {registro['titulo']} — {registro['autores']}",
              flush=True)
    else:
        print(f"\n  ⚠  [{registro['isbn']}] sem metadados — salvo só o ISBN",
              flush=True)


def _reprocessar_nao_encontrados() -> None:
    registros = carregar_todos_registros()
    falhos = [r for r in registros if r.get("fonte") == "nao_encontrado"]
    if not falhos:
        print("  → Nenhum ISBN sem metadados para reprocessar.\n")
        return
    print(f"  → Reprocessando {len(falhos)} ISBN(s) com metadados ausentes...")
    atualizados = 0
    for r in registros:
        if r.get("fonte") != "nao_encontrado":
            continue
        isbn = r["isbn"]
        print(f"     {isbn}...", end=" ", flush=True)
        novo = buscar_metadados(isbn)
        if novo.get("titulo"):
            r.update(novo)
            atualizados += 1
            print(f"✓  {novo['titulo']}")
        else:
            print("sem metadados")
    if atualizados:
        reescrever_registros(registros)
        print(f"  → {atualizados} registro(s) atualizado(s).\n")
    else:
        print("  → Nenhum novo dado encontrado.\n")


def main() -> None:
    print("📚  Cadastro de biblioteca — modo assíncrono")
    print("    Escaneie sem parar. Os metadados vêm em background.")
    print("    Comandos: 'sair', 'fila', 'reprocessar', Ctrl+C\n")

    conhecidos = carregar_isbns_cadastrados()
    fila: queue.Queue = queue.Queue()
    parar_evento = threading.Event()

    pendentes = carregar_pendentes()
    if pendentes:
        print(f"    {len(pendentes)} ISBN(s) pendente(s) da última sessão — re-enfileirando.")
        for isbn in pendentes:
            if isbn not in conhecidos:  # já salvo em disco não precisa ser re-processado
                fila.put(isbn)
            conhecidos.add(isbn)

    if conhecidos:
        print(f"    {len(conhecidos)} ISBN(s) conhecido(s) no acervo.\n")
    else:
        print()

    w = threading.Thread(target=worker, args=(fila, parar_evento),
                         kwargs={"on_result": _on_result}, daemon=True)
    w.start()

    try:
        while True:
            entrada = input(f"ISBN [{fila.unfinished_tasks} na fila] > ").strip()
            if not entrada:
                continue
            cmd = entrada.lower()
            if cmd in {"sair", "exit", "quit"}:
                break
            if cmd == "fila":
                print(f"  → {fila.unfinished_tasks} ISBN(s) aguardando.\n")
                continue
            if cmd == "reprocessar":
                if fila.unfinished_tasks > 0:
                    print(f"  ! Aguarde a fila esvaziar ({fila.unfinished_tasks} pendente(s)).\n")
                else:
                    _reprocessar_nao_encontrados()
                continue

            isbn = normalizar_isbn(entrada)
            if not isbn:
                print(f"  ! '{entrada}' não parece um ISBN válido (10 ou 13 dígitos).\n")
                continue

            if isbn in conhecidos:
                print(f"  ⚠  ISBN {isbn} já cadastrado ou na fila.\n")
                continue

            conhecidos.add(isbn)
            adicionar_pendente(isbn)
            fila.put(isbn)
            print(f"  → {isbn} enfileirado.\n")

    except (KeyboardInterrupt, EOFError):
        print()

    restante = fila.unfinished_tasks
    if restante:
        print(f"\nAguardando processamento de {restante} ISBN(s) na fila...")
        print("(Ctrl+C de novo abandona — ISBNs ficam em pendentes.txt)")
        try:
            fila.join()
        except KeyboardInterrupt:
            print("\nAbandonando fila. ISBNs pendentes ficam para a próxima execução.")

    parar_evento.set()
    fila.put(None)
    w.join(timeout=3)

    print(f"\nSessão encerrada. {len(conhecidos)} ISBN(s) conhecido(s).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--reprocessar", action="store_true")
    args, _ = parser.parse_known_args()
    if args.reprocessar:
        _reprocessar_nao_encontrados()
    else:
        main()
