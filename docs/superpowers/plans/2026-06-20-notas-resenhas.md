# Notas e Resenhas por Livro — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar suporte a anotações de texto livre e links externos por livro, visível na ficha individual de cada livro na UI Streamlit.

**Architecture:** Novo módulo `catalog/notas/` com arquivo de persistência `data/notas.json` indexado por ISBN, seguindo o padrão do `catalog/reading/`. A UI adiciona uma seção "📝 Anotações" em `ui/pages/ficha.py`, com visualização pública e dialog de edição protegido por `_is_autenticado()`. O dialog é definido em `ui/utils.py`, seguindo o padrão de `_dialog_editar`.

**Tech Stack:** Python stdlib (json, os, threading, datetime), Streamlit, pytest, git_sync (já existente no projeto)

---

## File Map

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `catalog/config.py` | Modificar | Adicionar constante `NOTAS_FILE` |
| `catalog/notas/__init__.py` | Criar | Re-exports públicos do módulo |
| `catalog/notas/storage.py` | Criar | CRUD de notas: `carregar`, `salvar`, `remover` |
| `tests/test_notas.py` | Criar | 6 casos de teste (TDD) |
| `ui/utils.py` | Modificar | Adicionar `import catalog.notas`, função `_dialog_notas` |
| `ui/pages/ficha.py` | Modificar | Adicionar import de `_dialog_notas` e seção de notas |
| `CLAUDE.md` | Modificar | Documentar arquivo de dados e fronteiras de módulo |

---

### Task 1: Adicionar NOTAS_FILE ao config

**Files:**
- Modify: `catalog/config.py:9`

- [ ] **Step 1: Inserir constante após LEITURA_FILE**

Em `catalog/config.py`, após a linha `LEITURA_FILE = "data/lista_leitura.json"` (linha 9), adicionar:

```python
NOTAS_FILE = "data/notas.json"
```

- [ ] **Step 2: Verificar importação**

```bash
python -c "from catalog.config import NOTAS_FILE; print(NOTAS_FILE)"
```

Esperado: `data/notas.json`

- [ ] **Step 3: Commit**

```bash
git add catalog/config.py
git commit -m "feat(config): adiciona NOTAS_FILE"
```

---

### Task 2: Escrever testes para catalog.notas (TDD — escrever antes de implementar)

**Files:**
- Create: `tests/test_notas.py`

- [ ] **Step 1: Criar o arquivo de testes**

```python
import pytest
import catalog.notas.storage as notas_storage


@pytest.fixture(autouse=True)
def tmp_notas_file(tmp_path, monkeypatch):
    tmp_file = tmp_path / "notas.json"
    monkeypatch.setattr(notas_storage, "_NOTAS_FILE", str(tmp_file))


def test_carregar_isbn_sem_nota():
    assert notas_storage.carregar("9781098115784") is None


def test_salvar_e_carregar():
    links = [{"url": "https://example.com", "rotulo": "Exemplo"}]
    notas_storage.salvar("9781098115784", "Boa leitura", links)
    nota = notas_storage.carregar("9781098115784")
    assert nota["anotacao"] == "Boa leitura"
    assert nota["links"] == links
    assert "data_modificacao" in nota


def test_salvar_atualiza_data_modificacao(monkeypatch):
    monkeypatch.setattr(notas_storage, "_agora", lambda: "2026-01-01T10:00:00")
    notas_storage.salvar("9781098115784", "v1", [])
    nota1 = notas_storage.carregar("9781098115784")

    monkeypatch.setattr(notas_storage, "_agora", lambda: "2026-01-01T10:00:01")
    notas_storage.salvar("9781098115784", "v2", [])
    nota2 = notas_storage.carregar("9781098115784")

    assert nota1["data_modificacao"] == "2026-01-01T10:00:00"
    assert nota2["data_modificacao"] == "2026-01-01T10:00:01"


def test_salvar_substitui_nota_existente():
    notas_storage.salvar("9781098115784", "versão 1", [])
    notas_storage.salvar(
        "9781098115784",
        "versão 2",
        [{"url": "https://x.com", "rotulo": "X"}],
    )
    nota = notas_storage.carregar("9781098115784")
    assert nota["anotacao"] == "versão 2"
    assert len(nota["links"]) == 1


def test_remover():
    notas_storage.salvar("9781098115784", "para remover", [])
    notas_storage.remover("9781098115784")
    assert notas_storage.carregar("9781098115784") is None


def test_remover_isbn_inexistente():
    notas_storage.remover("9999999999999")  # não deve lançar exceção
```

- [ ] **Step 2: Confirmar que os testes falham (módulo ainda não existe)**

```bash
pytest tests/test_notas.py -v
```

Esperado: `ModuleNotFoundError: No module named 'catalog.notas'`

