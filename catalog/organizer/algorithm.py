from .models import ConfigEstantes, PrateleiraResultado


def capacidade_prateleira(largura_cm: float, espessura_cm: float) -> int:
    """Número de livros que cabem numa prateleira dadas as dimensões."""
    if espessura_cm <= 0:
        return 1
    return max(1, int(largura_cm / espessura_cm))


# ── Extratores de chave ──────────────────────────────────────────────────────

def _sobrenome(autores: str) -> str:
    """Último sobrenome do primeiro autor. Desconhecido → 'ZZZZ'."""
    if not autores or not autores.strip():
        return "ZZZZ"
    primeiro = autores.split(",")[0].strip()
    partes = primeiro.split()
    return partes[-1].upper() if partes else "ZZZZ"


def _assunto_principal(assuntos: str) -> str:
    if not assuntos or not assuntos.strip():
        return "ZZZZ"
    return assuntos.split(",")[0].strip().upper()


def _ano_key(registro: dict) -> int:
    """Ano como int negativo (mais recente primeiro). Desconhecido → 0."""
    try:
        return -int(str(registro.get("ano", "") or "").strip()[:4])
    except (ValueError, TypeError):
        return 0


def _eh_desconhecido(registro: dict) -> bool:
    return registro.get("fonte") == "nao_encontrado"


# ── Ordenação ────────────────────────────────────────────────────────────────

def _ordenar(livros: list[dict], estilo: str) -> list[dict]:
    conhecidos = [r for r in livros if not _eh_desconhecido(r)]
    desconhecidos = [r for r in livros if _eh_desconhecido(r)]

    def _nome_completo(r: dict) -> str:
        return (r.get("autores") or "").upper()

    if estilo == "autor":
        conhecidos.sort(key=lambda r: (
            _sobrenome(r.get("autores", "")),
            _nome_completo(r),
        ))
    elif estilo == "assunto":
        conhecidos.sort(key=lambda r: (
            _assunto_principal(r.get("assuntos", "")),
            _sobrenome(r.get("autores", "")),
            _nome_completo(r),
        ))
    elif estilo == "ano":
        conhecidos.sort(key=_ano_key)

    return conhecidos + desconhecidos


# ── Labels ────────────────────────────────────────────────────────────────────

def _label(livros: list[dict], estilo: str) -> str:
    if not livros:
        return "(vazia)"
    if estilo == "autor":
        primeiro = _sobrenome(livros[0].get("autores", ""))[:3]
        ultimo = _sobrenome(livros[-1].get("autores", ""))[:3]
        return f"{primeiro} – {ultimo}" if primeiro != "ZZZ" else "(sem autor)"
    if estilo == "assunto":
        assuntos = []
        vistos: set[str] = set()
        for r in livros:
            a = _assunto_principal(r.get("assuntos", ""))
            if a != "ZZZZ" and a not in vistos:
                assuntos.append(a.title())
                vistos.add(a)
            if len(assuntos) == 2:
                break
        return ", ".join(assuntos) if assuntos else "(sem assunto)"
    if estilo == "ano":
        anos = [
            int(str(r.get("ano", "") or "").strip()[:4])
            for r in livros
            if str(r.get("ano", "") or "").strip()[:4].isdigit()
        ]
        if anos:
            return f"{min(anos)} – {max(anos)}"
        return "(sem ano)"
    return ""


# ── Função principal ─────────────────────────────────────────────────────────

def organizar(
    livros: list[dict],
    config: ConfigEstantes,
    estilo: str,
) -> tuple[list[PrateleiraResultado], list[dict]]:
    """
    Distribui os livros nas prateleiras segundo o estilo de organização.

    Retorna (resultados_por_prateleira, livros_sem_lugar).
    `livros_sem_lugar` é não-vazio quando o acervo excede a capacidade total.
    """
    ordenados = _ordenar(livros, estilo)

    # Monta lista de prateleiras com suas capacidades
    slots: list[tuple[str, str, int]] = []  # (nome_estante, nome_prat, capacidade)
    for estante in config.estantes:
        for prat in estante.prateleiras:
            cap = capacidade_prateleira(prat.largura_cm, config.espessura_media_cm)
            slots.append((estante.nome, prat.nome, cap))

    resultados: list[PrateleiraResultado] = []
    idx = 0
    for nome_est, nome_prat, cap in slots:
        fatia = ordenados[idx: idx + cap]
        idx += cap
        resultados.append(PrateleiraResultado(
            estante=nome_est,
            prateleira=nome_prat,
            capacidade=cap,
            livros=fatia,
            label_sugerido=_label(fatia, estilo),
        ))

    livros_sem_lugar = ordenados[idx:]
    return resultados, livros_sem_lugar
