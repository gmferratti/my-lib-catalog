import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from catalog.organizer import (
    ConfigEstantes,
    EstanteConfig,
    PrateleiraConfig,
    carregar_config,
    organizar,
    salvar_config,
)
from catalog.organizer.algorithm import _ordenar
from catalog.storage import carregar_todos_registros, reescrever_registros

st.set_page_config(
    page_title="Minha Biblioteca",
    page_icon="📚",
    layout="wide",
)

FONTE_CORES = {
    "openlibrary":    "#2e7d32",
    "googlebooks":    "#1565c0",
    "brasilapi":      "#f9a825",
    "isbndb":         "#6a1b9a",
    "nao_encontrado": "#b71c1c",
    "manual":         "#37474f",
}

FONTE_LABELS = {
    "openlibrary":    "Open Library",
    "googlebooks":    "Google Books",
    "brasilapi":      "BrasilAPI",
    "isbndb":         "ISBNdb",
    "nao_encontrado": "Não encontrado",
    "manual":         "Manual",
}

CAPA_FONTE_CORES = {
    "openlibrary_isbn":    "#1b5e20",
    "openlibrary_cover_i": "#2e7d32",
    "openlibrary_titulo":  "#388e3c",
    "googlebooks_isbn":    "#0d47a1",
    "googlebooks_titulo":  "#1565c0",
    "duckduckgo":          "#e65100",
    "google_cse":          "#4a148c",
    "manual":              "#37474f",
}

CAPA_FONTE_LABELS = {
    "openlibrary_isbn":    "OL ISBN",
    "openlibrary_cover_i": "OL Cover ID",
    "openlibrary_titulo":  "OL Título",
    "googlebooks_isbn":    "GB ISBN",
    "googlebooks_titulo":  "GB Título",
    "duckduckgo":          "DuckDuckGo",
    "google_cse":          "Google CSE",
    "manual":              "Manual",
}

ESTILOS = {
    "autor":   "Por autor (A → Z)",
    "assunto": "Por assunto / gênero",
    "ano":     "Por ano (mais recente primeiro)",
}

_IDIOMA_NORM = {
    "pt": "Português", "por": "Português", "pt-br": "Português", "pt-BR": "Português",
    "en": "Inglês", "eng": "Inglês",
    "es": "Espanhol", "spa": "Espanhol",
    "fr": "Francês", "fra": "Francês",
    "de": "Alemão", "deu": "Alemão", "ger": "Alemão",
    "ja": "Japonês", "jpn": "Japonês",
}


def _normalizar(s: str) -> str:
    return unicodedata.normalize("NFD", s.lower()).encode("ascii", "ignore").decode("ascii")


def _estatisticas(registros: list[dict]) -> dict:
    total = len(registros)
    total_paginas = sum(
        int(r["paginas"]) for r in registros
        if str(r.get("paginas", "")).isdigit()
    )
    com_capa = sum(1 for r in registros if r.get("capa_url"))

    contagem_idioma: dict[str, int] = {}
    for r in registros:
        cod = (r.get("idioma") or "").strip()
        if not cod:
            continue
        nome = _IDIOMA_NORM.get(cod, cod)
        contagem_idioma[nome] = contagem_idioma.get(nome, 0) + 1
    idiomas = sorted(contagem_idioma.items(), key=lambda x: -x[1])

    contagem_assunto: dict[str, int] = {}
    for r in registros:
        for termo in (r.get("assuntos") or "").split(","):
            termo = termo.strip()
            if termo:
                contagem_assunto[termo] = contagem_assunto.get(termo, 0) + 1
    assuntos = sorted(contagem_assunto.items(), key=lambda x: -x[1])[:5]

    return {
        "total": total,
        "total_paginas": total_paginas,
        "com_capa": com_capa,
        "idiomas": idiomas,
        "assuntos": assuntos,
    }


