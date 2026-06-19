# Lista de Leitura — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar um módulo de lista de leitura com fila ordenada, rastreamento de progresso por página, 4 status (na_fila / lendo / lido / abandonado), e UI dedicada no Streamlit.

**Architecture:** Novo arquivo `data/lista_leitura.json` análogo ao `estantes.json`, novo módulo `catalog/reading/storage.py` com CRUD thread-safe, nova página `ui/pages/leitura.py` com três seções (lendo agora, fila, histórico), e integração de status/progresso na página de ficha existente.

**Tech Stack:** Python stdlib (json, threading, datetime), Streamlit, pytest + monkeypatch

---

## File Map

| Arquivo | Ação |
|---|---|
| `catalog/config.py` | Modificar — adicionar `LEITURA_FILE` |
| `catalog/reading/__init__.py` | Criar — exporta API pública |
| `catalog/reading/storage.py` | Criar — CRUD do `lista_leitura.json` |
| `ui/app.py` | Modificar — registrar nova página |
| `ui/pages/leitura.py` | Criar — página dedicada |
| `ui/pages/ficha.py` | Modificar — seção de status/progresso |
| `tests/test_reading.py` | Criar — testes do módulo reading |

---

## Task 1: Adicionar `LEITURA_FILE` ao config

**Files:**
- Modify: `catalog/config.py`

- [ ] **Step 1: Adicionar a constante**

Abrir `catalog/config.py` e adicionar após `CAPAS_MANUAIS_FILE`:

```python
LEITURA_FILE = "data/lista_leitura.json"
```

- [ ] **Step 2: Verificar que o projeto ainda importa sem erros**

```bash
python -c "from catalog.config import LEITURA_FILE; print(LEITURA_FILE)"
```

Esperado: `data/lista_leitura.json`

- [ ] **Step 3: Commit**

```bash
git add catalog/config.py
git commit -m "feat(reading): add LEITURA_FILE constant to config"
```

---

## Task 2: Criar `catalog/reading/storage.py` com TDD

**Files:**
- Create: `catalog/reading/__init__.py`
- Create: `catalog/reading/storage.py`
- Test: `tests/test_reading.py`

- [ ] **Step 1: Escrever os testes (todos vão falhar)**

Criar `tests/test_reading.py`:

