def _formatar_livro(livro: dict, markdown: bool = True) -> str:
    titulo = livro.get("titulo") or "(sem título)"
    autores = livro.get("autores") or ""
    _ano = str(livro.get("ano") or "").strip()
    ano = f" ({_ano})" if _ano and _ano.lower() != "none" else ""
    titulo_fmt = f"**{titulo}**" if markdown else titulo
    if autores:
        return f"{titulo_fmt} — {autores}{ano}"
    return f"{titulo_fmt}{ano}"
