import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

st.title("📚 Minha Biblioteca")

col, _ = st.columns([2, 1])
with col:
    st.header("Sobre o My Lib Catalog")
    st.markdown("""
My Lib Catalog nasceu de uma necessidade muito simples: Gustavo Ferratti, um apaixonado
por livros que mora em Araraquara, interior de São Paulo, precisava de uma forma de
organizar e consultar o próprio acervo pessoal de livros que crescia rapidamente.

O projeto foi construído inteiramente por ele (AI-assisted) com muito amor e carinho,
de forma gratuita, de bookworm para bookworm. Nada de algoritmos de recomendação, nada
de dados sendo vendidos. Só você, seus livros, uma interface que respeita o seu tempo
e o bom e velho open source.

**Como funciona:** você escaneia o código de barras do livro com um leitor de código de
barras pela CLI (rodar comando `make run` para entrar no loop principal); o sistema busca
os metadados automaticamente a partir do ISBN em múltiplas fontes (Open Library,
Google Books, BrasilAPI, ISBNdb) e organiza tudo para você consultar por autor, ano,
idioma, etc. Se algo não vier certo, há a possibilidade de ajuste manual.

**Organização de estantes:** a funcionalidade de organização física das estantes está em
desenvolvimento. Em breve você poderá distribuir seus livros pelas prateleiras de
forma otimizada.
""")