---

### Task 3: Implementar catalog/notas/

**Files:**
- Create: `catalog/notas/storage.py`
- Create: `catalog/notas/__init__.py`

- [ ] **Step 1: Criar catalog/notas/storage.py**

```python
import json
import os
import threading
from datetime import datetime

import catalog.storage.git_sync as git_sync

_lock = threading.Lock()
_NOTAS_FILE = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "notas.json")
)


def _agora() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _carregar_raw() -> dict:
    try:
        with open(_NOTAS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, FileNotFoundError):
        return {"notas": {}}


def _salvar_raw(data: dict) -> None:
    os.makedirs(os.path.dirname(_NOTAS_FILE), exist_ok=True)
    with open(_NOTAS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def carregar(isbn: str) -> dict | None:
    return _carregar_raw()["notas"].get(isbn)


def salvar(isbn: str, anotacao: str, links: list[dict]) -> None:
    with _lock:
        data = _carregar_raw()
        data["notas"][isbn] = {
            "anotacao": anotacao,
            "links": links,
            "data_modificacao": _agora(),
        }
        _salvar_raw(data)
    git_sync.commit_se_houver_mudancas(
        f"notas: {isbn} – anotação atualizada", arquivos=[_NOTAS_FILE]
    )


def remover(isbn: str) -> None:
    modificado = False
    with _lock:
        data = _carregar_raw()
        if isbn in data["notas"]:
            del data["notas"][isbn]
            _salvar_raw(data)
            modificado = True
    if modificado:
        git_sync.commit_se_houver_mudancas(
            f"notas: {isbn} – nota removida", arquivos=[_NOTAS_FILE]
        )
```

- [ ] **Step 2: Criar catalog/notas/__init__.py**

```python
from .storage import carregar, remover, salvar

__all__ = ["carregar", "remover", "salvar"]
```

- [ ] **Step 3: Executar os testes**

```bash
pytest tests/test_notas.py -v
```

Esperado: 6 testes com status PASSED.

- [ ] **Step 4: Executar a suite completa para checar regressões**

```bash
pytest -v
```

Esperado: todos os testes existentes continuam passando.

- [ ] **Step 5: Commit**

```bash
git add catalog/notas/ tests/test_notas.py
git commit -m "feat(notas): módulo catalog/notas com CRUD e testes"
```

---

### Task 4: Adicionar _dialog_notas a ui/utils.py

**Files:**
- Modify: `ui/utils.py:305` (após o fim de `_dialog_editar`)

- [ ] **Step 1: Adicionar import de catalog.notas no topo de ui/utils.py**

Logo após a linha `from catalog.storage import carregar_todos_registros, reescrever_registros` (linha 18), adicionar:

```python
import catalog.notas as notas
```

- [ ] **Step 2: Adicionar _dialog_notas após _dialog_editar**

Após o fim da função `_dialog_editar` (após a linha `st.rerun()` que fecha o `if submitted:`, em torno da linha 305), adicionar:

```python
@st.dialog("📝 Editar anotações", width="large")
def _dialog_notas(isbn: str, nota_atual: dict | None) -> None:
    key = f"notas_links_{isbn}"
    if key not in st.session_state:
        st.session_state[key] = [dict(l) for l in (nota_atual or {}).get("links", [])]

    anotacao = st.text_area(
        "Anotação",
        value=(nota_atual or {}).get("anotacao", ""),
        height=200,
        key=f"{key}_anotacao",
        placeholder="Escreva sua resenha ou anotações sobre o livro...",
    )

    st.markdown("**Links externos**")
    indices_remover = []
    for i, link in enumerate(st.session_state[key]):
        c1, c2, c3 = st.columns([3, 2, 1])
        link["url"] = c1.text_input(
            "URL",
            value=link.get("url", ""),
            key=f"{key}_url_{i}",
            label_visibility="collapsed",
            placeholder="https://...",
        )
        link["rotulo"] = c2.text_input(
            "Rótulo",
            value=link.get("rotulo", ""),
            key=f"{key}_rot_{i}",
            label_visibility="collapsed",
            placeholder="Rótulo (opcional)",
        )
        if c3.button("✕", key=f"{key}_rm_{i}"):
            indices_remover.append(i)

    for i in reversed(indices_remover):
        st.session_state[key].pop(i)
        st.rerun()

    if st.button("＋ Adicionar link"):
        st.session_state[key].append({"url": "", "rotulo": ""})
        st.rerun()

    st.divider()
    if st.button("💾 Salvar", type="primary", use_container_width=True):
        links_validos = [
            l for l in st.session_state[key] if l.get("url", "").strip()
        ]
        notas.salvar(isbn, anotacao, links_validos)
        del st.session_state[key]
        st.rerun()
```

