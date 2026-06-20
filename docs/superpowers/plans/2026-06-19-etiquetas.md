# Sistema de Etiquetas — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar um campo `etiquetas` ao schema de livros e expô-lo na UI — com atribuição no dialog de edição, badges nos cards, filtro AND na sidebar e exibição completa na ficha.

**Architecture:** Campo string separada por vírgula (mesmo padrão de `assuntos`), adicionado a `CSV_HEADERS` em `config.py`. A camada de persistência já lida com campos extras sem mudanças. Um script de migração adiciona o campo vazio aos registros existentes. A UI usa um helper `_badge_etiqueta()` em `ui/utils.py` reutilizado nos cards e na ficha.

**Tech Stack:** Python 3.12, Streamlit 1.58, JSONL + CSV, pytest

---

## Mapa de arquivos

| Arquivo | Ação |
|---|---|
| `catalog/config.py` | Modificar — adicionar `"etiquetas"` em `CSV_HEADERS` |
| `tests/test_persistence.py` | Modificar — novo caso de teste para o campo `etiquetas` |
| `scripts/migrar_etiquetas.py` | Criar — script de migração one-shot |
| `ui/utils.py` | Modificar — helper `_badge_etiqueta`, campo etiquetas em `_dialog_editar` e `_salvar_edicao` |
| `ui/pages/acervo.py` | Modificar — badges nos cards + filtro AND na sidebar |
| `ui/pages/ficha.py` | Modificar — exibição completa das etiquetas |

---

## Task 1: Schema + Teste de persistência

**Files:**
- Modify: `catalog/config.py`
- Modify: `tests/test_persistence.py`

- [ ] **Step 1: Escrever o teste que vai falhar**

Em `tests/test_persistence.py`, adicionar ao final do arquivo:

```python
def test_salvar_etiquetas(sample_record):
    registro = {**sample_record, "etiquetas": "lazer, doutorado"}
    salvar(registro)

    # JSONL roundtrip
    registros = carregar_todos_registros()
    assert registros[0].get("etiquetas") == "lazer, doutorado"

    # CSV deve ter coluna etiquetas
    with open(pers.CSV_FILE, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert "etiquetas" in rows[0], "coluna etiquetas ausente no CSV"
    assert rows[0]["etiquetas"] == "lazer, doutorado"
```

- [ ] **Step 2: Rodar o teste para confirmar que falha**

```bash
pytest tests/test_persistence.py::test_salvar_etiquetas -v
```

Resultado esperado: **FAIL** — `"coluna etiquetas ausente no CSV"`

- [ ] **Step 3: Adicionar `etiquetas` ao CSV_HEADERS**

Em `catalog/config.py`, na lista `CSV_HEADERS`, adicionar `"etiquetas"` após `"prateleira"`:

```python
CSV_HEADERS = [
    "isbn", "titulo", "autores", "editora", "ano",
    "paginas", "idioma", "assuntos", "capa_url", "capa_fonte", "fonte", "data_cadastro",
    "estante", "prateleira", "etiquetas",
]
```

- [ ] **Step 4: Rodar o teste para confirmar que passa**

```bash
pytest tests/test_persistence.py -v
```

Resultado esperado: **PASS** em todos os testes (incluindo o novo).

- [ ] **Step 5: Commit**

```bash
git add catalog/config.py tests/test_persistence.py
git commit -m "feat: add etiquetas field to schema and persistence"
```

---

## Task 2: Script de migração

**Files:**
- Create: `scripts/migrar_etiquetas.py`

- [ ] **Step 1: Criar o script**