```python
import pytest
import catalog.config as cfg
import catalog.reading.storage as storage


@pytest.fixture(autouse=True)
def _isolate(tmp_path, monkeypatch):
    leitura_file = str(tmp_path / "data" / "lista_leitura.json")
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(cfg, "LEITURA_FILE", leitura_file)


def test_carregar_vazio():
    assert storage.carregar() == []


def test_adicionar_cria_item_na_fila():
    storage.adicionar("9781098115784")
    itens = storage.carregar()
    assert len(itens) == 1
    assert itens[0]["isbn"] == "9781098115784"
    assert itens[0]["status"] == "na_fila"
    assert itens[0]["ordem"] == 1
    assert itens[0]["progresso_paginas"] == 0


def test_adicionar_duplicado_levanta_value_error():
    storage.adicionar("9781098115784")
    with pytest.raises(ValueError, match="já está na lista"):
        storage.adicionar("9781098115784")


def test_adicionar_multiplos_incrementa_ordem():
    storage.adicionar("9781098115784")
    storage.adicionar("9780201633610")
    itens = storage.carregar()
    na_fila = sorted(
        [i for i in itens if i["status"] == "na_fila"], key=lambda i: i["ordem"]
    )
    assert na_fila[0]["isbn"] == "9781098115784"
    assert na_fila[1]["isbn"] == "9780201633610"
    assert na_fila[1]["ordem"] == 2


def test_atualizar_status_para_lendo_preenche_data_inicio():
    storage.adicionar("9781098115784")
    storage.atualizar_status("9781098115784", "lendo")
    item = storage.carregar()[0]
    assert item["status"] == "lendo"
    assert item["data_inicio"] is not None


def test_atualizar_status_para_lido_preenche_data_conclusao():
    storage.adicionar("9781098115784")
    storage.atualizar_status("9781098115784", "lendo")
    storage.atualizar_status("9781098115784", "lido")
    item = storage.carregar()[0]
    assert item["status"] == "lido"
    assert item["data_conclusao"] is not None


def test_atualizar_status_para_abandonado_preenche_data_abandono():
    storage.adicionar("9781098115784")
    storage.atualizar_status("9781098115784", "lendo")
    storage.atualizar_status("9781098115784", "abandonado")
    item = storage.carregar()[0]
    assert item["status"] == "abandonado"
    assert item["data_abandono"] is not None


def test_atualizar_status_retorno_para_na_fila_mantem_progresso():
    storage.adicionar("9781098115784")
    storage.atualizar_status("9781098115784", "lendo")
    storage.atualizar_progresso("9781098115784", 80)
    storage.atualizar_status("9781098115784", "na_fila")
    item = storage.carregar()[0]
    assert item["status"] == "na_fila"
    assert item["progresso_paginas"] == 80


def test_atualizar_status_compacta_ordem_ao_sair_da_fila():
    storage.adicionar("9781098115784")
    storage.adicionar("9780201633610")
    storage.adicionar("9780596516178")
    storage.atualizar_status("9781098115784", "lendo")
    itens = storage.carregar()
    na_fila = sorted(
        [i for i in itens if i["status"] == "na_fila"], key=lambda i: i["ordem"]
    )
    assert na_fila[0]["isbn"] == "9780201633610"
    assert na_fila[0]["ordem"] == 1
    assert na_fila[1]["isbn"] == "9780596516178"
    assert na_fila[1]["ordem"] == 2


def test_atualizar_progresso():
    storage.adicionar("9781098115784")
    storage.atualizar_status("9781098115784", "lendo")
    storage.atualizar_progresso("9781098115784", 150)
    item = storage.carregar()[0]
    assert item["progresso_paginas"] == 150


def test_reordenar_cima():
    storage.adicionar("9781098115784")
    storage.adicionar("9780201633610")
    storage.reordenar("9780201633610", "cima")
    na_fila = sorted(
        [i for i in storage.carregar() if i["status"] == "na_fila"],
        key=lambda i: i["ordem"],
    )
    assert na_fila[0]["isbn"] == "9780201633610"
    assert na_fila[1]["isbn"] == "9781098115784"


def test_reordenar_baixo():
    storage.adicionar("9781098115784")
    storage.adicionar("9780201633610")
    storage.reordenar("9781098115784", "baixo")
    na_fila = sorted(
        [i for i in storage.carregar() if i["status"] == "na_fila"],
        key=lambda i: i["ordem"],
    )
    assert na_fila[0]["isbn"] == "9780201633610"
    assert na_fila[1]["isbn"] == "9781098115784"


def test_reordenar_sem_efeito_no_topo():
    storage.adicionar("9781098115784")
    storage.adicionar("9780201633610")
    storage.reordenar("9781098115784", "cima")
    na_fila = sorted(
        [i for i in storage.carregar() if i["status"] == "na_fila"],
        key=lambda i: i["ordem"],
    )
    assert na_fila[0]["isbn"] == "9781098115784"


def test_reordenar_sem_efeito_no_final():
    storage.adicionar("9781098115784")
    storage.adicionar("9780201633610")
    storage.reordenar("9780201633610", "baixo")
    na_fila = sorted(
        [i for i in storage.carregar() if i["status"] == "na_fila"],
        key=lambda i: i["ordem"],
    )
    assert na_fila[1]["isbn"] == "9780201633610"


def test_remover():
    storage.adicionar("9781098115784")
    storage.adicionar("9780201633610")
    storage.remover("9781098115784")
    itens = storage.carregar()
    assert len(itens) == 1
    assert itens[0]["isbn"] == "9780201633610"


def test_remover_compacta_ordem():
    storage.adicionar("9781098115784")
    storage.adicionar("9780201633610")
    storage.adicionar("9780596516178")
    storage.remover("9780201633610")
    na_fila = sorted(
        [i for i in storage.carregar() if i["status"] == "na_fila"],
        key=lambda i: i["ordem"],
    )
    assert na_fila[0]["isbn"] == "9781098115784"
    assert na_fila[0]["ordem"] == 1
    assert na_fila[1]["isbn"] == "9780596516178"
    assert na_fila[1]["ordem"] == 2
```

