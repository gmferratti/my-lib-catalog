import re


def normalizar_isbn(codigo: str) -> str | None:
    """Mantém só dígitos (e 'X' final do ISBN-10). Retorna None se inválido."""
    codigo = re.sub(r"[^\dXx]", "", codigo).upper()
    if len(codigo) in (10, 13):
        return codigo
    return None
