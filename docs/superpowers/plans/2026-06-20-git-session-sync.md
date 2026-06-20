# Git Session Sync — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cada sessão de uso da UI Streamlit cria um branch `data/YYYY-MM-DD`, cada operação de escrita gera um commit nesse branch, e um botão "Finalizar sessão" faz squash + abre uma PR para `main`.

**Architecture:** Um novo módulo `catalog/storage/git_sync.py` encapsula toda a lógica git (via subprocess). Os módulos de escrita existentes chamam `git_sync.commit_se_houver_mudancas()` após persistir. A UI ganha um componente `_session_bar()` em `ui/utils.py` que mostra o estado da sessão e expõe o botão de finalização.

**Tech Stack:** Python stdlib (`subprocess`, `datetime`, `pathlib`), `gh` CLI para criar PRs, `pytest` + `unittest.mock` para testes.

---

## Mapa de arquivos

| Ação | Arquivo | Responsabilidade |
|---|---|---|
| Criar | `catalog/storage/git_sync.py` | Toda a lógica git: branch, commit, squash, PR |
| Criar | `tests/test_git_sync.py` | Testes unitários do módulo git_sync |
| Modificar | `tests/conftest.py` | Adicionar fixture `mock_git_sync` autouse |
| Modificar | `catalog/storage/persistence.py` | Commit após `reescrever_registros` |
| Modificar | `catalog/reading/storage.py` | Commit após cada função de escrita |
| Modificar | `catalog/organizer/storage.py` | Commit após `salvar_config` |
| Modificar | `ui/app.py` | Chamar `garantir_branch_sessao()` no startup |
| Modificar | `ui/utils.py` | Adicionar `_session_bar()` |
| Modificar | `ui/pages/acervo.py` | Chamar `_session_bar()` |
| Modificar | `ui/pages/ficha.py` | Chamar `_session_bar()` |
| Modificar | `ui/pages/estantes.py` | Chamar `_session_bar()` |
| Modificar | `ui/pages/leitura.py` | Chamar `_session_bar()` |

---

## Task 1: `catalog/storage/git_sync.py`

**Files:**
- Create: `catalog/storage/git_sync.py`
- Create: `tests/test_git_sync.py`

- [ ] **Step 1: Escrever os testes**

Criar `tests/test_git_sync.py`:

```python
from datetime import date
from unittest.mock import call, patch
import subprocess

import pytest

import catalog.storage.git_sync as git_sync


class TestBranchAtual:
    def test_retorna_nome_do_branch(self):
        with patch.object(git_sync, "_git_output", return_value="main"):
            assert git_sync.branch_atual() == "main"


class TestGarantirBranchSessao:
    def test_ja_em_branch_sessao_retorna_sem_criar(self):
        with patch.object(git_sync, "_git_output", return_value="data/2026-06-20"), \
             patch.object(git_sync, "_git") as mock_git:
            result = git_sync.garantir_branch_sessao()
        assert result == "data/2026-06-20"
        mock_git.assert_not_called()

    def test_em_main_cria_branch_do_dia(self):
        esperado = f"data/{date.today().isoformat()}"
        with patch.object(git_sync, "_git_output", return_value="main"), \
             patch.object(git_sync, "_git") as mock_git:
            result = git_sync.garantir_branch_sessao()
        assert result == esperado
        mock_git.assert_called_once_with("checkout", "-b", esperado)

    def test_branch_ja_existe_faz_checkout(self):
        esperado = f"data/{date.today().isoformat()}"
        with patch.object(git_sync, "_git_output", return_value="main"), \
             patch.object(git_sync, "_git", side_effect=[
                 subprocess.CalledProcessError(128, "git"),  # -b falha
                 None,  # checkout sem -b ok
             ]) as mock_git:
            result = git_sync.garantir_branch_sessao()
        assert result == esperado
        assert mock_git.call_args_list == [
            call("checkout", "-b", esperado),
            call("checkout", esperado),
        ]


class TestCommitSeHouverMudancas:
    def test_sem_mudancas_retorna_false(self):
        with patch.object(git_sync, "_git"), \
             patch.object(git_sync, "_tem_mudancas_staged", return_value=False):
            result = git_sync.commit_se_houver_mudancas("edit: Livro")
        assert result is False

    def test_com_mudancas_commita_e_retorna_true(self):
        with patch.object(git_sync, "_git") as mock_git, \
             patch.object(git_sync, "_tem_mudancas_staged", return_value=True):
            result = git_sync.commit_se_houver_mudancas("edit: Livro Teste")
        assert result is True
        mock_git.assert_any_call("commit", "-m", "edit: Livro Teste")

    def test_sempre_faz_git_add_data(self):
        with patch.object(git_sync, "_git") as mock_git, \
             patch.object(git_sync, "_tem_mudancas_staged", return_value=False):
            git_sync.commit_se_houver_mudancas("qualquer")
        mock_git.assert_called_once_with("add", "data/")


class TestContarCommitsSessao:
    def test_retorna_inteiro(self):
        with patch.object(git_sync, "_git_output", return_value="3"):
            assert git_sync.contar_commits_sessao() == 3

    def test_sem_commits_retorna_zero(self):
        with patch.object(git_sync, "_git_output", return_value="0"):
            assert git_sync.contar_commits_sessao() == 0

    def test_erro_git_retorna_zero(self):
        with patch.object(git_sync, "_git_output",
                          side_effect=subprocess.CalledProcessError(1, "git")):
            assert git_sync.contar_commits_sessao() == 0


class TestFinalizarSessao:
    def test_sem_commits_levanta_value_error(self):
        with patch.object(git_sync, "contar_commits_sessao", return_value=0):
            with pytest.raises(ValueError, match="Nenhuma alteração"):
                git_sync.finalizar_sessao()

    def test_squash_e_pr_retorna_url(self):
        url_esperada = "https://github.com/user/repo/pull/42"
        with patch.object(git_sync, "contar_commits_sessao", return_value=2), \
             patch.object(git_sync, "branch_atual", return_value="data/2026-06-20"), \
             patch.object(git_sync, "_git") as mock_git, \
             patch.object(git_sync, "_gh", return_value=url_esperada):
            url = git_sync.finalizar_sessao()
        assert url == url_esperada
        mock_git.assert_any_call("reset", "--soft", "main")
        mock_git.assert_any_call("push", "-u", "origin", "data/2026-06-20")

    def test_mensagem_singular(self):
        with patch.object(git_sync, "contar_commits_sessao", return_value=1), \
             patch.object(git_sync, "branch_atual", return_value="data/2026-06-20"), \
             patch.object(git_sync, "_git"), \
             patch.object(git_sync, "_gh", return_value="https://example.com") as mock_gh:
            git_sync.finalizar_sessao()
        titulo = mock_gh.call_args.args[2]  # --title value
        assert "1 alteração" in titulo

    def test_mensagem_plural(self):
        with patch.object(git_sync, "contar_commits_sessao", return_value=5), \
             patch.object(git_sync, "branch_atual", return_value="data/2026-06-20"), \
             patch.object(git_sync, "_git"), \
             patch.object(git_sync, "_gh", return_value="https://example.com") as mock_gh:
            git_sync.finalizar_sessao()
        titulo = mock_gh.call_args.args[2]
        assert "5 alterações" in titulo

    def test_gh_nao_instalado_levanta_runtime_error(self):
        with patch.object(git_sync, "contar_commits_sessao", return_value=1), \
             patch.object(git_sync, "branch_atual", return_value="data/2026-06-20"), \
             patch.object(git_sync, "_git"), \
             patch.object(git_sync, "_gh",
                          side_effect=RuntimeError("gh CLI não encontrado")):
            with pytest.raises(RuntimeError, match="gh CLI"):
                git_sync.finalizar_sessao()
```

- [ ] **Step 2: Rodar os testes para confirmar que falham**

```bash
pytest tests/test_git_sync.py -v
```

Esperado: `ModuleNotFoundError` ou `ImportError` — o módulo não existe ainda.

- [ ] **Step 3: Implementar `catalog/storage/git_sync.py`**