def _barra(valor: int, maximo: int, largura: int = 20) -> str:
    preenchimento = round(valor / maximo * largura) if maximo else 0
    return "█" * preenchimento


# ── Cache helpers ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=60)
def _carregar() -> list[dict]:
    return carregar_todos_registros()


@st.cache_data(ttl=None)
def _carregar_config() -> ConfigEstantes:
    return carregar_config()


# ── Utilitários de exibição ───────────────────────────────────────────────────

def _badge(fonte: str) -> str:
    cor = FONTE_CORES.get(fonte, "#78909c")
    label = FONTE_LABELS.get(fonte, fonte)
    return (
        f'<span style="background:{cor};color:white;padding:2px 8px;'
        f'border-radius:4px;font-size:0.75rem">{label}</span>'
    )


def _badge_capa(capa_fonte: str) -> str:
    if not capa_fonte or capa_fonte == "legado":
        return ""
    cor = CAPA_FONTE_CORES.get(capa_fonte, "#78909c")
    label = CAPA_FONTE_LABELS.get(capa_fonte, capa_fonte)
    return (
        f'<span style="background:{cor};color:white;padding:2px 8px;'
        f'border-radius:4px;font-size:0.75rem">{label}</span>'
    )


# ── Acervo: ficha de catálogo ─────────────────────────────────────────────────

def _render_ficha(registro: dict) -> None:
    if st.button("← Voltar ao acervo"):
        del st.session_state["isbn_selecionado"]
        st.rerun()

    st.divider()

    capa = registro.get("capa_url", "")
    col_capa, col_info = st.columns([1, 3])

    with col_capa:
        if capa:
            st.image(capa, width=200)
        else:
            st.markdown(
                '<div style="height:280px;background:#eceff1;display:flex;'
                'align-items:center;justify-content:center;font-size:4rem;'
                'border-radius:8px">📖</div>',
                unsafe_allow_html=True,
            )

    with col_info:
        st.title(registro.get("titulo") or registro.get("isbn", "—"))
        if registro.get("autores"):
            st.markdown(f"**{registro['autores']}**")

        partes = []
        if registro.get("ano"):
            partes.append(registro["ano"])
        if registro.get("editora"):
            partes.append(registro["editora"])
        if partes:
            st.caption(" · ".join(partes))

        st.divider()

        c1, c2, c3 = st.columns(3)
        c1.markdown(f"**ISBN**  \n`{registro['isbn']}`")
        idioma_nome = _IDIOMA_NORM.get(
            registro.get("idioma", ""), registro.get("idioma") or "—"
        )
        c2.markdown(f"**Idioma**  \n{idioma_nome}")
        c3.markdown(f"**Páginas**  \n{registro.get('paginas') or '—'}")

        if registro.get("assuntos"):
            st.markdown(f"**Assuntos:** {registro['assuntos']}")

        st.divider()

        st.markdown(
            f"**Fonte metadata:** {_badge(registro.get('fonte', ''))}",
            unsafe_allow_html=True,
        )
        badge_capa = _badge_capa(registro.get("capa_fonte", ""))
        if badge_capa:
            st.markdown(f"**Fonte capa:** {badge_capa}", unsafe_allow_html=True)
        st.markdown(f"**Cadastrado:** {registro.get('data_cadastro', '—')}")

        st.divider()

        estante = registro.get("estante", "")
        prateleira = registro.get("prateleira", "")
        if estante and prateleira:
            st.markdown(f"📍 **{estante} / Prateleira {prateleira}**")
        else:
            st.markdown(
                '<p style="color:#90a4ae">📍 Posição não confirmada — '
                'gere e aplique uma sugestão na aba Estantes.</p>',
                unsafe_allow_html=True,
            )

        st.divider()

        if st.button("✏️ Editar este livro", key=f"edit_ficha_{registro['isbn']}"):
            _dialog_editar(registro)


# ── Acervo: edição ────────────────────────────────────────────────────────────

