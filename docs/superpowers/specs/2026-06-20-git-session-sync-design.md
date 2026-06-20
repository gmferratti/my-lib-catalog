# Design: Git Session Sync

**Data:** 2026-06-20  
**Status:** Aprovado

## Problema

Edições feitas na UI Streamlit (metadados, etiquetas, posições de estante, progresso de leitura) precisam ser refletidas no repositório git de forma organizada — sem poluir o histórico de código e sem exigir ação manual a cada mudança.

## Solução

Cada sessão de uso do app cria um branch `data/YYYY-MM-DD`. Cada operação de escrita gera um commit nesse branch. Ao finalizar a sessão, todos os commits são squashados em um único commit e uma PR é aberta para `main`.

O histórico de `main` recebe um commit por sessão, com a PR como contexto. O histórico intraday fica no branch até o merge.

---

## Arquitetura

### Novo módulo: `catalog/storage/git_sync.py`

Encapsula toda a lógica git. Os módulos de escrita existentes não importam `subprocess` diretamente — delegam para `git_sync`.

**Funções públicas:**

```python
def garantir_branch_sessao() -> str:
    """
    Garante que o repo está em um branch data/YYYY-MM-DD.
    - Se já estiver num branch data/*, retorna o nome (app reiniciado).
    - Se estiver em main/master, cria e faz checkout do branch do dia.
    Retorna o nome do branch atual.
    """

def commit_se_houver_mudancas(mensagem: str) -> bool:
    """
    Faz `git add data/` e commita se houver mudanças staged.
    Retorna True se um commit foi criado, False se não havia nada.
    """

def contar_commits_sessao() -> int:
    """
    Conta quantos commits o branch atual tem à frente de main.
    Usado pela sidebar para mostrar "N alterações pendentes".
    """

def finalizar_sessao() -> str:
    """
    1. Conta commits da sessão — se 0, levanta ValueError.
    2. Squash: git reset --soft main
    3. Commita com mensagem "data: sessão YYYY-MM-DD – N alterações"
    4. Roda `gh pr create` e retorna a URL da PR criada.
    """
```

**Dependências:** apenas stdlib (`subprocess`, `datetime`, `pathlib`). Não importa nenhum módulo do projeto.

---

### Integração com módulos de escrita

`salvar()` em `persistence.py` é chamado exclusivamente pelo **worker da CLI** (thread background) — não recebe commit automático. Livros recém-escaneados ficam no JSONL e são capturados no próximo commit da UI (por exemplo, quando o usuário edita qualquer campo ou aplica posições de estante).

Funções chamadas **pela UI** que recebem `commit_se_houver_mudancas` após persistir:

| Módulo | Função | Mensagem do commit |
|---|---|---|
| `catalog/storage/persistence.py` | `reescrever_registros(registros)` | `edit: {titulo}` (1 livro) ou `edit: {N} registros atualizados` (lote) |
| `catalog/reading/storage.py` | `adicionar(isbn)` | `leitura: {isbn} adicionado à fila` |
| `catalog/reading/storage.py` | `atualizar_progresso(isbn, pagina)` | `leitura: {titulo} – p. {pagina}` |
| `catalog/reading/storage.py` | `atualizar_status(isbn, status)` | `leitura: {titulo} – {status}` |
| `catalog/reading/storage.py` | `reordenar(isbn, direcao)` | `leitura: fila reordenada` |
| `catalog/reading/storage.py` | `remover(isbn)` | `leitura: {isbn} removido da lista` |
| `catalog/organizer/storage.py` | `salvar_config(config)` | `estantes: configuração atualizada` |

`git add data/` na hora do commit captura todos os arquivos sob `data/` — incluindo `biblioteca.jsonl`, `lista_leitura.json` e `estantes.json` — então dois módulos gravando em sequência ainda geram commits separados e limpos.

---

### Startup: `ui/app.py`

```python
import catalog.storage.git_sync as git_sync

# Logo após os imports, antes de pg.run()
git_sync.garantir_branch_sessao()
```

Isso roda uma vez por processo Streamlit. Se o app reiniciar (hot reload), o branch já existe e a função retorna sem criar novo.

---

### Componente de sessão: função `_session_bar()` em `ui/utils.py`

A UI já usa `ui/utils.py` para código compartilhado — o componente de sessão entra lá como uma função, seguindo o padrão existente. Renderiza na sidebar de cada página que a chame:

```
🌿 data/2026-06-20
   3 alterações pendentes

[ Finalizar sessão → PR ]
```

- Se `contar_commits_sessao() == 0`: mostra "Nenhuma alteração ainda."
- Ao clicar em "Finalizar sessão → PR": chama `finalizar_sessao()`, exibe link da PR criada.
- Se `gh` não estiver instalado ou não autenticado: exibe mensagem de erro clara.

`_session_bar()` é chamada em cada `pages/*.py` na sidebar, ao lado dos outros utilitários de `ui/utils.py`.

---

## Fluxo completo

```
App sobe
  └── garantir_branch_sessao()  → checkout data/2026-06-20

Usuário edita livro
  └── reescrever_registros()
        └── commit_se_houver_mudancas("edit: O Hobbit")
              └── git add data/ && git commit -m "edit: O Hobbit"

Usuário atualiza progresso de leitura
  └── atualizar_progresso()
        └── commit_se_houver_mudancas("leitura: O Hobbit – p. 142")

Sidebar mostra: "🌿 data/2026-06-20 · 2 alterações pendentes"

Usuário clica "Finalizar sessão → PR"
  └── finalizar_sessao()
        ├── git reset --soft main
        ├── git commit -m "data: sessão 2026-06-20 – 2 alterações"
        └── gh pr create --title "data: sessão 2026-06-20" --body "..."
              → exibe URL da PR
```

---

## Casos de borda

| Situação | Comportamento |
|---|---|
| Nenhuma alteração ao finalizar | `ValueError` — sidebar informa "Nenhuma alteração para enviar" |
| App reinicia no meio da sessão | `garantir_branch_sessao()` detecta branch `data/*` existente, continua |
| `data/YYYY-MM-DD` já existe de sessão anterior não merged | Continua no branch existente, acumulando commits |
| `gh` não instalado | `finalizar_sessao()` levanta `RuntimeError` com instrução de instalação |
| Conflito com main | Não tratado automaticamente — usuário resolve no GitHub após abrir PR |
| Sessão em fim de dia (branch muda de data) | Branch do dia anterior continua ativo; novo branch só é criado no próximo startup |

---

## O que não muda

- Schema de dados: nenhum campo novo.
- `catalog.storage.persistence._io_lock`: ainda protege escrita de arquivo; `git_sync` roda **depois** do lock ser liberado.
- CLI (`main.py`): não chama `garantir_branch_sessao()` — git sync é exclusivo da UI.
- Testes existentes: sem impacto (git_sync pode ser mockado ou ignorado em testes).

---

## Pré-requisitos

- `git` disponível no PATH.
- `gh` CLI instalado e autenticado (`gh auth login`).
- Repo tem um remote `origin` configurado (para `gh pr create` funcionar).
