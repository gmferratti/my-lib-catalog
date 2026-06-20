# Organizer Display & Shelf Editor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Padronizar a exibição de livros no organizador (formato "Título — Autor (ano)") e substituir o formulário global de estantes por um editor granular onde cada estante e prateleira tem suas próprias dimensões.

**Architecture:** Feature 1 extrai uma função pura `_formatar_livro` para `ui/formatting.py` e a aplica em 4 pontos de exibição em `ui/pages/estantes.py`. Feature 2 substitui o formulário de config global pelo um editor com session state (`estante_draft`) que rastreia a estrutura das estantes; mudanças estruturais (add/remove) sincronizam os valores dos widgets para o draft, limpam as chaves de session state e fazem `st.rerun()`.

**Tech Stack:** Python 3.12, Streamlit, pytest

---

## File Structure

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `ui/formatting.py` | **Criar** | `_formatar_livro(livro, markdown)` — função pura, sem import de streamlit |
| `ui/pages/estantes.py` | **Modificar** | Importa `_formatar_livro`; aplica em 4 pontos; adiciona helpers de draft; substitui form por editor |
| `tests/test_formatting.py` | **Criar** | Testes unitários de `_formatar_livro` |

---

## Task 1: Helper `_formatar_livro` (TDD)

**Files:**
- Create: `ui/formatting.py`
- Create: `tests/test_formatting.py`

- [ ] **Step 1: Escrever os testes**

Criar `tests/test_formatting.py`:

```python
from ui.formatting import _formatar_livro


def _livro(**kwargs):
    base = {"titulo": "", "autores": "", "ano": "", "isbn": "0000000000"}
    base.update(kwargs)
    return base


# ── markdown=True (padrão) ────────────────────────────────────────────────────

def test_titulo_autor_ano():
    livro = _livro(titulo="Kubernetes", autores="Kevin Welter", ano="2022")
    assert _formatar_livro(livro) == "**Kubernetes** — Kevin Welter (2022)"


def test_sem_autor():
    livro = _livro(titulo="Quadribol através dos séculos", ano="2001")
    assert _formatar_livro(livro) == "**Quadribol através dos séculos** (2001)"


def test_sem_ano():
    livro = _livro(titulo="Kubernetes", autores="Kevin Welter")
    assert _formatar_livro(livro) == "**Kubernetes** — Kevin Welter"


def test_sem_titulo():
    livro = _livro(autores="Autor Desconhecido", ano="2020")
    assert _formatar_livro(livro) == "**(sem título)** — Autor Desconhecido (2020)"


def test_apenas_titulo_sem_autor_sem_ano():
    livro = _livro(titulo="Apenas Título")
    assert _formatar_livro(livro) == "**Apenas Título**"


def test_titulo_e_autor_sem_ano():
    livro = _livro(titulo="Social Psychology of Organizing", autores="Karl E Weick")
    assert _formatar_livro(livro) == "**Social Psychology of Organizing** — Karl E Weick"


# ── markdown=False ────────────────────────────────────────────────────────────

def test_plain_text_com_autor():
    livro = _livro(titulo="Kubernetes", autores="Kevin Welter", ano="2022")
    assert _formatar_livro(livro, markdown=False) == "Kubernetes — Kevin Welter (2022)"


def test_plain_text_sem_autor():
    livro = _livro(titulo="Quadribol através dos séculos", ano="2001")
    assert _formatar_livro(livro, markdown=False) == "Quadribol através dos séculos (2001)"
```

- [ ] **Step 2: Executar os testes e confirmar que falham**

```bash
pytest tests/test_formatting.py -v
```

Resultado esperado: `ModuleNotFoundError: No module named 'ui.formatting'`

- [ ] **Step 3: Criar `ui/formatting.py`**

```python
def _formatar_livro(livro: dict, markdown: bool = True) -> str:
    titulo = livro.get("titulo") or "(sem título)"
    autores = livro.get("autores") or ""
    ano = f" ({livro['ano']})" if livro.get("ano") else ""
    titulo_fmt = f"**{titulo}**" if markdown else titulo
    if autores:
        return f"{titulo_fmt} — {autores}{ano}"
    return f"{titulo_fmt}{ano}"
```

- [ ] **Step 4: Executar os testes e confirmar que passam**

```bash
pytest tests/test_formatting.py -v
```

