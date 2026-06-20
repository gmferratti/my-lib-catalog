# Notas e Resenhas por Livro — Design Spec

**Data:** 2026-06-20
**Status:** Aprovado

## Visão geral

Adicionar suporte a anotações livres e links externos por livro no my-lib-catalog. Qualquer livro do acervo pode ter uma nota, independentemente do status de leitura.

**Escopo:**
- Texto livre (resenha/anotação) por livro
- Múltiplos links externos por livro, cada um com URL e rótulo opcional
- Sem avaliação/nota numérica (fora do escopo)
- Visível na ficha individual do livro; sem impacto nos cards do acervo

---

## Dados

**Arquivo:** `data/notas.json`

**Estrutura:**
```json
{
  "notas": {
    "9781098115784": {
      "anotacao": "Texto livre da resenha...",
      "links": [
        {"url": "https://blog.exemplo.com/resenha", "rotulo": "Resenha no blog"},
        {"url": "https://goodreads.com/book/show/123", "rotulo": "Goodreads"}
      ],
      "data_modificacao": "2026-06-20T14:30:00"
    }
  }
}
```

**Invariantes:**
- ISBNs sem nota não existem no dicionário (não há objeto vazio)
- `rotulo` pode ser string vazia — a URL é exibida truncada nesse caso
- `data_modificacao` é atualizado a cada `salvar()`
- Arquivo criado automaticamente na primeira escrita

---

## Módulo `catalog/notas/`

```
catalog/notas/
    __init__.py      # re-exports públicos
    storage.py       # lógica de leitura/escrita
```

**API pública:**

```python
carregar(isbn: str) -> dict | None
```
Retorna `{"anotacao": str, "links": list[dict], "data_modificacao": str}` ou `None` se o ISBN não tem nota.

```python
salvar(isbn: str, anotacao: str, links: list[dict]) -> None
```
Upsert — cria ou substitui a nota completa para o ISBN. Atualiza `data_modificacao`. Chama `git_sync.commit_se_houver_mudancas` após a escrita.

```python
remover(isbn: str) -> None
```
Remove a entrada do ISBN se existir; no-op se não existir. Chama `git_sync.commit_se_houver_mudancas` após a escrita.

**Sem lock explícito:** apenas a UI escreve notas (não há worker de background para esse módulo).

**Git sync:** após cada `salvar()` e `remover()`, chama:
```python
git_sync.commit_se_houver_mudancas(f"notas: {isbn} – anotação atualizada", arquivos=[_NOTAS_FILE])
```

---

## Fronteiras de módulo

Adições às fronteiras definidas no CLAUDE.md:

| Módulo | Pode importar de | Não pode importar de |
|---|---|---|
| `catalog.notas` | `catalog.config`, `catalog.storage.git_sync`, stdlib | `catalog.metadata`, `catalog.scanning`, `catalog.reading`, `main` |
| `ui.pages.ficha` | `catalog.notas` (adição) | sem mudança nas demais restrições |

---

## UI — `ui/pages/ficha.py`

Nova seção **"📝 Anotações"** inserida após a seção de lista de leitura.

### Modo leitura (sempre visível)

- Sem nota: `st.caption("Nenhuma anotação ainda.")` em cinza sutil
- Com anotação: `st.markdown(nota["anotacao"])` — suporta negrito, listas etc.
- Links exibidos como `st.link_button(rotulo or url_truncada, url)` para cada item

### Modo edição (requer `_is_autenticado()`)

Botão "✏️ Editar anotações" abre um `@st.dialog` com:

1. `st.text_area("Anotação", value=anotacao_atual)` — sem limite de caracteres
2. Lista dos links atuais: linha com campos `url` + `rotulo` + botão "✕" para remover (gerenciado via `st.session_state`)
3. Botão "＋ Adicionar link" — anexa linha vazia à lista no session_state
4. Botão "💾 Salvar" — chama `notas.salvar(isbn, anotacao, links)` e fecha o dialog

Visual e autenticação seguem o padrão de `_dialog_editar` em `ui/utils.py`.

**Sem mudanças em:** `ui/pages/acervo.py`, `ui/pages/leitura.py`, cards do acervo.

---

## Testes — `tests/test_notas.py`

| Caso | O que verifica |
|---|---|
| `test_carregar_isbn_sem_nota` | Retorna `None` para ISBN inexistente |
| `test_salvar_e_carregar` | Salva uma nota e recupera dados corretamente |
| `test_salvar_atualiza_data_modificacao` | `data_modificacao` muda a cada `salvar()` |
| `test_salvar_substitui_nota_existente` | Upsert funciona corretamente |
| `test_remover` | Entrada desaparece após `remover()` |
| `test_remover_isbn_inexistente` | Não lança exceção |

`mock_git_sync` com `autouse=True` em `tests/conftest.py` é herdado automaticamente — sem configuração extra.

---

## Arquivos criados/modificados

| Arquivo | Ação |
|---|---|
| `catalog/notas/__init__.py` | Criar |
| `catalog/notas/storage.py` | Criar |
| `catalog/config.py` | Adicionar `NOTAS_FILE = "data/notas.json"` |
| `ui/pages/ficha.py` | Adicionar seção de notas |
| `tests/test_notas.py` | Criar |
| `CLAUDE.md` | Atualizar fronteiras de módulo e arquivos de dados |

---

## Fora do escopo

- Avaliação numérica (estrelas ou nota) — não implementar
- Notas visíveis nos cards do acervo — não implementar
- Múltiplas notas por livro (histórico) — não implementar; uma nota por livro substituída a cada edição
- Busca/filtragem por conteúdo das notas — não implementar