- [ ] **Step 2: Confirmar que os testes falham**

```bash
pytest tests/test_reading.py -v 2>&1 | head -20
```

Esperado: `ModuleNotFoundError: No module named 'catalog.reading'`

- [ ] **Step 3: Criar `catalog/reading/__init__.py`**

```python
from .storage import (
    adicionar,
    atualizar_progresso,
    atualizar_status,
    carregar,
    reordenar,
    remover,
)

__all__ = [
    "adicionar",
    "atualizar_progresso",
    "atualizar_status",
    "carregar",
    "reordenar",
    "remover",
]
```

- [ ] **Step 4: Criar `catalog/reading/storage.py`**

```python
import json
import threading
from datetime import datetime
from pathlib import Path

import catalog.config as cfg

_lock = threading.Lock()


def _agora() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def _carregar_raw() -> dict:
    path = Path(cfg.LEITURA_FILE)
    if not path.exists():
        return {"itens": []}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _salvar_raw(data: dict) -> None:
    path = Path(cfg.LEITURA_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _compactar_ordem(itens: list) -> None:
    na_fila = sorted(
        [i for i in itens if i["status"] == "na_fila"],
        key=lambda i: i["ordem"],
    )
    for idx, item in enumerate(na_fila, start=1):
        item["ordem"] = idx


def carregar() -> list:
    return _carregar_raw()["itens"]


def adicionar(isbn: str) -> None:
    with _lock:
        data = _carregar_raw()
        itens = data["itens"]
        if any(item["isbn"] == isbn for item in itens):
            raise ValueError(f"ISBN {isbn} já está na lista de leitura")
        na_fila = [item for item in itens if item["status"] == "na_fila"]
        itens.append({
            "isbn": isbn,
            "status": "na_fila",
            "ordem": len(na_fila) + 1,
            "progresso_paginas": 0,
            "data_adicao": _agora(),
            "data_inicio": None,
            "data_conclusao": None,
            "data_abandono": None,
        })
        _salvar_raw(data)


def atualizar_status(isbn: str, novo_status: str) -> None:
    with _lock:
        data = _carregar_raw()
        item = next((i for i in data["itens"] if i["isbn"] == isbn), None)
        if item is None:
            raise ValueError(f"ISBN {isbn} não encontrado na lista de leitura")
        saiu_da_fila = item["status"] == "na_fila" and novo_status != "na_fila"
        item["status"] = novo_status
        agora = _agora()
        if novo_status == "lendo" and item["data_inicio"] is None:
            item["data_inicio"] = agora
        elif novo_status == "lido":
            item["data_conclusao"] = agora
        elif novo_status == "abandonado":
            item["data_abandono"] = agora
        if saiu_da_fila:
            _compactar_ordem(data["itens"])
        _salvar_raw(data)


def atualizar_progresso(isbn: str, pagina: int) -> None:
    with _lock:
        data = _carregar_raw()
        item = next((i for i in data["itens"] if i["isbn"] == isbn), None)
        if item is None:
            raise ValueError(f"ISBN {isbn} não encontrado na lista de leitura")
        item["progresso_paginas"] = pagina
        _salvar_raw(data)


def reordenar(isbn: str, direcao: str) -> None:
    with _lock:
        data = _carregar_raw()
        na_fila = sorted(
            [i for i in data["itens"] if i["status"] == "na_fila"],
            key=lambda i: i["ordem"],
        )
        idx = next(
            (i for i, item in enumerate(na_fila) if item["isbn"] == isbn), None
        )
        if idx is None:
            return
        if direcao == "cima" and idx > 0:
            na_fila[idx]["ordem"], na_fila[idx - 1]["ordem"] = (
                na_fila[idx - 1]["ordem"],
                na_fila[idx]["ordem"],
            )
        elif direcao == "baixo" and idx < len(na_fila) - 1:
            na_fila[idx]["ordem"], na_fila[idx + 1]["ordem"] = (
                na_fila[idx + 1]["ordem"],
                na_fila[idx]["ordem"],
            )
        _salvar_raw(data)


def remover(isbn: str) -> None:
    with _lock:
        data = _carregar_raw()
        data["itens"] = [i for i in data["itens"] if i["isbn"] != isbn]
        _compactar_ordem(data["itens"])
        _salvar_raw(data)
```

