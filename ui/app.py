import sys
from pathlib import Path

# Garante que o pacote catalog seja encontrado ao rodar via "streamlit run ui/app.py"
sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from catalog.storage import carregar_todos_registros

st.set_page_config(
    page_title="Minha Biblioteca",
    page_icon="📚",
    layout="wide",
)

FONTE_CORES = {
    "openlibrary": "#2e7d32",
    "googlebooks": "#1565c0",
    "mercadolivre": "#f9a825",
    "isbndb": "#6a1b9a",
    "nao_encontrado": "#b71c1c",
}

FONTE_LABELS = {
    "openlibrary": "Open Library",
    "googlebooks": "Google Books",
    "mercadolivre": "Mercado Livre",
    "isbndb": "ISBNdb",
    "nao_encontrado": "Não encontrado",
}


@st.cache_data(ttl=60)
def _carregar() -> list[dict]:
    return carregar_todos_registros()


def _badge(fonte: str) -> str:
    cor = FONTE_CORES.get(fonte, "#78909c")
    label = FONTE_LABELS.get(fonte, fonte)
    return (
        f'<span style="background:{cor};color:white;padding:2px 8px;'
        f'border-radius:4px;font-size:0.75rem">{label}</span>'
    )


def main():
    st.title("📚 Minha Biblioteca")

    registros = _carregar()

    # ── Sidebar ──────────────────────────────────────────────────────────
    with st.sidebar:
        st.header("Filtros")

        busca = st.text_input("Título ou autor", placeholder="ex: Tolkien")

        idiomas = sorted({r.get("idioma", "") for r in registros if r.get("idioma")})
        idioma_sel = st.selectbox("Idioma", ["Todos"] + idiomas)

        fontes_disp = sorted({r.get("fonte", "") for r in registros if r.get("fonte")})
        fonte_sel = st.selectbox("Fonte", ["Todas"] + fontes_disp)

        ocultar_sem_meta = st.checkbox("Ocultar sem metadados", value=False)

        st.divider()
        if st.button("🔄 Recarregar dados"):
            st.cache_data.clear()
            st.rerun()

    # ── Filtragem ─────────────────────────────────────────────────────────
    filtrados = registros

    if ocultar_sem_meta:
        filtrados = [r for r in filtrados if r.get("fonte") != "nao_encontrado"]

    if busca:
        q = busca.lower()
        filtrados = [
            r for r in filtrados
            if q in r.get("titulo", "").lower() or q in r.get("autores", "").lower()
        ]

    if idioma_sel != "Todos":
        filtrados = [r for r in filtrados if r.get("idioma") == idioma_sel]

    if fonte_sel != "Todas":
        filtrados = [r for r in filtrados if r.get("fonte") == fonte_sel]

    # ── Métricas ──────────────────────────────────────────────────────────
    total = len(registros)
    com_capa = sum(1 for r in registros if r.get("capa_url"))
    sem_meta = sum(1 for r in registros if r.get("fonte") == "nao_encontrado")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total no acervo", total)
    col2.metric("Exibindo", len(filtrados))
    col3.metric("Com capa", com_capa)
    col4.metric("Sem metadados", sem_meta)

    st.divider()

    # ── Grid de cards ─────────────────────────────────────────────────────
    if not filtrados:
        st.info("Nenhum livro encontrado com os filtros aplicados.")
    else:
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
                    if capa:
                        st.image(capa, width="stretch")
                    else:
                        st.markdown(
                            '<div style="height:160px;background:#eceff1;display:flex;'
                            'align-items:center;justify-content:center;font-size:3rem;'
                            'border-radius:4px">📖</div>',
                            unsafe_allow_html=True,
                        )
                    titulo = r.get("titulo") or r.get("isbn", "—")
                    st.markdown(f"**{titulo}**")
                    if r.get("autores"):
                        st.caption(r["autores"])
                    ano = r.get("ano", "")
                    if ano:
                        st.caption(f"📅 {ano}")
                    st.markdown(_badge(r.get("fonte", "")), unsafe_allow_html=True)
                    st.write("")

    # ── Tabela completa ───────────────────────────────────────────────────
    with st.expander("Ver tabela completa"):
        if filtrados:
            # Normaliza tipos mistos antes de passar pro dataframe (ex: paginas int vs str)
            rows = [{k: str(v) if not isinstance(v, str) else v for k, v in r.items()}
                    for r in filtrados]
            st.dataframe(
                rows,
                width="stretch",
                column_order=[
                    "isbn", "titulo", "autores", "editora", "ano",
                    "paginas", "idioma", "assuntos", "fonte", "data_cadastro", "capa_url",
                ],
            )
        else:
            st.write("Sem registros.")


if __name__ == "__main__":
    main()
else:
    main()