```python
#!/usr/bin/env python3
"""One-shot migration: add etiquetas field to all existing records."""

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
        if "etiquetas" not in r:
            r["etiquetas"] = ""
            atualizados += 1

    if atualizados:
        reescrever_registros(registros)
        print(f"{atualizados} registro(s) migrado(s) — campo etiquetas adicionado.")
    else:
        print("Todos os registros já têm o campo etiquetas. Nada a migrar.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Rodar o script**

```bash
python scripts/migrar_etiquetas.py
```

Resultado esperado: `N registro(s) migrado(s) — campo etiquetas adicionado.`

- [ ] **Step 3: Verificar que o JSONL foi atualizado**

```bash
python -c "
import json
from pathlib import Path
linhas = Path('data/biblioteca.jsonl').read_text().splitlines()
r = json.loads(linhas[0])
print('etiquetas' in r, repr(r.get('etiquetas')))
"
```

Resultado esperado: `True ''`

- [ ] **Step 4: Commit**

```bash
git add scripts/migrar_etiquetas.py data/biblioteca.jsonl data/biblioteca.csv
git commit -m "feat: migrate existing records to include etiquetas field"
```

---

## Task 3: Helper de badge + dialog de edição

**Files:**
- Modify: `ui/utils.py`

- [ ] **Step 1: Adicionar helper `_badge_etiqueta` em `ui/utils.py`**

Após a função `_badge_capa` (linha ~145), inserir:

```python
def _badge_etiqueta(etiqueta: str) -> str:
    return (
        f'<span style="background:#ede7f6;color:#6a1b9a;padding:2px 8px;'
        f'border-radius:12px;font-size:0.75rem;font-weight:500">{etiqueta}</span>'
    )
```

- [ ] **Step 2: Adicionar importação de `carregar_todos_registros` em `ui/utils.py`**

A linha atual de importação já inclui `carregar_todos_registros`:

```python
from catalog.storage import carregar_todos_registros, reescrever_registros
```

Confirmar que está presente (linha ~17). Se não estiver, adicionar `carregar_todos_registros` ao import.

- [ ] **Step 3: Adicionar campo etiquetas ao `_dialog_editar`**

Dentro da função `_dialog_editar`, antes do bloco `with st.form(...)`, adicionar:

```python
    todos_registros = carregar_todos_registros()
    todas_etiquetas = sorted({
        e.strip()
        for r in todos_registros
        for e in (r.get("etiquetas") or "").split(",")
        if e.strip()
    })
    etiquetas_atuais = [
        e.strip()
        for e in (registro.get("etiquetas") or "").split(",")
        if e.strip()
    ]
```

- [ ] **Step 4: Adicionar widget de etiquetas ao form**

Dentro do `with st.form("form_edicao", border=False):`, após o campo `assuntos` (linha ~221), adicionar:

```python
        etiquetas_sel = st.multiselect(
            "Etiquetas",
            options=sorted(set(todas_etiquetas) | set(etiquetas_atuais)),
            default=etiquetas_atuais,
            accept_new_options=True,
            help="Sua curadoria pessoal — selecione existentes ou digite novas",
        )
```

- [ ] **Step 5: Incluir `etiquetas` no `_salvar_edicao`**

No bloco `if submitted:` no final de `_dialog_editar`, adicionar `"etiquetas"` ao dict passado para `_salvar_edicao`:

```python
    if submitted:
        _salvar_edicao(isbn, {
            "titulo": titulo.strip(), "autores": autores.strip(),
            "editora": editora.strip(), "ano": ano.strip(),
            "paginas": paginas.strip(), "idioma": idioma.strip(),
            "assuntos": assuntos.strip(), "capa_url": capa_url.strip(),
            "fonte": fonte,
            "etiquetas": ", ".join(etiquetas_sel),
        })
```

- [ ] **Step 6: Rodar os testes para garantir que nada quebrou**

```bash
pytest -v
```

Resultado esperado: todos os testes passam.

- [ ] **Step 7: Commit**

```bash
git add ui/utils.py
git commit -m "feat: add etiquetas badge helper and edit dialog field"
```

---

## Task 4: Badges nos cards + filtro na sidebar (acervo)

**Files:**
- Modify: `ui/pages/acervo.py`

- [ ] **Step 1: Adicionar `_badge_etiqueta` aos imports**

No topo de `ui/pages/acervo.py`, adicionar `_badge_etiqueta` à lista de imports de `ui.utils`:

```python
from ui.utils import (
    ESTILOS,
    _IDIOMA_NORM,
    _badge,
    _badge_capa,
    _badge_etiqueta,
    _carregar,
    _dialog_editar,
    _dialog_login,
    _estatisticas,
    _is_autenticado,
    _normalizar,
)
```

- [ ] **Step 2: Calcular etiquetas únicas do acervo**

Após a linha `registros = _carregar()` (linha ~23), adicionar:

```python
_todas_etiquetas_acervo = sorted({
    e.strip()
    for r in registros
    for e in (r.get("etiquetas") or "").split(",")
    if e.strip()
})
```

- [ ] **Step 3: Adicionar filtro de etiquetas na sidebar**

Dentro do bloco `with st.sidebar:`, após `ocultar_sem_meta = st.checkbox(...)` e antes do `st.divider()` que precede "Ordenação", adicionar:

```python
    if _todas_etiquetas_acervo:
        etiquetas_sel = st.multiselect("🏷️ Etiquetas", options=_todas_etiquetas_acervo)
    else:
        etiquetas_sel = []
