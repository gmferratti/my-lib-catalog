import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from ui.utils import (
    _IDIOMA_NORM,
    _badge,
    _badge_capa,
    _carregar,
    _dialog_editar,
    _dialog_login,
    _is_autenticado,
)

isbn = st.session_state.get("isbn_ficha")
if not isbn:
    st.switch_page("pages/acervo.py")
    st.stop()

registros = _carregar()
registro = next((r for r in registros if r["isbn"] == isbn), None)
if not registro:
    st.switch_page("pages/acervo.py")
    st.stop()

if st.button("← Voltar ao acervo"):
    st.switch_page("pages/acervo.py")

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

    if _is_autenticado():
        if st.button("✏️ Editar este livro", key=f"edit_ficha_{registro['isbn']}",
                     type="primary"):
            _dialog_editar(registro)
    else:
        if st.button("🔒 Editar este livro", key=f"edit_ficha_{registro['isbn']}",
                     help="Requer senha para editar"):
            _dialog_login()