Resultado esperado:
```
tests/test_formatting.py::test_titulo_autor_ano PASSED
tests/test_formatting.py::test_sem_autor PASSED
tests/test_formatting.py::test_sem_ano PASSED
tests/test_formatting.py::test_sem_titulo PASSED
tests/test_formatting.py::test_apenas_titulo_sem_autor_sem_ano PASSED
tests/test_formatting.py::test_titulo_e_autor_sem_ano PASSED
tests/test_formatting.py::test_plain_text_com_autor PASSED
tests/test_formatting.py::test_plain_text_sem_autor PASSED
8 passed
```

- [ ] **Step 5: Commit**

```bash
git add ui/formatting.py tests/test_formatting.py
git commit -m "feat(display): helper _formatar_livro — Título — Autor (ano)"
```

---

## Task 2: Aplicar `_formatar_livro` nos 4 pontos de exibição

**Files:**
- Modify: `ui/pages/estantes.py`

- [ ] **Step 1: Adicionar import em `ui/pages/estantes.py`**

Localizar a linha:
```python
from ui.utils import ESTILOS, _carregar, _carregar_config, _session_bar
```

Adicionar após ela:
```python
from ui.formatting import _formatar_livro
```

- [ ] **Step 2: Substituir ponto 1 — loop principal em `_gerar_txt`**

Localizar (dentro de `_gerar_txt`, loop `for livro in r.livros:`):
```python
        for livro in r.livros:
            titulo = livro.get("titulo") or "(sem título)"
            autores = livro.get("autores") or "(sem autor)"
            ano = livro.get("ano") or "—"
            linhas.append(f"  {autores} — {titulo} ({ano})")
```

Substituir por:
```python
        for livro in r.livros:
            linhas.append(f"  {_formatar_livro(livro, markdown=False)}")
```

- [ ] **Step 3: Substituir ponto 2 — sem_lugar em `_gerar_txt`**

Localizar (ainda dentro de `_gerar_txt`):
```python
        for livro in sem_lugar:
            titulo = livro.get("titulo") or livro.get("isbn", "—")
            linhas.append(f"  {titulo}")
```

Substituir por:
```python
        for livro in sem_lugar:
            linhas.append(f"  {_formatar_livro(livro, markdown=False)}")
```

- [ ] **Step 4: Substituir ponto 3 — loop principal no expander de prateleira**

Localizar (dentro do `with st.expander(header, expanded=False):`):
```python
            for livro in r.livros:
                titulo = livro.get("titulo") or "(sem título)"
                autores = livro.get("autores") or "(sem autor)"
                ano = f" ({livro['ano']})" if livro.get("ano") else ""
                st.markdown(f"- {autores} — **{titulo}**{ano}")
```

Substituir por:
```python
            for livro in r.livros:
                st.markdown(f"- {_formatar_livro(livro)}")
```

- [ ] **Step 5: Substituir ponto 4 — seção sem_lugar na UI**

Localizar:
```python
if sem_lugar:
    st.subheader("📦 Livros sem lugar")
    for livro in sem_lugar:
        titulo = livro.get("titulo") or livro.get("isbn", "—")
        autores = livro.get("autores", "")
        st.markdown(f"- {autores} — **{titulo}**" if autores else f"- **{titulo}**")
```

Substituir por:
```python
if sem_lugar:
    st.subheader("📦 Livros sem lugar")
    for livro in sem_lugar:
        st.markdown(f"- {_formatar_livro(livro)}")
```

- [ ] **Step 6: Executar a suíte completa**

```bash
pytest -v
```

Resultado esperado: todos os testes passam (incluindo os 8 novos de `test_formatting.py`).

- [ ] **Step 7: Commit**

```bash
git add ui/pages/estantes.py
git commit -m "feat(display): aplicar _formatar_livro nos 4 pontos de exibição do organizador"
```

---

## Task 3: Helpers de draft + inicialização de estado

**Files:**
- Modify: `ui/pages/estantes.py`

- [ ] **Step 1: Adicionar helpers `_sync_draft` e `_clear_widget_keys` após `_gerar_txt`**

Localizar a linha que encerra `_gerar_txt`:
```python
    return "\n".join(linhas)
```

