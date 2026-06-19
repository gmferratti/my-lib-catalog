import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import catalog.reading.storage as reading_storage
from catalog.storage import carregar_todos_registros
from ui.utils import _dialog_login, _is_autenticado

st.title("📋 Lista de Leitura")

try:
    itens = reading_storage.carregar()
except Exception as _e:
    st.error(f"Erro ao carregar lista de leitura: {type(_e).__name__}: {_e}")
    st.code(f"_LEITURA_FILE = {reading_storage._LEITURA_FILE!r}\n__file__ = {reading_storage.__file__!r}")
    import traceback
    st.code(traceback.format_exc())
    st.stop()
registros = carregar_todos_registros()
livros_por_isbn = {r["isbn"]: r for r in registros}
autenticado = _is_autenticado()

with st.sidebar:
    st.page_link("pages/acervo.py", label="📚 Acervo")
    st.page_link("pages/estantes.py", label="🗂️ Estantes")
    st.page_link("pages/leitura.py", label="📋 Lista de Leitura")
    st.page_link("pages/sobre.py", label="📖 Sobre")
    st.divider()
    if autenticado:
        if st.button("🔓 Sair do modo edição", use_container_width=True):
            st.session_state["autenticado"] = False
            st.rerun()
    else:
        if st.button("🔒 Modo edição", use_container_width=True):
            _dialog_login()

lendo = [i for i in itens if i["status"] == "lendo"]
na_fila = sorted(
    [i for i in itens if i["status"] == "na_fila"], key=lambda i: i["ordem"]
)
historico = sorted(
    [i for i in itens if i["status"] in ("lido", "abandonado")],
    key=lambda i: i.get("data_conclusao") or i.get("data_abandono") or "",
    reverse=True,
)

# --- Seção 1: Lendo agora ---
st.subheader("📖 Lendo agora")
if not lendo:
    st.info("Nenhum livro em andamento. Comece um livro da fila abaixo.")
else:
    for item in lendo:
        livro = livros_por_isbn.get(item["isbn"], {})
        titulo = livro.get("titulo") or item["isbn"]
        autores = livro.get("autores", "")
        paginas_total = int(livro.get("paginas") or 0)
        progresso = item["progresso_paginas"]

        with st.container(border=True):
            col_capa, col_info = st.columns([1, 4])
            with col_capa:
                capa = livro.get("capa_url", "")
                if capa:
                    st.image(capa, width=80)
                else:
                    st.markdown("📖")
            with col_info:
                st.markdown(f"**{titulo}**")
                if autores:
                    st.caption(autores)
                if paginas_total:
                    pct = min(100, round(progresso / paginas_total * 100))
                    st.progress(
                        pct / 100,
                        text=f"{progresso} / {paginas_total} páginas ({pct}%)",
                    )
                else:
                    st.caption(f"{progresso} páginas lidas")

                if autenticado:
                    nova_pagina = st.number_input(
                        "Página atual",
                        min_value=0,
                        max_value=paginas_total if paginas_total else 9999,
                        value=progresso,
                        key=f"prog_{item['isbn']}",
                    )
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        if st.button(
                            "💾 Salvar",
                            key=f"salvar_{item['isbn']}",
                            use_container_width=True,
                        ):
                            reading_storage.atualizar_progresso(item["isbn"], nova_pagina)
                            st.rerun()
                    with col_b:
                        if st.button(
                            "✅ Lido",
                            key=f"lido_{item['isbn']}",
                            use_container_width=True,
                        ):
                            reading_storage.atualizar_status(item["isbn"], "lido")
                            st.rerun()
                    with col_c:
                        if st.button(
                            "🚫 Abandonar",
                            key=f"abandonar_{item['isbn']}",
                            use_container_width=True,
                        ):
                            reading_storage.atualizar_status(item["isbn"], "abandonado")
                            st.rerun()

# --- Seção 2: Na fila ---
st.divider()
st.subheader("📋 Na fila")
if not na_fila:
    st.info("A fila está vazia.")
else:
    for item in na_fila:
        livro = livros_por_isbn.get(item["isbn"], {})
        titulo = livro.get("titulo") or item["isbn"]
        autores = livro.get("autores", "")

        col_pos, col_capa, col_info, col_acoes = st.columns([0.5, 0.8, 4, 2.5])
        with col_pos:
            st.markdown(f"**{item['ordem']}.**")
        with col_capa:
            capa = livro.get("capa_url", "")
            if capa:
                st.image(capa, width=50)
        with col_info:
            st.markdown(f"**{titulo}**")
            if autores:
                st.caption(autores)
        with col_acoes:
            if autenticado:
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    if st.button("▲", key=f"up_{item['isbn']}", use_container_width=True):
                        reading_storage.reordenar(item["isbn"], "cima")
                        st.rerun()
                with c2:
                    if st.button("▼", key=f"down_{item['isbn']}", use_container_width=True):
                        reading_storage.reordenar(item["isbn"], "baixo")
                        st.rerun()
                with c3:
                    if st.button(
                        "▶",
                        key=f"comecar_{item['isbn']}",
                        use_container_width=True,
                        help="Começar a ler",
                    ):
                        reading_storage.atualizar_status(item["isbn"], "lendo")
                        st.rerun()
                with c4:
                    if st.button(
                        "✕",
                        key=f"remover_{item['isbn']}",
                        use_container_width=True,
                        help="Remover da fila",
                    ):
                        reading_storage.remover(item["isbn"])
                        st.rerun()

# --- Seção 3: Histórico ---
st.divider()
with st.expander(f"📚 Histórico ({len(historico)} livros)"):
    if not historico:
        st.info("Nenhum livro lido ou abandonado ainda.")
    else:
        rows = []
        for item in historico:
            livro = livros_por_isbn.get(item["isbn"], {})
            paginas_total = int(livro.get("paginas") or 0)
            data_fim = item.get("data_conclusao") or item.get("data_abandono") or "—"
            rows.append({
                "Título": livro.get("titulo") or item["isbn"],
                "Autor": livro.get("autores", "—"),
                "Status": "✅ Lido" if item["status"] == "lido" else "🚫 Abandonado",
                "Data": data_fim[:10] if data_fim != "—" else "—",
                "Progresso": (
                    f"{item['progresso_paginas']} / {paginas_total}"
                    if paginas_total
                    else str(item["progresso_paginas"])
                ),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
