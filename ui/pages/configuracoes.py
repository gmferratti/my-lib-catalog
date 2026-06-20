import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
from catalog.metadata.api import (
    FONTES_CAPAS,
    FONTES_METADADOS,
    carregar_config_apis,
    salvar_config_apis,
)
from ui.utils import _injetar_tema, _session_bar, _sidebar_tema

_injetar_tema()

if st.button("← Voltar ao acervo"):
    st.switch_page("pages/acervo.py")

st.title("⚙️ Configurações de APIs")
st.caption(
    "Selecione quais fontes serão consultadas ao cadastrar livros e buscar capas. "
    "Fontes desabilitadas são ignoradas na cascata — útil para poupar cota ou acelerar buscas."
)

cfg = carregar_config_apis()
ativas_meta  = set(cfg.get("metadados", []))
ativas_capas = set(cfg.get("capas",     []))

with st.form("form_config_apis"):
    st.subheader("📖 Metadados")
    st.caption("Ordem de consulta: BrasilAPI → Open Library → Google Books → ISBNdb → OL Edição (ISBNs brasileiros consultam BrasilAPI primeiro).")

    sel_meta: dict[str, bool] = {}
    for fonte_id, label, desc in FONTES_METADADOS:
        col_chk, col_desc = st.columns([1, 4])
        with col_chk:
            sel_meta[fonte_id] = st.checkbox(
                label, value=fonte_id in ativas_meta, key=f"meta_{fonte_id}"
            )
        with col_desc:
            st.caption(desc)

    st.divider()
    st.subheader("🖼️ Capas")
    st.caption("Tentadas em ordem até encontrar uma imagem válida.")

    sel_capas: dict[str, bool] = {}
    for fonte_id, label, desc in FONTES_CAPAS:
        col_chk, col_desc = st.columns([1, 4])
        with col_chk:
            sel_capas[fonte_id] = st.checkbox(
                label, value=fonte_id in ativas_capas, key=f"capa_{fonte_id}"
            )
        with col_desc:
            st.caption(desc)

    st.divider()
    col_save, col_reset = st.columns([2, 1])
    with col_save:
        salvar = st.form_submit_button("💾 Salvar configuração", type="primary", use_container_width=True)
    with col_reset:
        resetar = st.form_submit_button("↺ Restaurar padrões", use_container_width=True)

if salvar:
    nova_cfg = {
        "metadados": [f for f in sel_meta  if sel_meta[f]],
        "capas":     [f for f in sel_capas if sel_capas[f]],
    }
    salvar_config_apis(nova_cfg)
    st.toast("Configuração salva!", icon="✅")
    st.rerun()

if resetar:
    import os
    try:
        os.remove("data/config_apis.json")
    except FileNotFoundError:
        pass
    st.toast("Padrões restaurados!", icon="↺")
    st.rerun()

_session_bar()
_sidebar_tema()