- [ ] **Step 3: Verificar importação de utils sem erro**

```bash
python -c "from ui.utils import _dialog_notas; print('ok')"
```

Esperado: `ok`

---

### Task 5: Adicionar seção de notas em ui/pages/ficha.py

**Files:**
- Modify: `ui/pages/ficha.py:8-18` (imports)
- Modify: `ui/pages/ficha.py:155-157` (inserção da seção)

- [ ] **Step 1: Adicionar _dialog_notas ao bloco de imports de ui.utils**

No topo de `ui/pages/ficha.py`, no bloco `from ui.utils import (...)` (linhas 8-18), adicionar `_dialog_notas` à lista:

```python
from ui.utils import (
    _IDIOMA_NORM,
    _badge,
    _badge_capa,
    _badge_etiqueta,
    _carregar,
    _dialog_editar,
    _dialog_login,
    _dialog_notas,
    _is_autenticado,
    _session_bar,
)
```

- [ ] **Step 2: Adicionar import de catalog.notas no topo de ficha.py**

No topo de `ui/pages/ficha.py`, após a linha `import catalog.reading.storage as reading_storage`, adicionar:

```python
import catalog.notas as notas
```

- [ ] **Step 3: Inserir seção de notas no corpo da ficha**

No corpo da ficha, dentro do bloco `with col_info:`, após o fim da seção de lista de leitura (após a linha `st.rerun()` do botão "💾 Salvar progresso", em torno da linha 154) e antes do `st.divider()` que precede o botão "Editar este livro" (linha 157), inserir:

```python
    st.divider()
    st.markdown("**📝 Anotações**")

    nota = notas.carregar(isbn)

    if nota and (nota.get("anotacao") or nota.get("links")):
        if nota.get("anotacao"):
            st.markdown(nota["anotacao"])
        for link in nota.get("links", []):
            rotulo = link.get("rotulo") or link["url"][:60]
            st.link_button(rotulo, link["url"])
    else:
        st.caption("Nenhuma anotação ainda.")

    if _is_autenticado():
        if st.button("✏️ Editar anotações", key=f"btn_notas_{isbn}"):
            _dialog_notas(isbn, nota)
    else:
        st.caption("🔒 Faça login para adicionar anotações.")
```

- [ ] **Step 4: Verificar que a UI sobe sem erro**

```bash
streamlit run ui/app.py &
```

Aguardar o log `You can now view your Streamlit app in your browser` e verificar ausência de `ImportError` ou `SyntaxError`.

- [ ] **Step 5: Testar manualmente o fluxo completo**

1. Abrir a UI no browser (http://localhost:8501)
2. Navegar ao Acervo, clicar em qualquer livro → ficha
3. Verificar que a seção "📝 Anotações" aparece com "Nenhuma anotação ainda."
4. Fazer login (botão cadeado → senha)
5. Clicar "✏️ Editar anotações"
6. Digitar uma anotação e adicionar um link (URL + rótulo)
7. Clicar "💾 Salvar"
8. Verificar que a anotação e o link aparecem na ficha
9. Verificar que `data/notas.json` foi criado com a estrutura correta

- [ ] **Step 6: Commit**

```bash
git add ui/pages/ficha.py ui/utils.py
git commit -m "feat(ui): seção de notas e resenhas na ficha do livro"
```

---

### Task 6: Atualizar CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Adicionar notas.json na tabela de arquivos de dados**

Na seção "Arquivos de dados", adicionar uma linha:

```
| `data/notas.json` | Anotações e links externos por livro, indexados por ISBN |
```

- [ ] **Step 2: Adicionar catalog.notas nas fronteiras de módulo**

Na seção "Fronteiras de módulo", adicionar a linha:

```
| `catalog.notas` | `catalog.config`, `catalog.storage.git_sync`, stdlib | `catalog.scanning`, `catalog.metadata`, `catalog.reading`, `main` |
```

E na linha de `ui.app`, adicionar `catalog.notas` na coluna "Pode importar de":

```
| `ui.app` | `catalog.storage`, `catalog.organizer`, `catalog.series`, `catalog.notas`, streamlit | `catalog.metadata`, `catalog.scanning`, `main` |
```

- [ ] **Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs(claude): adiciona catalog.notas nas fronteiras e data/notas.json"
```

---

## Verificação final

- [ ] Rodar suite completa de testes:

```bash
pytest -v
```

Esperado: todos os testes passando, incluindo os 6 novos de `test_notas.py`.

- [ ] Verificar estrutura de `data/notas.json` após uso manual:

```bash
python -c "import json; print(json.dumps(json.load(open('data/notas.json')), indent=2, ensure_ascii=False))"
```

Esperado: JSON com chave `"notas"` contendo os ISBNs editados.