Adicionar imediatamente após (fora da função):
```python

def _sync_draft() -> None:
    """Lê os valores atuais dos widgets e os grava no rascunho."""
    for i, e in enumerate(st.session_state.get("estante_draft", [])):
        e["nome"] = st.session_state.get(f"est_{i}_nome", e["nome"])
        for j, p in enumerate(e["prateleiras"]):
            p["nome"] = st.session_state.get(f"prat_{i}_{j}_nome", p["nome"])
            p["largura_cm"] = float(
                st.session_state.get(f"prat_{i}_{j}_largura", p["largura_cm"])
            )


def _clear_widget_keys() -> None:
    """Remove as chaves dos widgets de prateleira/estante para forçar reinicialização."""
    for k in [k for k in st.session_state
              if k.startswith(("est_", "prat_", "espessura_editor"))]:
        del st.session_state[k]
```

- [ ] **Step 2: Adicionar bloco de inicialização do draft antes do expander de configuração**

Localizar:
```python
with st.expander("⚙️ Configurar estantes", expanded=not bool(_carregar_config().estantes)):
```

Inserir antes dessa linha:
```python
if "estante_draft" not in st.session_state:
    _cfg_init = carregar_config()
    st.session_state["estante_draft"] = [
        {
            "nome": e.nome,
            "prateleiras": [
                {"nome": p.nome, "largura_cm": p.largura_cm}
                for p in e.prateleiras
            ],
        }
        for e in _cfg_init.estantes
    ]
    st.session_state["espessura_draft"] = _cfg_init.espessura_media_cm

```

- [ ] **Step 3: Executar testes**

```bash
pytest -v
```

Resultado esperado: todos os testes passam.

- [ ] **Step 4: Commit**

```bash
git add ui/pages/estantes.py
git commit -m "feat(estantes): helpers de draft e inicialização de estado para o editor granular"
```

---

## Task 4: Substituir formulário global pelo editor granular

**Files:**
- Modify: `ui/pages/estantes.py`

Este task substitui o bloco `with st.expander("⚙️ Configurar estantes"...):` atual (incluindo o bloco `if salvar:`) pelo novo editor granular.

- [ ] **Step 1: Localizar e apagar o bloco do formulário antigo**

Remover o trecho que começa em:
```python
with st.expander("⚙️ Configurar estantes", expanded=not bool(_carregar_config().estantes)):
```

e termina em (inclusive):
```python
        st.rerun()
```

após o `if salvar:` block (todo o bloco de ~67 linhas, até a linha `st.rerun()` do `if salvar:`).

- [ ] **Step 2: No lugar do trecho removido, inserir o novo editor**

```python
with st.expander("⚙️ Configurar estantes", expanded=not bool(st.session_state["estante_draft"])):
    st.number_input(
        "Espessura média dos livros (cm)", min_value=0.5, max_value=10.0,
        value=float(st.session_state.get("espessura_draft", 2.5)),
        step=0.5, key="espessura_editor",
        help="Usada para estimar quantos livros cabem em cada prateleira.",
    )

    for i, estante in enumerate(st.session_state["estante_draft"]):
        st.markdown(f"---\n**🗄️ Estante {i + 1}**")
        st.text_input(
            "Nome da estante", value=estante["nome"],
            key=f"est_{i}_nome", label_visibility="collapsed",
            placeholder="Nome da estante",
        )

        for j, prat in enumerate(estante["prateleiras"]):
            c1, c2, c3 = st.columns([2, 4, 1])
            c1.text_input(
                "Nome", value=prat["nome"],
                key=f"prat_{i}_{j}_nome", label_visibility="collapsed",
                placeholder="Nome",
            )
            c2.number_input(
                "Largura (cm)", min_value=10.0, max_value=500.0, step=5.0,
                value=float(prat["largura_cm"]),
                key=f"prat_{i}_{j}_largura", label_visibility="collapsed",
            )
            if c3.button("🗑️", key=f"del_prat_{i}_{j}", help="Remover prateleira"):
                _sync_draft()
                estante["prateleiras"].pop(j)
                _clear_widget_keys()
                st.rerun()

        col_add_p, col_del_e = st.columns([3, 2])
        if col_add_p.button("+ Prateleira", key=f"add_prat_{i}"):
            _sync_draft()
            letras = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            n = len(estante["prateleiras"])
            nome_prat = (
                letras[n % 26] if n < 26
                else f"{letras[(n // 26) - 1]}{letras[n % 26]}"
            )
            estante["prateleiras"].append({"nome": nome_prat, "largura_cm": 80.0})
            _clear_widget_keys()
            st.rerun()
        if col_del_e.button("🗑️ Remover estante", key=f"del_est_{i}", type="secondary"):
            _sync_draft()
            st.session_state["estante_draft"].pop(i)
            _clear_widget_keys()
            st.rerun()

        espessura_val = float(st.session_state.get("espessura_editor", 2.5))
        cap_est = sum(
            max(1, int(
                float(st.session_state.get(f"prat_{i}_{j}_largura", p["largura_cm"]))
                / espessura_val
            ))
            for j, p in enumerate(estante["prateleiras"])
        )
        st.caption(
            f"Capacidade estimada: **{cap_est} livros** "
            f"({len(estante['prateleiras'])} prateleiras)"
        )

    st.divider()
    col_add_e, col_save = st.columns([1, 1])
    if col_add_e.button("+ Adicionar estante", key="add_estante"):
        _sync_draft()
        n = len(st.session_state["estante_draft"])
        st.session_state["estante_draft"].append({
            "nome": f"Estante {n + 1}",
            "prateleiras": [{"nome": "A", "largura_cm": 80.0}],
        })
        _clear_widget_keys()
        st.rerun()

    if col_save.button("💾 Salvar configuração", type="primary", key="salvar_estantes"):
        _sync_draft()
        nova_cfg = ConfigEstantes(
            espessura_media_cm=float(st.session_state.get("espessura_editor", 2.5)),
            estantes=[
                EstanteConfig(
                    nome=e["nome"],
                    prateleiras=[
                        PrateleiraConfig(
                            nome=p["nome"],
                            largura_cm=float(p["largura_cm"]),
                        )
                        for p in e["prateleiras"]
                    ],
                )
                for e in st.session_state["estante_draft"]
            ],
        )
        salvar_config(nova_cfg)
        del st.session_state["estante_draft"]
        _clear_widget_keys()
        st.cache_data.clear()
        st.toast("Configuração salva!", icon="✅")
        st.rerun()
```