def _salvar_edicao(isbn: str, campos: dict) -> None:
    registros = carregar_todos_registros()
    for r in registros:
        if r["isbn"] == isbn:
            r.update(campos)
            break
    reescrever_registros(registros)
    st.cache_data.clear()


@st.dialog("Editar livro", width="large")
def _dialog_editar(registro: dict) -> None:
    isbn = registro["isbn"]

    capa_atual = registro.get("capa_url", "")
    if capa_atual:
        col_img, col_info = st.columns([1, 3])
        with col_img:
            st.image(capa_atual, width=120)
        with col_info:
            st.markdown(f"**ISBN:** `{isbn}`")
            st.markdown(f"**Fonte original:** {registro.get('fonte', '—')}")
            capa_fonte_label = CAPA_FONTE_LABELS.get(
                registro.get("capa_fonte", ""), registro.get("capa_fonte") or "—"
            )
            st.markdown(f"**Fonte da capa:** {capa_fonte_label}")
            st.markdown(f"**Cadastrado em:** {registro.get('data_cadastro', '—')}")
    else:
        st.markdown(f"**ISBN:** `{isbn}` &nbsp;·&nbsp; sem capa cadastrada",
                    unsafe_allow_html=True)
        capa_fonte_val = registro.get("capa_fonte", "")
        if capa_fonte_val and capa_fonte_val != "legado":
            capa_fonte_label = CAPA_FONTE_LABELS.get(capa_fonte_val, capa_fonte_val)
            st.markdown(f"**Fonte da capa:** {capa_fonte_label}")

    st.divider()

    with st.form("form_edicao", border=False):
        titulo = st.text_input("Título", value=registro.get("titulo", ""))
        autores = st.text_input("Autores", value=registro.get("autores", ""),
                                help="Separe múltiplos autores por vírgula")

        c1, c2, c3 = st.columns(3)
        with c1:
            editora = st.text_input("Editora", value=registro.get("editora", ""))
        with c2:
            ano = st.text_input("Ano", value=registro.get("ano", ""))
        with c3:
            paginas = st.text_input("Páginas", value=str(registro.get("paginas", "")))

        c4, c5 = st.columns([1, 3])
        with c4:
            idioma = st.text_input("Idioma", value=registro.get("idioma", ""),
                                   help="ISO 639-1 — pt, en, es …")
        with c5:
            assuntos = st.text_input("Assuntos", value=registro.get("assuntos", ""),
                                     help="Separe por vírgula")

        st.markdown("**URL da capa**")
        capa_url = st.text_input("URL da capa", value=capa_atual,
                                 label_visibility="collapsed",
                                 placeholder="https://...")

        st.markdown("**Fonte**")
        opcoes_fonte = list(FONTE_LABELS.keys())
        fonte_atual = registro.get("fonte", "manual")
        fonte_idx = opcoes_fonte.index(fonte_atual) if fonte_atual in opcoes_fonte else opcoes_fonte.index("manual")
        fonte = st.selectbox("Fonte", options=opcoes_fonte, index=fonte_idx,
                             format_func=lambda k: FONTE_LABELS[k],
                             label_visibility="collapsed")

        submitted = st.form_submit_button("💾 Salvar alterações", type="primary",
                                          use_container_width=True)

    if submitted:
        _salvar_edicao(isbn, {
            "titulo": titulo.strip(), "autores": autores.strip(),
            "editora": editora.strip(), "ano": ano.strip(),
            "paginas": paginas.strip(), "idioma": idioma.strip(),
            "assuntos": assuntos.strip(), "capa_url": capa_url.strip(),
            "fonte": fonte,
        })
        st.toast("Registro atualizado!", icon="✅")
        st.rerun()


# ── Tab: Acervo ───────────────────────────────────────────────────────────────

