import sys
from pathlib import Path

_proj_root = str(Path(__file__).parent.parent)
sys.path.insert(0, _proj_root)

# Evict any stale installed 'catalog' from site-packages before pages load
for _k in [k for k in sys.modules if k == "catalog" or k.startswith("catalog.")]:
    if "site-packages" in (getattr(sys.modules[_k], "__file__", "") or ""):
        del sys.modules[_k]

import streamlit as st
import catalog.storage.git_sync as git_sync

st.set_page_config(
    page_title="Minha Biblioteca",
    page_icon="📚",
    layout="wide",
)

try:
    git_sync.garantir_branch_sessao()
except Exception:
    pass  # Streamlit Cloud ou ambiente sem git writeable — session bar mostrará aviso

pg = st.navigation(
    [
        st.Page("pages/acervo.py",   title="Acervo",          icon="📚", default=True),
        st.Page("pages/ficha.py",    title="Ficha",            icon="📖", url_path="ficha"),
        st.Page("pages/estantes.py",       title="Estantes",         icon="🗂️"),
        st.Page("pages/leitura.py",        title="Lista de Leitura", icon="📋"),
        st.Page("pages/configuracoes.py",  title="Configurações",    icon="⚙️"),
        st.Page("pages/sobre.py",          title="Sobre",            icon="ℹ️"),
    ],
    position="hidden",
)
pg.run()