- [ ] **Step 5: Rodar os testes e confirmar que passam**

```bash
pytest tests/test_reading.py -v
```

Esperado: todos os 16 testes `PASSED`

- [ ] **Step 6: Commit**

```bash
git add catalog/reading/__init__.py catalog/reading/storage.py tests/test_reading.py
git commit -m "feat(reading): add catalog/reading storage module with TDD"
```

---

## Task 3: Criar `ui/pages/leitura.py` e registrar no menu

**Files:**
- Create: `ui/pages/leitura.py`
- Modify: `ui/app.py`

- [ ] **Step 1: Criar `ui/pages/leitura.py`**

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st
import catalog.reading.storage as reading_storage
from catalog.storage import carregar_todos_registros
from ui.utils import _dialog_login, _is_autenticado

st.title("📋 Lista de Leitura")

itens = reading_storage.carregar()
registros = carregar_todos_registros()
livros_por_isbn = {r["isbn"]: r for r in registros}
autenticado = _is_autenticado()

with st.sidebar:
    st.page_link("pages/acervo.py", label="📚 Acervo")
    st.page_link("pages/estantes.py", label="🗂️ Estantes")
    st.page_link("pages/leitura.py", label="📋 Lista de Leitura")
    st.page_link("pages/sobre.py", label="📖 Sobre")
    st.divider()
    if autenticado:
        if st.button("🔓 Sair do modo edição", use_container_width=True):
            st.session_state["autenticado"] = False
            st.rerun()
    else:
        if st.button("🔒 Modo edição", use_container_width=True):
            _dialog_login()

lendo = [i for i in itens if i["status"] == "lendo"]
na_fila = sorted(
    [i for i in itens if i["status"] == "na_fila"], key=lambda i: i["ordem"]
)
historico = sorted(
    [i for i in itens if i["status"] in ("lido", "abandonado")],
    key=lambda i: i.get("data_conclusao") or i.get("data_abandono") or "",
    reverse=True,
)

# --- Seção 1: Lendo agora ---
st.subheader("📖 Lendo agora")
if not lendo:
    st.info("Nenhum livro em andamento. Comece um livro da fila abaixo.")
else:
    for item in lendo:
        livro = livros_por_isbn.get(item["isbn"], {})
        titulo = livro.get("titulo") or item["isbn"]
        autores = livro.get("autores", "")
        paginas_total = int(livro.get("paginas") or 0)
        progresso = item["progresso_paginas"]

        with st.container(border=True):
            col_capa, col_info = st.columns([1, 4])
            with col_capa:
                capa = livro.get("capa_url", "")
                if capa:
                    st.image(capa, width=80)
                else:
                    st.markdown("📖")
            with col_info:
                st.markdown(f"**{titulo}**")
                if autores:
                    st.caption(autores)
                if paginas_total:
                    pct = min(100, round(progresso / paginas_total * 100))
                    st.progress(
                        pct / 100,
                        text=f"{progresso} / {paginas_total} páginas ({pct}%)",
                    )
                else:
                    st.caption(f"{progresso} páginas lidas")

                if autenticado:
                    nova_pagina = st.number_input(
                        "Página atual",
                        min_value=0,
                        max_value=paginas_total if paginas_total else 9999,
                        value=progresso,
                        key=f"prog_{item['isbn']}",
                    )
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        if st.button(
                            "💾 Salvar",
                            key=f"salvar_{item['isbn']}",
                            use_container_width=True,
                        ):
                            reading_storage.atualizar_progresso(item["isbn"], nova_pagina)
                            st.rerun()
                    with col_b:
                        if st.button(
                            "✅ Lido",
                            key=f"lido_{item['isbn']}",
                            use_container_width=True,
                        ):
                            reading_storage.atualizar_status(item["isbn"], "lido")
                            st.rerun()
                    with col_c:
                        if st.button(
                            "🚫 Abandonar",
                            key=f"abandonar_{item['isbn']}",
                            use_container_width=True,
                        ):
                            reading_storage.atualizar_status(item["isbn"], "abandonado")
                            st.rerun()