```python
import subprocess
from datetime import date
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def _git(*args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )


def _git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def _gh(*args: str) -> str:
    try:
        result = subprocess.run(
            ["gh", *args],
            cwd=_REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except FileNotFoundError:
        raise RuntimeError(
            "gh CLI não encontrado. Instale em: https://cli.github.com/"
        )


def _tem_mudancas_staged() -> bool:
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=_REPO_ROOT,
    )
    return result.returncode != 0


def branch_atual() -> str:
    return _git_output("rev-parse", "--abbrev-ref", "HEAD")


def garantir_branch_sessao() -> str:
    branch = branch_atual()
    if branch.startswith("data/"):
        return branch
    nome = f"data/{date.today().isoformat()}"
    try:
        _git("checkout", "-b", nome)
    except subprocess.CalledProcessError:
        _git("checkout", nome)
    return nome


def commit_se_houver_mudancas(mensagem: str) -> bool:
    _git("add", "data/")
    if not _tem_mudancas_staged():
        return False
    _git("commit", "-m", mensagem)
    return True


def contar_commits_sessao() -> int:
    try:
        return int(_git_output("rev-list", "main..HEAD", "--count"))
    except (subprocess.CalledProcessError, ValueError):
        return 0


def finalizar_sessao() -> str:
    n = contar_commits_sessao()
    if n == 0:
        raise ValueError("Nenhuma alteração para enviar.")
    hoje = date.today().isoformat()
    sufixo = "ões" if n > 1 else "ão"
    mensagem = f"data: sessão {hoje} – {n} alteraç{sufixo}"
    branch = branch_atual()
    _git("reset", "--soft", "main")
    _git("commit", "-m", mensagem)
    _git("push", "-u", "origin", branch)
    return _gh(
        "pr", "create",
        "--title", mensagem,
        "--body", f"Sessão de {hoje}: {n} alteraç{sufixo} nos dados da biblioteca.",
        "--head", branch,
        "--base", "main",
    )
```

- [ ] **Step 4: Rodar os testes e confirmar que passam**

```bash
pytest tests/test_git_sync.py -v
```

Esperado: todos os testes passando.

- [ ] **Step 5: Commit**

```bash
git add catalog/storage/git_sync.py tests/test_git_sync.py
git commit -m "feat(git-sync): módulo git_sync com branch, commit, squash e PR"
```

---

## Task 2: Fixture global para isolar git_sync dos testes existentes

**Files:**
- Modify: `tests/conftest.py`

Quando `reescrever_registros`, `adicionar` (reading) e `salvar_config` (organizer) passarem a chamar `git_sync.commit_se_houver_mudancas`, os testes existentes começarão a tentar rodar comandos git reais. Esta task adiciona um mock autouse global.

- [ ] **Step 1: Rodar a suite completa para ver quais testes quebram após Task 1**

```bash
pytest --tb=short -q
```

Esperado: testes de persistence, reading e organizer ainda passam (git_sync não está integrado ainda). Isso confirma o estado atual.

- [ ] **Step 2: Adicionar fixture `mock_git_sync` em `tests/conftest.py`**

Adicionar ao final do arquivo existente:

```python
from unittest.mock import patch


@pytest.fixture(autouse=True)
def mock_git_sync():
    """Impede que testes rodem comandos git reais."""
    with patch("catalog.storage.git_sync.commit_se_houver_mudancas", return_value=False):
        yield
```

- [ ] **Step 3: Rodar a suite completa para confirmar que não quebrou nada**

```bash
pytest --tb=short -q
```

Esperado: mesma quantidade de testes passando que antes.

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py
git commit -m "test: fixture global mock_git_sync para isolar git de testes"
```

---

## Task 3: Integrar git_sync em `persistence.py`

**Files:**
- Modify: `catalog/storage/persistence.py`

Apenas `reescrever_registros` é chamada pela UI. `salvar()` é chamada pelo worker da CLI e não recebe commit automático.

- [ ] **Step 1: Escrever teste de integração**

Adicionar em `tests/test_persistence.py`:

```python
from unittest.mock import patch


def test_reescrever_registros_commita(sample_record):
    salvar(sample_record)
    atualizado = {**sample_record, "titulo": "Novo"}
    with patch("catalog.storage.git_sync.commit_se_houver_mudancas") as mock_commit:
        reescrever_registros([atualizado])
    mock_commit.assert_called_once()
    mensagem = mock_commit.call_args.args[0]
    assert mensagem.startswith("edit:")
