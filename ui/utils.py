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
from catalog.storage import carregar_todos_registros, reescrever_registros

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
    "cs": "Tcheco", "ces": "Tcheco", "cze": "Tcheco",
    "it": "Italiano", "ita": "Italiano",
    "ru": "Russo", "rus": "Russo",
    "zh": "Chinês", "chi": "Chinês", "zho": "Chinês",
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


@st.cache_data(ttl=60)
def _carregar() -> list[dict]:
    return carregar_todos_registros()


@st.cache_data(ttl=None)
def _carregar_config() -> ConfigEstantes:
    return carregar_config()


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


def _is_autenticado() -> bool:
    return st.session_state.get("autenticado", False)


@st.dialog("🔒 Acesso restrito", width="small")
def _dialog_login() -> None:
    st.markdown("Digite a senha para habilitar o modo edição.")
    senha = st.text_input("Senha", type="password", label_visibility="collapsed")
    if st.button("Entrar", type="primary", use_container_width=True):
        senha_correta = st.secrets.get("EDIT_PASSWORD", "")
        if senha and senha == senha_correta:
            st.session_state["autenticado"] = True
            st.rerun()
        else:
            st.error("Senha incorreta.")


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
