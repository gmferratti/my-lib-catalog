# Ficha de Catálogo, Busca no Topo e Consolidação de Estantes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar barra de busca no topo do Acervo, ficha de catálogo completa ao clicar em um livro, e mecanismo para confirmar posições de estante nos registros.

**Architecture:** Todas as mudanças ficam em `ui/app.py` (UI) e `catalog/config.py` + `scripts/migrar_posicao_estante.py` (schema). A navegação ficha↔grade usa `st.session_state["isbn_selecionado"]`; a consolidação grava `estante`/`prateleira` nos registros via `reescrever_registros()`.

**Tech Stack:** Streamlit, Python 3.11+, catalog.storage (JSONL + CSV)

---

## Estrutura de arquivos

| Arquivo | Ação | O que muda |
|---|---|---|
| `catalog/config.py` | Modificar | Adicionar `"estante"` e `"prateleira"` ao `CSV_HEADERS` |
| `scripts/migrar_posicao_estante.py` | Criar | Script de migração idempotente |
| `CLAUDE.md` | Modificar | Schema atualizado com `estante` e `prateleira` |
| `ui/app.py` | Modificar | Busca no topo, `_render_ficha()`, botão "Ver ficha", botão "Aplicar sugestão" |

---

## Task 1: Schema + Migração

**Files:**
- Modify: `catalog/config.py:10-13`
- Create: `scripts/migrar_posicao_estante.py`
- Modify: `CLAUDE.md` (tabela de schema)

- [ ] **Step 1: Adicionar campos ao CSV_HEADERS**

Em `catalog/config.py`, linha 10-13, substituir:

```python
CSV_HEADERS = [
    "isbn", "titulo", "autores", "editora", "ano",
    "paginas", "idioma", "assuntos", "capa_url", "capa_fonte", "fonte", "data_cadastro",
]
```

por:

```python
CSV_HEADERS = [
    "isbn", "titulo", "autores", "editora", "ano",
    "paginas", "idioma", "assuntos", "capa_url", "capa_fonte", "fonte", "data_cadastro",
    "estante", "prateleira",
]
```

- [ ] **Step 2: Criar script de migração**

Criar `scripts/migrar_posicao_estante.py`:

```python
#!/usr/bin/env python3
"""One-shot migration: add estante and prateleira to all existing records."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from catalog.storage import carregar_todos_registros, reescrever_registros


def main() -> None:
    registros = carregar_todos_registros()
    if not registros:
        print("Nenhum registro encontrado.")
        return

    atualizados = 0
    for r in registros:
        changed = False
        if "estante" not in r:
            r["estante"] = ""
            changed = True
        if "prateleira" not in r:
            r["prateleira"] = ""
            changed = True
        if changed:
            atualizados += 1

    if atualizados:
        reescrever_registros(registros)
        print(f"{atualizados} registro(s) migrado(s) — campos estante e prateleira adicionados.")
    else:
        print("Todos os registros já têm estante e prateleira. Nada a migrar.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Rodar a migração**

```bash
PYTHONPATH=. uv run python scripts/migrar_posicao_estante.py
```

Expected output:
```
103 registro(s) migrado(s) — campos estante e prateleira adicionados.
```

- [ ] **Step 4: Atualizar CLAUDE.md**

Na tabela de schema (após `data_cadastro`), adicionar as duas linhas:

```markdown
| `estante` | str | `"Estante 2"` | Vazio se posição não confirmada |
| `prateleira` | str | `"B"` | Vazio se posição não confirmada |
```

- [ ] **Step 5: Verificar que o CSV tem os novos cabeçalhos**

```bash
head -1 data/biblioteca.csv
```

Expected: linha com `...data_cadastro,estante,prateleira`

- [ ] **Step 6: Commit**

```bash
git add catalog/config.py scripts/migrar_posicao_estante.py CLAUDE.md data/biblioteca.csv data/biblioteca.jsonl
git commit -m "feat(schema): add estante and prateleira fields; run migration"
```

---

## Task 2: Busca no Topo

**Files:**
- Modify: `ui/app.py` — função `_render_acervo()` (linhas ~244–342)

A busca atual está dentro do bloco `with st.sidebar:` (linha ~249). Precisa ser movida para **antes** do sidebar, como primeira linha de conteúdo de `_render_acervo()`.

- [ ] **Step 1: Mover busca para o topo do conteúdo**

Na função `_render_acervo()`, o bloco atual começa assim:

```python
def _render_acervo() -> None:
    registros = _carregar()

    with st.sidebar:
        st.header("Filtros")
        busca = st.text_input("Título ou autor", placeholder="ex: Tolkien")
        idiomas = sorted(...)
```

Substituir pelo seguinte (busca fora do sidebar, sidebar sem a linha de busca):

```python
def _render_acervo() -> None:
    registros = _carregar()

    busca = st.text_input(
        "",
        placeholder="🔍 Buscar por título ou autor...",
        label_visibility="collapsed",
    )

    with st.sidebar:
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
        modo_edicao = st.toggle("✏️ Modo edição", value=False,
                                help="Exibe botão de edição em cada card")
        st.divider()
        if st.button("🔄 Recarregar dados"):
            st.cache_data.clear()
            st.rerun()
    # ... resto da função inalterado