# --- Seção 2: Na fila ---
st.divider()
st.subheader("📋 Na fila")
if not na_fila:
    st.info("A fila está vazia.")
else:
    for item in na_fila:
        livro = livros_por_isbn.get(item["isbn"], {})
        titulo = livro.get("titulo") or item["isbn"]
        autores = livro.get("autores", "")

        col_pos, col_capa, col_info, col_acoes = st.columns([0.5, 0.8, 4, 2.5])
        with col_pos:
            st.markdown(f"**{item['ordem']}.**")
        with col_capa:
            capa = livro.get("capa_url", "")
            if capa:
                st.image(capa, width=50)
        with col_info:
            st.markdown(f"**{titulo}**")
            if autores:
                st.caption(autores)
        with col_acoes:
            if autenticado:
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    if st.button("▲", key=f"up_{item['isbn']}", use_container_width=True):
                        reading_storage.reordenar(item["isbn"], "cima")
                        st.rerun()
                with c2:
                    if st.button("▼", key=f"down_{item['isbn']}", use_container_width=True):
                        reading_storage.reordenar(item["isbn"], "baixo")
                        st.rerun()
                with c3:
                    if st.button(
                        "▶",
                        key=f"comecar_{item['isbn']}",
                        use_container_width=True,
                        help="Começar a ler",
                    ):
                        reading_storage.atualizar_status(item["isbn"], "lendo")
                        st.rerun()
                with c4:
                    if st.button(
                        "✕",
                        key=f"remover_{item['isbn']}",
                        use_container_width=True,
                        help="Remover da fila",
                    ):
                        reading_storage.remover(item["isbn"])
                        st.rerun()

