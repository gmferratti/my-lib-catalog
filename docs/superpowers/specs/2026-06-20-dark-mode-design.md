# Dark Mode — Design Spec

**Data:** 2026-06-20  
**Status:** Aprovado

---

## Resumo

Adicionar suporte a dark/light mode no app Streamlit com toggle na sidebar, persistência entre sessões via arquivo local e dark mode como padrão.

---

## Decisões de design

- **Abordagem:** `base = "dark"` no `config.toml` (dark nativo do Streamlit) + injeção de CSS para modo claro
- **Padrão inicial:** escuro
- **Persistência:** `.streamlit/ui_prefs.json` — fora de `data/` para não gerar ruído no git
- **Toggle:** sidebar de todas as páginas, abaixo dos controles existentes

---

## Seção 1 — Config & Persistência

### `config.toml`

```toml
[server]
headless = true

[theme]
base = "dark"
```

### `.streamlit/ui_prefs.json`

```json
{"tema": "escuro"}
```

Criado automaticamente na primeira troca de tema. Se ausente, `_ler_tema()` retorna `"escuro"` (default).

### Helpers em `ui/utils.py`

```python
_PREFS_PATH = Path(__file__).parent.parent / ".streamlit" / "ui_prefs.json"

def _ler_tema() -> str:
    # Retorna "escuro" ou "claro". Default: "escuro".

def _salvar_tema(tema: str) -> None:
    # Escreve {"tema": tema} em _PREFS_PATH.
```

---

## Seção 2 — Toggle na Sidebar

Nova função `_sidebar_tema()` em `ui/utils.py`:

1. Se `"tema"` não estiver em `st.session_state`, inicializa com `_ler_tema()`
2. Renderiza `st.toggle("☀️ Modo claro", value=(tema == "claro"), key="toggle_tema")` no sidebar
3. Se o valor mudar: chama `_salvar_tema()` + `st.rerun()`

Chamada em todas as páginas **fora** de blocos `with st.sidebar:` existentes (igual ao padrão de `_session_bar()`). A função abre internamente `with st.sidebar:`, então múltiplas chamadas no mesmo arquivo são seguras — o Streamlit renderiza na ordem.

---

## Seção 3 — CSS Injection

Nova função `_injetar_tema()` em `ui/utils.py`, chamada no topo de cada página.

### Modo escuro (dark nativo — CSS mínimo)

Corrige apenas os elementos HTML customizados que ficam ruins em fundo escuro:

| Elemento | Antes | Depois |
|---|---|---|
| `.badge-etiqueta` | `bg #ede7f6, color #6a1b9a` | `bg #2d1b4e, color #ce93d8` |
| `.capa-placeholder` | `bg #eceff1` | `bg #2d2d2d` |
| `button[kind="secondary"]` (título card) | `color rgb(49,51,63)` | `color #fafafa` |
| `button[kind="secondary"]:hover` | `color #1565c0` | `color #90caf9` |

### Modo claro (CSS de override)

Reverte o Streamlit para visual light via seletores:

- `.stApp`, `[data-testid="stAppViewContainer"]` → fundo `#ffffff`
- `section[data-testid="stSidebar"]` → fundo `#f0f2f6`
- Métricas, inputs, selects → cores light
- `.badge-etiqueta` → volta para `bg #ede7f6, color #6a1b9a`
- `.capa-placeholder` → volta para `bg #eceff1`
- `button[kind="secondary"]` → `color rgb(49,51,63)`, hover `color #1565c0`

### Mudança no HTML customizado

`_badge_etiqueta()` passa a emitir `class="badge-etiqueta"` sem inline style de cor:

```html
<!-- Antes -->
<span style="background:#ede7f6;color:#6a1b9a;...">etiqueta</span>

<!-- Depois -->
<span class="badge-etiqueta" style="padding:2px 8px;border-radius:12px;font-size:0.75rem;font-weight:500">etiqueta</span>
```

Placeholders de capa usam `class="capa-placeholder"` no lugar de `background:#eceff1` inline.

---

## Seção 4 — Arquivos alterados

| Arquivo | Mudança |
|---|---|
| `.streamlit/config.toml` | `base = "dark"` |
| `ui/utils.py` | `_ler_tema`, `_salvar_tema`, `_sidebar_tema`, `_injetar_tema`; `_badge_etiqueta` usa classe CSS |
| `ui/pages/acervo.py` | Chama `_injetar_tema()` no topo; `_sidebar_tema()` no sidebar; botão de título usa classe |
| `ui/pages/ficha.py` | Chama `_injetar_tema()` no topo; placeholder usa classe; `_sidebar_tema()` no sidebar |
| `ui/pages/estantes.py` | Chama `_injetar_tema()` no topo; `_sidebar_tema()` no sidebar |
| `ui/pages/leitura.py` | Chama `_injetar_tema()` no topo; `_sidebar_tema()` no sidebar |
| `ui/pages/sobre.py` | Chama `_injetar_tema()` no topo; `_sidebar_tema()` no sidebar |

**Sem novos campos no schema, sem migração de dados, sem novas dependências.**

---

## Fora de escopo

- Detecção automática do tema do sistema operacional (prefers-color-scheme)
- Temas customizados além de dark/light
- Persistência via localStorage do browser
