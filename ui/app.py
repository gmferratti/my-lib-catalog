import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(
    page_title="Minha Biblioteca",
    page_icon="📚",
    layout="wide",
)

pg = st.navigation(
    [
        st.Page("pages/acervo.py",   title="Acervo",          icon="📚", default=True),
        st.Page("pages/ficha.py",    title="Ficha",            icon="📖", url_path="ficha"),
        st.Page("pages/estantes.py", title="Estantes",         icon="🗂️"),
        st.Page("pages/leitura.py",  title="Lista de Leitura", icon="📋"),
        st.Page("pages/sobre.py",    title="Sobre",            icon="ℹ️"),
    ],
    position="hidden",
)
pg.run()