```

- [ ] **Step 4: Adicionar lógica de filtro AND**

Após o bloco dos filtros existentes (idioma, fonte, sem_meta), antes de `reverso = direcao == "desc"`, adicionar:

```python
if etiquetas_sel:
    def _tem_todas(r: dict) -> bool:
        tags_livro = {e.strip() for e in (r.get("etiquetas") or "").split(",") if e.strip()}
        return all(e in tags_livro for e in etiquetas_sel)
    filtrados = [r for r in filtrados if _tem_todas(r)]
```

- [ ] **Step 5: Renderizar badges de etiquetas nos cards**

Nos cards, após `st.markdown(_badge(r.get("fonte", "")), ...)` e o bloco do `badge_capa`, adicionar:

```python
                etiquetas_lista = [
                    e.strip()
                    for e in (r.get("etiquetas") or "").split(",")
                    if e.strip()
                ]
                if etiquetas_lista:
                    visiveis = etiquetas_lista[:3]
                    extra = len(etiquetas_lista) - 3
                    badges_html = " ".join(_badge_etiqueta(e) for e in visiveis)
                    if extra > 0:
                        badges_html += (
                            f' <span style="background:#f3e5f5;color:#9c27b0;'
                            f'padding:2px 8px;border-radius:12px;font-size:0.75rem">'
                            f'+{extra}</span>'
                        )
                    st.markdown(badges_html, unsafe_allow_html=True)
```

- [ ] **Step 6: Rodar os testes**

```bash
pytest -v
```

Resultado esperado: todos passam.

- [ ] **Step 7: Commit**

```bash
git add ui/pages/acervo.py
git commit -m "feat: add etiquetas badges to cards and AND filter in sidebar"
```

---

## Task 5: Exibição na ficha

**Files:**
- Modify: `ui/pages/ficha.py`

- [ ] **Step 1: Adicionar `_badge_etiqueta` aos imports**

No topo de `ui/pages/ficha.py`, adicionar `_badge_etiqueta` à lista de imports de `ui.utils`:

```python
from ui.utils import (
    _IDIOMA_NORM,
    _badge,
    _badge_capa,
    _badge_etiqueta,
    _carregar,
    _dialog_editar,
    _dialog_login,
    _is_autenticado,
)
```

- [ ] **Step 2: Exibir etiquetas após `assuntos` na ficha**

Na seção `with col_info:`, após o bloco `if registro.get("assuntos"):` (linha ~72), adicionar:

```python
    etiquetas_lista = [
        e.strip()
        for e in (registro.get("etiquetas") or "").split(",")
        if e.strip()
    ]
    if etiquetas_lista:
        badges_html = " ".join(_badge_etiqueta(e) for e in etiquetas_lista)
        st.markdown(f"**Etiquetas:** {badges_html}", unsafe_allow_html=True)
```

- [ ] **Step 3: Rodar os testes**

```bash
pytest -v
```

Resultado esperado: todos passam.

- [ ] **Step 4: Commit**

```bash
git add ui/pages/ficha.py
git commit -m "feat: display etiquetas on book detail page"
```

---

## Verificação final

- [ ] Iniciar a UI: `streamlit run ui/app.py`
- [ ] Abrir o acervo — verificar que os cards não mostram nada novo (etiquetas vazias)
- [ ] Entrar no modo edição, editar um livro, adicionar etiquetas (ex: `lazer`, `doutorado`)
- [ ] Salvar — verificar badge roxo no card
- [ ] Adicionar etiqueta `lazer` a um segundo livro
- [ ] Filtrar por `lazer` na sidebar — verificar que ambos aparecem
- [ ] Filtrar por `lazer` + `doutorado` — verificar que só o primeiro livro aparece (AND)
- [ ] Abrir a ficha de um livro com etiquetas — verificar exibição completa sem truncamento