```

- [ ] **Step 2: Verificar no browser**

Rodar `streamlit run ui/app.py`, abrir a aba Acervo e confirmar:
- Barra de busca aparece no topo do conteúdo (acima das métricas)
- Sidebar não tem mais o campo de busca
- Filtrar por "Harry" funciona e filtra os cards corretamente

- [ ] **Step 3: Commit**

```bash
git add ui/app.py
git commit -m "feat(ui): move search bar to top of Acervo content"
```

---

## Task 3: Ficha de Catálogo

**Files:**
- Modify: `ui/app.py` — adicionar `_render_ficha()`, botão nos cards, roteamento em `_render_acervo()`

- [ ] **Step 1: Adicionar função `_render_ficha()`**

Inserir a função **antes** de `_render_acervo()` (por volta da linha 244 atual):

```python
def _render_ficha(registro: dict) -> None:
    if st.button("← Voltar ao acervo"):
        del st.session_state["isbn_selecionado"]
        st.rerun()

    st.divider()

    capa = registro.get("capa_url", "")
    col_capa, col_info = st.columns([1, 3])

    with col_capa:
        if capa:
            st.image(capa, width=200)
        else:
            st.markdown(
                '<div style="height:280px;background:#eceff1;display:flex;'
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

        if st.button("✏️ Editar este livro", key=f"edit_ficha_{registro['isbn']}"):
            _dialog_editar(registro)
```

- [ ] **Step 2: Adicionar roteamento no início de `_render_acervo()`**

Logo após `registros = _carregar()` e antes da linha `busca = st.text_input(...)`, inserir:

```python
isbn_sel = st.session_state.get("isbn_selecionado")
if isbn_sel:
    r = next((r for r in registros if r["isbn"] == isbn_sel), None)
    if r:
        _render_ficha(r)
        return
    del st.session_state["isbn_selecionado"]
```

- [ ] **Step 3: Adicionar botão "Ver ficha" em cada card**

No loop de cards (dentro do `with col:`), após o bloco de badges e antes do bloco `if modo_edicao:`, adicionar:

```python
if st.button("📖 Ver ficha", key=f"ficha_{r['isbn']}", use_container_width=True):
    st.session_state["isbn_selecionado"] = r["isbn"]
    st.rerun()
```

O trecho do card deve ficar assim ao final:

```python
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
    st.markdown(f"**{r.get('titulo') or r.get('isbn', '—')}**")
    if r.get("autores"):
        st.caption(r["autores"])
    if r.get("ano"):
        st.caption(f"📅 {r['ano']}")
    st.markdown(_badge(r.get("fonte", "")), unsafe_allow_html=True)
    badge_capa = _badge_capa(r.get("capa_fonte", ""))
    if badge_capa:
        st.markdown(badge_capa, unsafe_allow_html=True)
    if st.button("📖 Ver ficha", key=f"ficha_{r['isbn']}", use_container_width=True):
        st.session_state["isbn_selecionado"] = r["isbn"]
        st.rerun()
    if modo_edicao:
        if st.button("✏️ Editar", key=f"edit_{r['isbn']}",
                     use_container_width=True):
            _dialog_editar(r)
```

- [ ] **Step 4: Verificar no browser**

Rodar `streamlit run ui/app.py` e testar:
- Clicar "📖 Ver ficha" em qualquer card abre a ficha corretamente
- Ficha mostra: capa, título, autores, editora/ano, ISBN, idioma, páginas, assuntos, badges, data, posição ("Posição não confirmada")
- "← Voltar ao acervo" retorna para a grade com os filtros preservados
- Botão "✏️ Editar este livro" abre o dialog de edição existente

- [ ] **Step 5: Commit**

```bash
git add ui/app.py
git commit -m "feat(ui): add book detail ficha with session_state navigation"
```

---

## Task 4: Botão "Aplicar Sugestão" (Consolidação de Estantes)

**Files:**
- Modify: `ui/app.py` — função `_render_estantes()` (após download button, ~linha 504)

- [ ] **Step 1: Adicionar botão após o download button**

Em `_render_estantes()`, localizar o bloco do download button (atual):

```python
    st.download_button(
        "📥 Baixar sugestão (.txt)",
        data=txt.encode("utf-8"),
        file_name=f"organizacao_{estilo_usado}.txt",
        mime="text/plain",
    )
```

Após ele, adicionar:

```python
    if st.button("✅ Aplicar esta sugestão como posição real", type="primary"):
        todos = carregar_todos_registros()
        mapa: dict[str, tuple[str, str]] = {}
        for prat in resultado:
            for livro in prat.livros:
                mapa[livro["isbn"]] = (prat.estante, prat.prateleira)
        for r in todos:
            estante_val, prat_val = mapa.get(r["isbn"], ("", ""))
            r["estante"] = estante_val
            r["prateleira"] = prat_val
        reescrever_registros(todos)
        st.cache_data.clear()
        st.toast("Posições aplicadas ao acervo!", icon="✅")
        st.rerun()
```

- [ ] **Step 2: Verificar no browser**

Rodar `streamlit run ui/app.py` e testar:
1. Ir em Estantes → configurar estantes → clicar "Gerar sugestão"
2. Clicar "✅ Aplicar esta sugestão como posição real"
3. Toast de confirmação aparece
4. Ir em Acervo → clicar "📖 Ver ficha" num livro que estava na sugestão
5. Posição exibe `📍 Estante 1 / Prateleira A` (ou equivalente)
6. Abrir um livro que ficou "sem lugar" — deve exibir "Posição não confirmada"

- [ ] **Step 3: Commit**

```bash
git add ui/app.py
git commit -m "feat(ui): add 'Aplicar sugestão' button to confirm shelf positions"
```