def _render_acervo() -> None:
    registros = _carregar()

    isbn_sel = st.session_state.get("isbn_selecionado")
    if isbn_sel:
        r = next((r for r in registros if r["isbn"] == isbn_sel), None)
        if r:
            _render_ficha(r)
            return
        del st.session_state["isbn_selecionado"]

    busca = st.text_input(
        "",
        placeholder="🔍 Buscar por título ou autor...",
        label_visibility="collapsed",
    )

    with st.sidebar:
        st.header("Filtros")
        idiomas = sorted({r.get("idioma", "") for r in registros if r.get("idioma")})
        idioma_sel = st.selectbox("Idioma", ["Todos"] + idiomas)
        fontes_disp = sorted({r.get("fonte", "") for r in registros if r.get("fonte")})
        fonte_sel = st.selectbox("Fonte", ["Todas"] + fontes_disp)
        ocultar_sem_meta = st.checkbox("Ocultar sem metadados", value=False)
        st.divider()
        st.subheader("Ordenação")
        ESTILOS_ACERVO = {"cadastro": "Ordem de cadastro"} | ESTILOS
        ordem_sel = st.selectbox(
            "Ordenar por",
            options=list(ESTILOS_ACERVO.keys()),
            format_func=lambda k: ESTILOS_ACERVO[k],
            label_visibility="collapsed",
        )
        st.divider()
        modo_edicao = st.toggle("✏️ Modo edição", value=False,
                                help="Exibe botão de edição em cada card")
        st.divider()
        if st.button("🔄 Recarregar dados"):
            st.cache_data.clear()
            st.rerun()

    filtrados = registros
    if ocultar_sem_meta:
        filtrados = [r for r in filtrados if r.get("fonte") != "nao_encontrado"]
    if busca:
        q = _normalizar(busca)
        filtrados = [r for r in filtrados
                     if q in _normalizar(r.get("titulo", ""))
                     or q in _normalizar(r.get("autores", ""))]
    if idioma_sel != "Todos":
        filtrados = [r for r in filtrados if r.get("idioma") == idioma_sel]
    if fonte_sel != "Todas":
        filtrados = [r for r in filtrados if r.get("fonte") == fonte_sel]
    if ordem_sel != "cadastro":
        filtrados = _ordenar(filtrados, ordem_sel)

    stats = _estatisticas(registros)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Total no acervo", stats["total"])
    m2.metric("Exibindo", len(filtrados))
    m3.metric("Total de páginas", f"{stats['total_paginas']:,}".replace(",", "."))
    m4.metric("Com capa", stats["com_capa"])
    m5.metric("Sem metadados", sum(1 for r in registros if r.get("fonte") == "nao_encontrado"))

    st.divider()

    if not filtrados:
        st.info("Nenhum livro encontrado com os filtros aplicados.")
    else:
        st.markdown("""<style>
div[data-testid="column"] button[kind="secondary"] {
    background: none !important;
    border: none !important;
    box-shadow: none !important;
    text-align: left !important;
    font-weight: 600 !important;
    padding: 2px 0 !important;
    cursor: pointer !important;
    line-height: 1.4 !important;
    white-space: normal !important;
    color: rgb(49,51,63) !important;
    width: 100% !important;
}
div[data-testid="column"] button[kind="secondary"]:hover {
    color: #1565c0 !important;
    background: none !important;
    box-shadow: none !important;
}
</style>""", unsafe_allow_html=True)

        COLUNAS = 4
        for i in range(0, len(filtrados), COLUNAS):
            cols = st.columns(COLUNAS)
            for j, col in enumerate(cols):
                idx = i + j
                if idx >= len(filtrados):
                    break
                r = filtrados[idx]
                with col:
                    capa = r.get("capa_url", "")
                    titulo = r.get("titulo") or r.get("isbn", "—")
                    if capa:
                        st.markdown(
                            f'<a href="#" onclick="return false" style="display:block;cursor:pointer">'
                            f'<img src="{capa}" style="width:100%;border-radius:4px;'
                            f'transition:box-shadow 0.15s" /></a>',
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            '<div style="height:160px;background:#eceff1;display:flex;'
                            'align-items:center;justify-content:center;font-size:3rem;'
                            'border-radius:4px;cursor:pointer">📖</div>',
                            unsafe_allow_html=True,
                        )
                    if st.button(titulo, key=f"ficha_{r['isbn']}",
                                 use_container_width=True):
                        st.session_state["isbn_selecionado"] = r["isbn"]
                        st.rerun()
                    if r.get("autores"):
                        st.caption(r["autores"])
                    if r.get("ano"):
                        st.caption(f"📅 {r['ano']}")
                    st.markdown(_badge(r.get("fonte", "")), unsafe_allow_html=True)
                    badge_capa = _badge_capa(r.get("capa_fonte", ""))
                    if badge_capa:
                        st.markdown(badge_capa, unsafe_allow_html=True)
                    if modo_edicao:
                        if st.button("✏️ Editar", key=f"edit_{r['isbn']}",
                                     type="primary",
                                     use_container_width=True):
                            _dialog_editar(r)

    with st.expander("Ver tabela completa"):
        if filtrados:
            rows = [{k: str(v) if not isinstance(v, str) else v for k, v in r.items()}
                    for r in filtrados]
            st.dataframe(rows, width="stretch",
                         column_order=["isbn", "titulo", "autores", "editora", "ano",
                                       "paginas", "idioma", "assuntos", "capa_fonte", "fonte",
                                       "data_cadastro", "capa_url"])
        else:
            st.write("Sem registros.")


