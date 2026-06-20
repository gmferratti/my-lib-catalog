import re

_ROMAN_TO_INT = {
    "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
    "VI": 6, "VII": 7, "VIII": 8, "IX": 9, "X": 10,
}

# "Vol. 4", "VOL.04", "vol 3", "volume 2", "Vol.I", "Tomo 2", "Parte III"
_KW_RE = re.compile(
    r'\b(vol(?:ume)?|tomo|parte)\b[\s.]*([IVX]+|\d+)\b',
    re.IGNORECASE,
)

# "/ V. 03" ou "V.3" no fim do título
_V_END_RE = re.compile(
    r'[/\s]+V\.?\s*(\d+)\s*$',
    re.IGNORECASE,
)


def _to_int(s: str) -> int | None:
    s = s.strip().upper()
    if s.isdigit():
        return int(s)
    return _ROMAN_TO_INT.get(s)


def detectar_serie(titulo: str) -> dict | None:
    """
    Tenta extrair série, volume e subtítulo de um título bruto.
    Retorna {"serie": str, "volume": int, "subtitulo": str} ou None.
    """
    if not titulo:
        return None

    # Padrão 1: volume no fim como "/ V. 03"
    m = _V_END_RE.search(titulo)
    if m:
        num = int(m.group(1))
        before = titulo[:m.start()].strip()
        parts = re.split(r'\s+-\s+', before, maxsplit=1)
        serie = re.sub(r'[\s\-/:,]+$', '', parts[0]).strip()
        sub = parts[1].strip() if len(parts) > 1 else ""
        return {"serie": serie, "volume": num, "subtitulo": sub}

    # Padrão 2: palavra-chave de volume no meio/fim
    m = _KW_RE.search(titulo)
    if m:
        num = _to_int(m.group(2))
        if num is None:
            return None
        before = titulo[:m.start()]
        after = titulo[m.end():]
        serie = re.sub(r'[\s\-/:,]+$', '', before).strip()
        sub = re.sub(r'^[\s\-:,]+', '', after).strip()
        return {"serie": serie, "volume": num, "subtitulo": sub}

    return None


def compor_titulo(serie: str, volume: int, subtitulo: str = "") -> str:
    """Compõe o título canônico: 'Série — Vol. N: Subtítulo'."""
    base = f"{serie} — Vol. {volume}"
    if subtitulo:
        return f"{base}: {subtitulo}"
    return base
