import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import catalog.reading.storage as reading_storage
import catalog.notas as notas
from ui.utils import (
    _IDIOMA_NORM,
    _badge,
    _badge_capa,
    _badge_etiqueta,
    _carregar,
    _dialog_editar,
    _dialog_login,
    _dialog_notas,
    _injetar_tema,
    _is_autenticado,
    _session_bar,
    _sidebar_tema,
)

_injetar_tema()
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
            '<div class="capa-placeholder" style="height:280px;display:flex;'
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

    etiquetas_lista = [
        e.strip()
        for e in (registro.get("etiquetas") or "").split(",")
        if e.strip()
    ]
    if etiquetas_lista:
        badges_html = " ".join(_badge_etiqueta(e) for e in etiquetas_lista)
        st.markdown(f"**Etiquetas:** {badges_html}", unsafe_allow_html=True)

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
    st.markdown("**📋 Lista de Leitura**")

    itens_leitura = reading_storage.carregar()
    item_leitura = next((i for i in itens_leitura if i["isbn"] == isbn), None)
    paginas_total = int(registro.get("paginas") or 0)

    STATUS_LABELS = {
        "na_fila": "📋 Na fila",
        "lendo": "📖 Lendo",
        "lido": "✅ Lido",
        "abandonado": "🚫 Abandonado",
    }

    if item_leitura is None:
        if _is_autenticado():
            if st.button("➕ Adicionar à fila de leitura", key=f"add_leitura_{isbn}"):
                reading_storage.adicionar(isbn)
                st.rerun()
        else:
            st.caption("🔒 Faça login para adicionar à lista de leitura.")
    else:
        st.markdown(
            f"Status: **{STATUS_LABELS.get(item_leitura['status'], item_leitura['status'])}**"
        )
        progresso = item_leitura["progresso_paginas"]
        if paginas_total:
            pct = min(100, round(progresso / paginas_total * 100))
            st.progress(
                pct / 100,
                text=f"{progresso} / {paginas_total} páginas ({pct}%)",
            )
        elif progresso:
            st.caption(f"{progresso} páginas lidas")

        if _is_autenticado() and item_leitura["status"] == "lendo":
            nova_pagina = st.number_input(
                "Página atual",
                min_value=0,
                max_value=paginas_total if paginas_total else 9999,
                value=progresso,
                key=f"prog_ficha_{isbn}",
            )
            if st.button("💾 Salvar progresso", key=f"salvar_ficha_{isbn}"):
                reading_storage.atualizar_progresso(isbn, nova_pagina)
                st.rerun()

    st.divider()
    st.markdown("**📝 Anotações**")

    nota = notas.carregar(isbn)

    if nota and (nota.get("anotacao") or nota.get("links")):
        if nota.get("anotacao"):
            st.markdown(nota["anotacao"])
        for link in nota.get("links", []):
            rotulo = link.get("rotulo") or link["url"][:60]
            st.link_button(rotulo, link["url"])
    else:
        st.caption("Nenhuma anotação ainda.")

    if _is_autenticado():
        if st.button("✏️ Editar anotações", key=f"btn_notas_{isbn}"):
            _dialog_notas(isbn, nota)
    else:
        st.caption("🔒 Faça login para adicionar anotações.")

    st.divider()

    if _is_autenticado():
        if st.button("✏️ Editar este livro", key=f"edit_ficha_{registro['isbn']}",
                     type="primary"):
            _dialog_editar(registro)
    else:
        if st.button("🔒 Editar este livro", key=f"edit_ficha_{registro['isbn']}",
                     help="Requer senha para editar"):
            _dialog_login()

_session_bar()
_sidebar_tema()
