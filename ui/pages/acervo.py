import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from catalog.organizer.algorithm import _ordenar
from ui.utils import (
    ESTILOS,
    _badge,
    _badge_capa,
    _carregar,
    _dialog_editar,
    _dialog_login,
    _estatisticas,
    _is_autenticado,
    _normalizar,
)

st.title("📚 Minha Biblioteca")

registros = _carregar()

busca = st.text_input(
    "Busca",
    placeholder="🔍 Buscar por título ou autor...",
    label_visibility="collapsed",
)

with st.sidebar:
    st.page_link("pages/acervo.py", label="📚 Acervo")
    st.page_link("pages/estantes.py", label="🗂️ Estantes")
    st.page_link("pages/leitura.py", label="📋 Lista de Leitura")
    st.page_link("pages/sobre.py", label="📖 Sobre")
    st.divider()
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
    if _is_autenticado():
        modo_edicao = st.toggle("✏️ Modo edição", value=False,
                                help="Exibe botão de edição em cada card")
        if st.button("🔓 Sair do modo edição", use_container_width=True):
            st.session_state["autenticado"] = False
            st.rerun()
    else:
        modo_edicao = False
        if st.button("🔒 Modo edição", use_container_width=True,
                     help="Requer senha para editar o acervo"):
            _dialog_login()
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
                        f'<img src="{capa}" style="width:100%;height:160px;object-fit:cover;'
                        f'border-radius:4px;transition:box-shadow 0.15s" /></a>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div style="height:160px;background:#eceff1;display:flex;'
                        'align-items:center;justify-content:center;font-size:3rem;'
                        'border-radius:4px;cursor:pointer">📖</div>',
                        unsafe_allow_html=True,
                    )
                if st.button(titulo, key=f"ficha_{r['isbn']}", use_container_width=True):
                    st.session_state["isbn_ficha"] = r["isbn"]
                    st.switch_page("pages/ficha.py")
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
