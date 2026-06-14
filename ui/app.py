import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

from catalog.storage import carregar_todos_registros, reescrever_registros

st.set_page_config(
    page_title="Minha Biblioteca",
    page_icon="📚",
    layout="wide",
)

FONTE_CORES = {
    "openlibrary":   "#2e7d32",
    "googlebooks":   "#1565c0",
    "mercadolivre":  "#f9a825",
    "isbndb":        "#6a1b9a",
    "nao_encontrado":"#b71c1c",
    "manual":        "#37474f",
}

FONTE_LABELS = {
    "openlibrary":    "Open Library",
    "googlebooks":    "Google Books",
    "mercadolivre":   "Mercado Livre",
    "isbndb":         "ISBNdb",
    "nao_encontrado": "Não encontrado",
    "manual":         "Manual",
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


def _salvar_edicao(isbn: str, campos: dict) -> None:
    """Atualiza um registro no JSONL/CSV e invalida o cache."""
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

    # ── Capa atual ───────────────────────────────────────────────────────
    capa_atual = registro.get("capa_url", "")
    if capa_atual:
        col_img, col_info = st.columns([1, 3])
        with col_img:
            st.image(capa_atual, width=120)
        with col_info:
            st.markdown(f"**ISBN:** `{isbn}`")
            st.markdown(f"**Fonte original:** {registro.get('fonte', '—')}")
            st.markdown(f"**Cadastrado em:** {registro.get('data_cadastro', '—')}")
    else:
        st.markdown(f"**ISBN:** `{isbn}` &nbsp;·&nbsp; sem capa cadastrada",
                    unsafe_allow_html=True)

    st.divider()

    # ── Formulário ────────────────────────────────────────────────────────
    with st.form("form_edicao", border=False):
        titulo = st.text_input(
            "Título",
            value=registro.get("titulo", ""),
        )
        autores = st.text_input(
            "Autores",
            value=registro.get("autores", ""),
            help="Separe múltiplos autores por vírgula",
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            editora = st.text_input("Editora", value=registro.get("editora", ""))
        with c2:
            ano = st.text_input("Ano", value=registro.get("ano", ""))
        with c3:
            paginas = st.text_input("Páginas", value=str(registro.get("paginas", "")))

        c4, c5 = st.columns([1, 3])
        with c4:
            idioma = st.text_input(
                "Idioma",
                value=registro.get("idioma", ""),
                help="ISO 639-1 — pt, en, es …",
            )
        with c5:
            assuntos = st.text_input(
                "Assuntos",
                value=registro.get("assuntos", ""),
                help="Separe por vírgula",
            )

        st.markdown("**URL da capa**")
        capa_url = st.text_input(
            "URL da capa",
            value=capa_atual,
            label_visibility="collapsed",
            placeholder="https://...",
        )

        st.markdown("**Fonte**")
        opcoes_fonte = list(FONTE_LABELS.keys())
        fonte_atual = registro.get("fonte", "manual")
        fonte_idx = opcoes_fonte.index(fonte_atual) if fonte_atual in opcoes_fonte else opcoes_fonte.index("manual")
        fonte = st.selectbox(
            "Fonte",
            options=opcoes_fonte,
            index=fonte_idx,
            format_func=lambda k: FONTE_LABELS[k],
            label_visibility="collapsed",
            help="'Manual' indica que os dados foram inseridos ou corrigidos à mão",
        )

        submitted = st.form_submit_button(
            "💾 Salvar alterações",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        _salvar_edicao(isbn, {
            "titulo":   titulo.strip(),
            "autores":  autores.strip(),
            "editora":  editora.strip(),
            "ano":      ano.strip(),
            "paginas":  paginas.strip(),
            "idioma":   idioma.strip(),
            "assuntos": assuntos.strip(),
            "capa_url": capa_url.strip(),
            "fonte":    fonte,
        })
        st.toast("Registro atualizado!", icon="✅")
        st.rerun()


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
        modo_edicao = st.toggle("✏️ Modo edição", value=False,
                                help="Exibe botão de edição em cada card")

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
    manuais  = sum(1 for r in registros if r.get("fonte") == "manual")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total no acervo", total)
    c2.metric("Exibindo", len(filtrados))
    c3.metric("Com capa", com_capa)
    c4.metric("Sem metadados", sem_meta)
    c5.metric("Editados", manuais)

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
                    if r.get("ano"):
                        st.caption(f"📅 {r['ano']}")
                    st.markdown(_badge(r.get("fonte", "")), unsafe_allow_html=True)

                    if modo_edicao:
                        if st.button("✏️ Editar", key=f"edit_{r['isbn']}",
                                     use_container_width=True):
                            _dialog_editar(r)

    # ── Tabela completa ───────────────────────────────────────────────────
    with st.expander("Ver tabela completa"):
        if filtrados:
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