```

- [ ] **Step 2: Rodar o novo teste para confirmar que falha**

```bash
pytest tests/test_persistence.py::test_reescrever_registros_commita -v
```

Esperado: FAIL — `commit_se_houver_mudancas` não é chamada ainda.

- [ ] **Step 3: Modificar `catalog/storage/persistence.py`**

Adicionar import no topo do arquivo (após os imports existentes):

```python
from . import git_sync
```

Substituir a função `reescrever_registros` existente:

```python
def reescrever_registros(registros: list[dict]) -> None:
    with _io_lock:
        with open(JSON_FILE, "w", encoding="utf-8") as f:
            for r in registros:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            w.writeheader()
            for r in registros:
                w.writerow({k: r.get(k, "") for k in CSV_HEADERS})
    titulo = registros[0].get("titulo") or registros[0].get("isbn", "?") if len(registros) == 1 else f"{len(registros)} registros"
    git_sync.commit_se_houver_mudancas(f"edit: {titulo}")
```

- [ ] **Step 4: Rodar todos os testes de persistence**

```bash
pytest tests/test_persistence.py -v
```

Esperado: todos passando, incluindo o novo.

- [ ] **Step 5: Commit**

```bash
git add catalog/storage/persistence.py tests/test_persistence.py
git commit -m "feat(git-sync): commit automático após reescrever_registros"
```

---

## Task 4: Integrar git_sync em `reading/storage.py`

**Files:**
- Modify: `catalog/reading/storage.py`
- Modify: `tests/test_reading.py`

- [ ] **Step 1: Escrever testes de integração**

Adicionar em `tests/test_reading.py`:

```python
from unittest.mock import patch


def test_adicionar_commita():
    with patch("catalog.storage.git_sync.commit_se_houver_mudancas") as mock_commit:
        storage.adicionar("9781098115784")
    mock_commit.assert_called_once()
    assert "9781098115784" in mock_commit.call_args.args[0]


def test_atualizar_progresso_commita():
    storage.adicionar("9781098115784")
    with patch("catalog.storage.git_sync.commit_se_houver_mudancas") as mock_commit:
        storage.atualizar_progresso("9781098115784", 50)
    mock_commit.assert_called_once()


def test_atualizar_status_commita():
    storage.adicionar("9781098115784")
    with patch("catalog.storage.git_sync.commit_se_houver_mudancas") as mock_commit:
        storage.atualizar_status("9781098115784", "lendo")
    mock_commit.assert_called_once()


def test_reordenar_commita():
    storage.adicionar("9781098115784")
    storage.adicionar("9780201633610")
    with patch("catalog.storage.git_sync.commit_se_houver_mudancas") as mock_commit:
        storage.reordenar("9781098115784", "baixo")
    mock_commit.assert_called_once()


def test_remover_commita():
    storage.adicionar("9781098115784")
    with patch("catalog.storage.git_sync.commit_se_houver_mudancas") as mock_commit:
        storage.remover("9781098115784")
    mock_commit.assert_called_once()
```

- [ ] **Step 2: Rodar os novos testes para confirmar que falham**

```bash
pytest tests/test_reading.py -k "commita" -v
```

Esperado: todos FAIL.

- [ ] **Step 3: Modificar `catalog/reading/storage.py`**

Adicionar import após os imports existentes:

```python
import catalog.storage.git_sync as git_sync
```

Adicionar chamada de commit ao final de cada função de escrita (fora do bloco `with _lock:`):

```python
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
    git_sync.commit_se_houver_mudancas(f"leitura: {isbn} adicionado à fila")


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
    git_sync.commit_se_houver_mudancas(f"leitura: {isbn} – {novo_status}")


def atualizar_progresso(isbn: str, pagina: int) -> None:
    with _lock:
        data = _carregar_raw()
        item = next((i for i in data["itens"] if i["isbn"] == isbn), None)
        if item is None:
            raise ValueError(f"ISBN {isbn} não encontrado na lista de leitura")
        item["progresso_paginas"] = pagina
        _salvar_raw(data)
    git_sync.commit_se_houver_mudancas(f"leitura: {isbn} – p. {pagina}")


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
    git_sync.commit_se_houver_mudancas("leitura: fila reordenada")