- [ ] **Step 3: Executar testes**

```bash
pytest -v
```

Resultado esperado: todos os testes passam.

- [ ] **Step 4: Verificação manual — caminho principal**

Iniciar a UI:
```bash
streamlit run ui/app.py
```

Verificar:
1. Abrir a página **Estantes**. O expander "⚙️ Configurar estantes" deve abrir se não há config salva.
2. Clicar em **+ Adicionar estante**. Deve aparecer "Estante 1" com prateleira "A" de 80 cm.
3. Editar o nome da estante para "Sala" e a largura para 100 cm.
4. Clicar em **+ Prateleira**. Deve aparecer prateleira "B" de 80 cm.
5. Remover a prateleira "B" com o botão 🗑️. Deve sumir.
6. Clicar em **💾 Salvar configuração**. O toast "Configuração salva!" deve aparecer.
7. Reabrir o expander: os valores devem refletir o que foi salvo (nome "Sala", largura 100 cm).
8. Clicar em **🗂️ Gerar sugestão**. O organizador deve usar as larguras salvas.
9. Verificar que os livros na lista aparecem como "**Título** — Autor (ano)" e livros sem autor aparecem como "**Título** (ano)" sem prefixo.

- [ ] **Step 5: Verificação manual — download TXT**

1. Gerar sugestão e baixar o arquivo `.txt`.
2. Confirmar que cada livro aparece como "Título — Autor (ano)" ou "Título (ano)" em texto puro, sem asteriscos.

- [ ] **Step 6: Commit**

```bash
git add ui/pages/estantes.py
git commit -m "feat(estantes): editor granular de estantes e prateleiras com dimensões individuais"
```

---

## Self-Review

**Spec coverage:**
- ✅ Feature 1: `_formatar_livro` extraída em `ui/formatting.py`, aplicada em 4 pontos (spec dizia 3, mas o `_gerar_txt` tem 2 loops separados — correto incluir os 4).
- ✅ Feature 2: editor substitui o formulário global; add/remove de estante e prateleira; largura por prateleira; espessura global; salvar reconstrói `ConfigEstantes`.
- ✅ Schema de `estantes.json` inalterado.
- ✅ `espessura_media_cm` permanece global.

**Placeholders:** nenhum.

**Type consistency:** `_formatar_livro(livro: dict, markdown: bool) -> str` — usado consistentemente com esse assinatura em todos os pontos. `_sync_draft` e `_clear_widget_keys` sem retorno, usados antes de todos os `st.rerun()`.
