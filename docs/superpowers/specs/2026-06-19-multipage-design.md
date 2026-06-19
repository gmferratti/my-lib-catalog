# Migração para Streamlit Multipage — Design

## Objetivo

Converter o app Streamlit de single-page com tabs para multipage usando a API moderna (`st.navigation` / `st.switch_page`). Benefício principal: o botão de voltar do browser funciona nativamente ao navegar da ficha de catálogo de volta ao acervo.

---

## Estrutura de arquivos

```
ui/
  app.py            ← entry point: st.navigation() com as 4 páginas
  utils.py          ← constantes, helpers e dialog compartilhados entre páginas
  pages/
    acervo.py       ← grade de cards + busca + sidebar de filtros
    ficha.py        ← detalhe do livro (recebe ISBN via session_state)
    estantes.py     ← organizador de estantes
    sobre.py        ← sobre o projeto
```

---

## Conteúdo de cada arquivo

### `ui/utils.py` (novo)

Tudo compartilhado entre duas ou mais páginas:

- Constantes: `FONTE_CORES`, `FONTE_LABELS`, `CAPA_FONTE_CORES`, `CAPA_FONTE_LABELS`, `ESTILOS`, `_IDIOMA_NORM`
- Funções: `_badge()`, `_badge_capa()`, `_normalizar()`, `_estatisticas()`, `_barra()`
- Cache: `_carregar()` (`@st.cache_data(ttl=60)`), `_carregar_config()` (`@st.cache_data(ttl=None)`)
- Persistência: `_salvar_edicao()`
- Dialog: `_dialog_editar()` (usado em `acervo.py` e `ficha.py`)

### `ui/app.py` (refatorado)

```python
import streamlit as st

st.set_page_config(page_title="Minha Biblioteca", page_icon="📚", layout="wide")

pg = st.navigation(
    [
        st.Page("pages/acervo.py",   title="Acervo",   icon="📚", default=True),
        st.Page("pages/ficha.py",    title="Ficha",     icon="📖", url_path="ficha"),
        st.Page("pages/estantes.py", title="Estantes",  icon="🗂️"),
        st.Page("pages/sobre.py",    title="Sobre",     icon="ℹ️"),
    ],
    position="hidden",  # suprime menu automático do Streamlit
)
pg.run()
```

Com `position="hidden"`, o Streamlit não renderiza o menu lateral automático. Cada página que precisa de sidebar define a sua própria. O Acervo e as Estantes têm sidebar de filtros/config; a Ficha e o Sobre não precisam de sidebar.

A navegação principal (Acervo / Estantes / Sobre) é exibida via `st.page_link()` na sidebar do Acervo e das Estantes. A Ficha é acessível apenas via `st.switch_page` — não aparece em nenhum menu.

### `ui/pages/acervo.py`

Conteúdo atual de `_render_acervo()`, adaptado:
- Remove verificação de `isbn_selecionado` (não mais necessária — ficha é página separada)
- Ao clicar no título: `st.session_state["isbn_ficha"] = isbn; st.switch_page("pages/ficha.py")`
- Importa tudo de `utils`

### `ui/pages/ficha.py`

Conteúdo atual de `_render_ficha()`, adaptado:
- Lê `isbn = st.session_state.get("isbn_ficha")`
- Se `isbn` não definido: redireciona para Acervo com `st.switch_page("pages/acervo.py")`
- Botão "← Voltar ao acervo": `st.switch_page("pages/acervo.py")`
- Importa tudo de `utils`

### `ui/pages/estantes.py`

Conteúdo atual de `_render_estantes()`, sem alterações funcionais. Importa de `utils`.

### `ui/pages/sobre.py`

Conteúdo atual de `_render_sobre()`, sem alterações funcionais.

---

## Navegação

| De | Para | Mecanismo |
|---|---|---|
| Acervo → Ficha | Clica no título do livro | `st.session_state["isbn_ficha"] = isbn` + `st.switch_page("pages/ficha.py")` |
| Ficha → Acervo (botão) | Clica "← Voltar" | `st.switch_page("pages/acervo.py")` |
| Ficha → Acervo (browser) | Botão de voltar do browser/celular | Funciona nativamente via `pushState` do `st.switch_page` |
| Qualquer → qualquer | Menu lateral | Links nativos do `st.navigation` |

---

## Session state entre páginas

Com `st.navigation`, o `session_state` é preservado ao navegar entre páginas na mesma sessão:
- `st.session_state["isbn_ficha"]` — ISBN passado do Acervo para a Ficha
- Filtros ativos, busca, configuração de estantes — todos preservados automaticamente

---

## Sidebar

Com `position="hidden"`, a sidebar padrão do Streamlit é suprimida. Cada página que precisar de sidebar define a sua. O Acervo mantém a sidebar de filtros. As demais páginas podem ter uma sidebar mínima com link de volta.

---

## Arquivos a modificar/criar

| Arquivo | Ação |
|---|---|
| `ui/utils.py` | Criar — extrair helpers compartilhados |
| `ui/app.py` | Refatorar — virar entry point com `st.navigation` |
| `ui/pages/acervo.py` | Criar — extrair `_render_acervo()` |
| `ui/pages/ficha.py` | Criar — extrair `_render_ficha()` |
| `ui/pages/estantes.py` | Criar — extrair `_render_estantes()` |
| `ui/pages/sobre.py` | Criar — extrair `_render_sobre()` |

`ui/app.py` atual é substituído completamente. As funções são movidas, não duplicadas.

---

## Não muda

- `catalog/` — nenhuma alteração em storage, metadata, organizer, config
- Dados em `data/` — nenhuma alteração
- Testes em `tests/` — nenhuma alteração (não testam UI)
- `CLAUDE.md` — seção "Como executar" mantém `streamlit run ui/app.py`