def remover(isbn: str) -> None:
    with _lock:
        data = _carregar_raw()
        data["itens"] = [i for i in data["itens"] if i["isbn"] != isbn]
        _compactar_ordem(data["itens"])
        _salvar_raw(data)
    git_sync.commit_se_houver_mudancas(f"leitura: {isbn} removido da lista")
```

- [ ] **Step 4: Rodar todos os testes de reading**

```bash
pytest tests/test_reading.py -v
```

Esperado: todos passando.

- [ ] **Step 5: Commit**

```bash
git add catalog/reading/storage.py tests/test_reading.py
git commit -m "feat(git-sync): commit automático após escritas na lista de leitura"
```

---

## Task 5: Integrar git_sync em `organizer/storage.py`

**Files:**
- Modify: `catalog/organizer/storage.py`
- Modify: `tests/test_organizer.py`

- [ ] **Step 1: Escrever teste de integração**

Verificar o que `test_organizer.py` importa e adicionar ao final do arquivo:

```python
from unittest.mock import patch
from catalog.organizer.storage import salvar_config
from catalog.organizer.models import ConfigEstantes


def test_salvar_config_commita(tmp_path):
    config = ConfigEstantes(estantes=[], espessura_media_cm=2.5)
    path = str(tmp_path / "estantes.json")
    with patch("catalog.storage.git_sync.commit_se_houver_mudancas") as mock_commit:
        salvar_config(config, path=path)
    mock_commit.assert_called_once_with("estantes: configuração atualizada")
```

- [ ] **Step 2: Rodar o novo teste para confirmar que falha**

```bash
pytest tests/test_organizer.py::test_salvar_config_commita -v
```

Esperado: FAIL.

- [ ] **Step 3: Modificar `catalog/organizer/storage.py`**

Adicionar import após os existentes:

```python
import catalog.storage.git_sync as git_sync
```

Substituir `salvar_config`:

```python
def salvar_config(config: ConfigEstantes, path: str = ESTANTES_FILE) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(asdict(config), f, ensure_ascii=False, indent=2)
    git_sync.commit_se_houver_mudancas("estantes: configuração atualizada")
```

- [ ] **Step 4: Rodar todos os testes de organizer**

```bash
pytest tests/test_organizer.py -v
```

Esperado: todos passando.

- [ ] **Step 5: Commit**

```bash
git add catalog/organizer/storage.py tests/test_organizer.py
git commit -m "feat(git-sync): commit automático após salvar configuração de estantes"
```

---

## Task 6: Startup — `ui/app.py`

**Files:**
- Modify: `ui/app.py`

Sem teste unitário para efeito de startup; verificação é manual.

- [ ] **Step 1: Modificar `ui/app.py`**

Adicionar import após os imports existentes e chamar `garantir_branch_sessao()` antes de `pg.run()`:

```python
import streamlit as st
import catalog.storage.git_sync as git_sync   # ← adicionar

st.set_page_config(
    page_title="Minha Biblioteca",
    page_icon="📚",
    layout="wide",
)