# --- Seção 3: Histórico ---
st.divider()
with st.expander(f"📚 Histórico ({len(historico)} livros)"):
    if not historico:
        st.info("Nenhum livro lido ou abandonado ainda.")
    else:
        rows = []
        for item in historico:
            livro = livros_por_isbn.get(item["isbn"], {})
            paginas_total = int(livro.get("paginas") or 0)
            data_fim = item.get("data_conclusao") or item.get("data_abandono") or "—"
            rows.append({
                "Título": livro.get("titulo") or item["isbn"],
                "Autor": livro.get("autores", "—"),
                "Status": "✅ Lido" if item["status"] == "lido" else "🚫 Abandonado",
                "Data": data_fim[:10] if data_fim != "—" else "—",
                "Progresso": (
                    f"{item['progresso_paginas']} / {paginas_total}"
                    if paginas_total
                    else str(item["progresso_paginas"])
                ),
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)
```

- [ ] **Step 2: Registrar a página em `ui/app.py`**

Abrir `ui/app.py` e modificar a lista de páginas para incluir `leitura.py`:

```python
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
```

- [ ] **Step 3: Adicionar o link do sidebar nas páginas acervo e estantes**

Em `ui/pages/acervo.py`, dentro do bloco `with st.sidebar:`, adicionar após o link de Estantes:

```python
st.page_link("pages/leitura.py", label="📋 Lista de Leitura")
```

Em `ui/pages/estantes.py`, fazer o mesmo (verificar o bloco sidebar e inserir o link na posição equivalente).

- [ ] **Step 4: Commit**

```bash
git add ui/pages/leitura.py ui/app.py ui/pages/acervo.py ui/pages/estantes.py
git commit -m "feat(reading): add lista de leitura page and register in navigation"
```

---

## Task 4: Integrar status e progresso na ficha do livro

**Files:**
- Modify: `ui/pages/ficha.py`

- [ ] **Step 1: Adicionar importação no topo de `ui/pages/ficha.py`**

Após as importações existentes, adicionar:

```python
import catalog.reading.storage as reading_storage
```

- [ ] **Step 2: Adicionar seção de lista de leitura no corpo da ficha**

Ainda dentro do bloco `with col_info:`, após o último `st.divider()` (linha do bloco de edição) e **antes** do bloco `if _is_autenticado(): st.button("✏️ Editar...")`, inserir:

```python
    st.divider()
    st.markdown("**📋 Lista de Leitura**")

    itens_leitura = reading_storage.carregar()
    item_leitura = next((i for i in itens_leitura if i["isbn"] == isbn), None)
    paginas_total = int(registro.get("paginas") or 0)

    STATUS_LABELS = {
        "na_fila": "📋 Na fila",
        "lendo": "📖 Lendo",
        "lido": "✅ Lido",
        "abandonado": "🚫 Abandonado",
    }

    if item_leitura is None:
        if _is_autenticado():
            if st.button("➕ Adicionar à fila de leitura", key=f"add_leitura_{isbn}"):
                reading_storage.adicionar(isbn)
                st.rerun()
        else:
            st.caption("🔒 Faça login para adicionar à lista de leitura.")
    else:
        st.markdown(
            f"Status: **{STATUS_LABELS.get(item_leitura['status'], item_leitura['status'])}**"
        )
        progresso = item_leitura["progresso_paginas"]
        if paginas_total:
            pct = min(100, round(progresso / paginas_total * 100))
            st.progress(
                pct / 100,
                text=f"{progresso} / {paginas_total} páginas ({pct}%)",
            )
        elif progresso:
            st.caption(f"{progresso} páginas lidas")

        if _is_autenticado() and item_leitura["status"] == "lendo":
            nova_pagina = st.number_input(
                "Página atual",
                min_value=0,
                max_value=paginas_total if paginas_total else 9999,
                value=progresso,
                key=f"prog_ficha_{isbn}",
            )
            if st.button("💾 Salvar progresso", key=f"salvar_ficha_{isbn}"):
                reading_storage.atualizar_progresso(isbn, nova_pagina)
                st.rerun()

    st.divider()
```

- [ ] **Step 3: Commit**

```bash
git add ui/pages/ficha.py
git commit -m "feat(reading): show reading status and progress in ficha page"
```

---

## Task 5: Smoke test manual

- [ ] **Step 1: Rodar toda a suíte de testes**

```bash
pytest -v
```

Esperado: todos os testes `PASSED` (nenhuma regressão)

- [ ] **Step 2: Iniciar a UI e verificar o fluxo completo**

```bash
streamlit run ui/app.py
```

Verificar:
1. O menu lateral mostra "📋 Lista de Leitura"
2. Acessar a página — fila vazia aparece corretamente
3. Na ficha de um livro (modo edição ativo), clicar "➕ Adicionar à fila de leitura" — livro aparece na fila
4. Na página Lista de Leitura, clicar "▶" (Começar a ler) — livro passa para "Lendo agora"
5. Salvar progresso de páginas — barra atualiza
6. Marcar como lido — livro vai para Histórico
7. Reabrir a ficha do livro lido — mostra "✅ Lido" com progresso

- [ ] **Step 3: Commit final se houver ajustes menores**

```bash
git add -p   # revisar apenas o que mudou
git commit -m "fix(reading): adjustments after manual smoke test"
```