# ── Tab: Estantes ─────────────────────────────────────────────────────────────

def _gerar_txt(
    resultados: list,
    sem_lugar: list[dict],
    estilo: str,
) -> str:
    linhas = [f"Organização por: {ESTILOS[estilo]}", "=" * 60, ""]
    for r in resultados:
        ocupacao = len(r.livros)
        linhas.append(f"🗄️  {r.estante} — {r.prateleira}  |  {r.label_sugerido}"
                      f"  |  {ocupacao}/{r.capacidade} livros")
        linhas.append("-" * 60)
        for livro in r.livros:
            titulo = livro.get("titulo") or "(sem título)"
            autores = livro.get("autores") or "(sem autor)"
            ano = livro.get("ano") or "—"
            linhas.append(f"  {autores} — {titulo} ({ano})")
        linhas.append("")
    if sem_lugar:
        linhas += [f"⚠️  {len(sem_lugar)} livros sem lugar:", "-" * 60]
        for livro in sem_lugar:
            titulo = livro.get("titulo") or livro.get("isbn", "—")
            linhas.append(f"  {titulo}")
    return "\n".join(linhas)


def _render_estantes() -> None:
    livros = _carregar()

    # ── Configuração ──────────────────────────────────────────────────────
    with st.expander("⚙️ Configurar estantes", expanded=not bool(_carregar_config().estantes)):
        cfg_atual = _carregar_config()

        with st.form("form_config_estantes"):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                num_estantes = st.number_input(
                    "Número de estantes", min_value=1, max_value=20,
                    value=max(1, len(cfg_atual.estantes)),
                    step=1,
                )
            with c2:
                prat_por_estante = st.number_input(
                    "Prateleiras por estante", min_value=1, max_value=30,
                    value=max(1, len(cfg_atual.estantes[0].prateleiras)
                              if cfg_atual.estantes else 4),
                    step=1,
                )
            with c3:
                largura_cm = st.number_input(
                    "Largura de cada prateleira (cm)", min_value=10.0, max_value=300.0,
                    value=float(cfg_atual.estantes[0].prateleiras[0].largura_cm
                                if cfg_atual.estantes and cfg_atual.estantes[0].prateleiras
                                else 80.0),
                    step=5.0,
                )
            with c4:
                espessura_cm = st.number_input(
                    "Espessura média dos livros (cm)", min_value=0.5, max_value=10.0,
                    value=float(cfg_atual.espessura_media_cm),
                    step=0.5,
                    help="Espessura média da lombada. Padrão: 2,5 cm.",
                )

            # Prévia da capacidade
            cap_prat = max(1, int(largura_cm / espessura_cm))
            cap_total = int(num_estantes) * int(prat_por_estante) * cap_prat
            num_prat_total = int(num_estantes) * int(prat_por_estante)
            st.caption(
                f"Capacidade estimada: **{cap_prat} livros/prateleira** · "
                f"**{num_prat_total} prateleiras** · "
                f"**{cap_total} livros no total**"
            )

            salvar = st.form_submit_button("💾 Salvar configuração", type="primary")

        if salvar:
            letras = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            nova_cfg = ConfigEstantes(
                espessura_media_cm=float(espessura_cm),
                estantes=[
                    EstanteConfig(
                        nome=f"Estante {i + 1}",
                        prateleiras=[
                            PrateleiraConfig(
                                nome=letras[j % 26] if j < 26 else f"{letras[(j // 26) - 1]}{letras[j % 26]}",
                                largura_cm=float(largura_cm),
                            )
                            for j in range(int(prat_por_estante))
                        ],
                    )
                    for i in range(int(num_estantes))
                ],
            )
            salvar_config(nova_cfg)
            st.cache_data.clear()
            st.toast("Configuração salva!", icon="✅")
            st.rerun()

    cfg = _carregar_config()
    if not cfg.estantes:
        st.info("Configure as suas estantes acima para gerar uma sugestão de organização.")
        return

    # ── Gerar sugestão ────────────────────────────────────────────────────
    st.divider()
    col_estilo, col_btn = st.columns([3, 1])
    with col_estilo:
        estilo = st.selectbox(
            "Estilo de organização",
            options=list(ESTILOS.keys()),
            format_func=lambda k: ESTILOS[k],
            label_visibility="collapsed",
        )
    with col_btn:
        gerar = st.button("🗂️ Gerar sugestão", type="primary", use_container_width=True)

    if "organizer_resultado" not in st.session_state or gerar:
        if livros:
            res, sem_lugar = organizar(livros, cfg, estilo)
            st.session_state["organizer_resultado"] = res
            st.session_state["organizer_sem_lugar"] = sem_lugar
            st.session_state["organizer_estilo"] = estilo
        else:
            st.warning("Nenhum livro no acervo para organizar.")
            return

    resultado: list = st.session_state.get("organizer_resultado", [])
    sem_lugar: list = st.session_state.get("organizer_sem_lugar", [])
    estilo_usado: str = st.session_state.get("organizer_estilo", estilo)

    if not resultado:
        return

    # ── Métricas ──────────────────────────────────────────────────────────
    total_livros = len(livros)
    total_prat = len(resultado)
    cap_total = sum(r.capacidade for r in resultado)
    distribuidos = sum(len(r.livros) for r in resultado)
    ocupacao_pct = round(distribuidos / cap_total * 100) if cap_total else 0

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("Livros no acervo", total_livros)
    m2.metric("Prateleiras", total_prat)
    m3.metric("Capacidade total", cap_total)
    m4.metric("Distribuídos", distribuidos)
    m5.metric("Ocupação", f"{ocupacao_pct}%")

    if sem_lugar:
        prat_extras = -(-len(sem_lugar) // (cap_total // total_prat)) if total_prat else "?"
        st.warning(
            f"⚠️ **{len(sem_lugar)} livros não cabem** nas prateleiras configuradas. "
            f"Considere adicionar ~{prat_extras} prateleira(s) ou aumentar a largura."
        )

    st.divider()

    # ── Download ──────────────────────────────────────────────────────────
    txt = _gerar_txt(resultado, sem_lugar, estilo_usado)
    col_dl, col_ap = st.columns([2, 3])
    with col_dl:
        st.download_button(
            "📥 Baixar sugestão (.txt)",
            data=txt.encode("utf-8"),
            file_name=f"organizacao_{estilo_usado}.txt",
            mime="text/plain",
        )
    with col_ap:
        if st.button("✅ Aplicar esta sugestão como posição real", type="primary",
                     use_container_width=True):
            todos = carregar_todos_registros()
            mapa: dict[str, tuple[str, str]] = {}
            for prat in resultado:
                for livro in prat.livros:
                    mapa[livro["isbn"]] = (prat.estante, prat.prateleira)
            for r in todos:
                estante_val, prat_val = mapa.get(r["isbn"], ("", ""))
                r["estante"] = estante_val
                r["prateleira"] = prat_val
            reescrever_registros(todos)
            st.cache_data.clear()
            st.toast("Posições aplicadas ao acervo!", icon="✅")
            st.rerun()

    # ── Resultado por estante → prateleira ────────────────────────────────
    estante_atual = None
    for r in resultado:
        if r.estante != estante_atual:
            estante_atual = r.estante
            st.subheader(f"🗄️ {r.estante}")

        ocupacao = len(r.livros)
        pct = ocupacao / r.capacidade if r.capacidade else 0
        header = (
            f"**{r.prateleira}** &nbsp;·&nbsp; "
            f"*{r.label_sugerido}* &nbsp;·&nbsp; "
            f"{ocupacao}/{r.capacidade} livros"
        )
        with st.expander(header, expanded=False):
            st.progress(pct)
            if not r.livros:
                st.caption("(vazia)")
            else:
                for livro in r.livros:
                    titulo = livro.get("titulo") or "(sem título)"
                    autores = livro.get("autores") or "(sem autor)"
                    ano = f" ({livro['ano']})" if livro.get("ano") else ""
                    st.markdown(f"- {autores} — **{titulo}**{ano}")

    if sem_lugar:
        st.subheader("📦 Livros sem lugar")
        for livro in sem_lugar:
            titulo = livro.get("titulo") or livro.get("isbn", "—")
            autores = livro.get("autores", "")
            st.markdown(f"- {autores} — **{titulo}**" if autores else f"- **{titulo}**")


# ── Tab: Sobre ────────────────────────────────────────────────────────────────

def _render_sobre() -> None:
    st.header("Sobre o My Lib Catalog")

    col, _ = st.columns([2, 1])
    with col:
        st.markdown("""
My Lib Catalog nasceu de uma necessidade muito simples: Gustavo Ferratti, um apaixonado
por livros que mora em Araraquara, interior de São Paulo, precisava de uma forma de
organizar e consultar o próprio acervo pessoal de livros que crescia rapidamente.

O projeto foi construído inteiramente por ele (AI-assisted) com muito amor e carinho,
de forma gratuita, de bookworm para bookworm. Nada de algoritmos de recomendação, nada
de dados sendo vendidos. Só você, seus livros, uma interface que respeita o seu tempo
e o bom e velho open source.

**Como funciona:** você escaneia o código de barras do livro com um leitor de código de
barras pela CLI (rodar comando `make run` para entrar no loop principal); o sistema busca
os metadados automaticamente a partir do ISBN em múltiplas fontes (Open Library,
Google Books, BrasilAPI, ISBNdb) e organiza tudo para você consultar por autor, ano,
idioma, etc. Se algo não vier certo, há a possibilidade de ajuste manual.

**Organização de estantes:** a funcionalidade de organização física das estantes está em
desenvolvimento. Em breve você poderá distribuir seus livros pelas prateleiras de
forma otimizada.
""")


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    st.title("📚 Minha Biblioteca")
    tab_acervo, tab_estantes, tab_sobre = st.tabs(["📚 Acervo", "🗂️ Estantes", "📖 Sobre"])

    with tab_acervo:
        _render_acervo()

    with tab_estantes:
        _render_estantes()

    with tab_sobre:
        _render_sobre()


if __name__ == "__main__":
    main()
else:
    main()