git_sync.garantir_branch_sessao()   # ← adicionar

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
```

- [ ] **Step 2: Verificar manualmente**

```bash
streamlit run ui/app.py
```

Verificar no terminal: o processo deve subir sem erro. Confirmar com `git branch` que o branch `data/YYYY-MM-DD` foi criado.

```bash
git branch
```

Esperado: ver `* data/2026-06-20` (ou data de hoje).

- [ ] **Step 3: Commit**

```bash
git add ui/app.py
git commit -m "feat(git-sync): criar branch de sessão no startup da UI"
```

---

## Task 7: `_session_bar()` em `ui/utils.py`

**Files:**
- Modify: `ui/utils.py`

- [ ] **Step 1: Adicionar `_session_bar` ao final de `ui/utils.py`**

```python
def _session_bar() -> None:
    import catalog.storage.git_sync as git_sync

    with st.sidebar:
        st.divider()
        try:
            branch = git_sync.branch_atual()
            n = git_sync.contar_commits_sessao()
        except Exception:
            st.caption("⚠️ git indisponível")
            return

        if not branch.startswith("data/"):
            st.caption(f"⚠️ Branch: `{branch}`")
            return

        st.caption(f"🌿 `{branch}`")
        if n == 0:
            st.caption("Sem alterações pendentes.")
        else:
            label = f"{n} alteraç{'ões' if n > 1 else 'ão'} pendente{'s' if n > 1 else ''}"
            st.caption(label)

        if st.button(
            "Finalizar sessão → PR",
            disabled=(n == 0),
            key="btn_finalizar_sessao",
        ):
            try:
                url = git_sync.finalizar_sessao()
                st.success("PR criada com sucesso!")
                st.link_button("Abrir PR →", url)
            except ValueError as e:
                st.warning(str(e))
            except RuntimeError as e:
                st.error(str(e))
```

- [ ] **Step 2: Commit**

```bash
git add ui/utils.py
git commit -m "feat(git-sync): componente _session_bar na sidebar"
```

---

## Task 8: Wire `_session_bar()` nas páginas

**Files:**
- Modify: `ui/pages/acervo.py`
- Modify: `ui/pages/ficha.py`
- Modify: `ui/pages/estantes.py`
- Modify: `ui/pages/leitura.py`

Em cada página, `_session_bar()` renderiza dentro de `with st.sidebar:` internamente — portanto basta chamá-la em qualquer ponto do script de cada página. Chamá-la ao final garante que os filtros/navegação apareçam antes da sessão na sidebar.

- [ ] **Step 1: Adicionar `_session_bar` aos imports de cada página**

Em `ui/pages/acervo.py`, adicionar `_session_bar` à linha `from ui.utils import (`:

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
    _session_bar,   # ← adicionar
)
```

Em `ui/pages/ficha.py`, adicionar `_session_bar` à linha `from ui.utils import (`:

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
    _session_bar,   # ← adicionar
)
```

Em `ui/pages/estantes.py` e `ui/pages/leitura.py`: localizar a linha `from ui.utils import (` e adicionar `_session_bar` à lista.

- [ ] **Step 2: Adicionar chamada `_session_bar()` ao final de cada página**

Última linha de `ui/pages/acervo.py`:
```python
_session_bar()
```

Última linha de `ui/pages/ficha.py`:
```python
_session_bar()
```

Última linha de `ui/pages/estantes.py`:
```python
_session_bar()
```

Última linha de `ui/pages/leitura.py`:
```python
_session_bar()
```

- [ ] **Step 3: Verificar manualmente no browser**

```bash
streamlit run ui/app.py
```

Abrir `http://localhost:8501` e verificar que:
1. A sidebar mostra `🌿 data/YYYY-MM-DD` e "Sem alterações pendentes."
2. Editar um livro → a sidebar atualiza para "1 alteração pendente"
3. O botão "Finalizar sessão → PR" fica habilitado após a edição

- [ ] **Step 4: Commit**

```bash
git add ui/pages/acervo.py ui/pages/ficha.py ui/pages/estantes.py ui/pages/leitura.py
git commit -m "feat(git-sync): session bar nas páginas da UI"
```

---

## Task 9: Rodar a suite completa e verificar

- [ ] **Step 1: Rodar todos os testes**

```bash
pytest -v
```

Esperado: todos os testes passando, zero falhas.

- [ ] **Step 2: Verificar fluxo completo manualmente**

1. `git checkout main` — reiniciar do branch principal
2. `streamlit run ui/app.py` — deve criar `data/YYYY-MM-DD` automaticamente
3. Editar um livro na UI — sidebar deve mostrar "1 alteração pendente"
4. Clicar "Finalizar sessão → PR" — deve criar PR e exibir link
5. `git log --oneline main..HEAD` — deve mostrar 1 commit apenas (squashado)

- [ ] **Step 3: Commit final se necessário**

Se houver ajustes de última hora:
```bash
git add -p
git commit -m "fix(git-sync): ajustes pós-verificação manual"
```
