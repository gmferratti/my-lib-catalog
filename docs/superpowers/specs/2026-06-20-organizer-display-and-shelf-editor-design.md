# Design: Padronização de nomes + Editor granular de estantes

**Data:** 2026-06-20  
**Módulo afetado:** `ui/pages/estantes.py`  
**Status:** Aprovado

---

## Contexto

Dois problemas independentes na página de Estantes:

1. **Exibição inconsistente de livros** — livros com autor aparecem como `(sem autor) — Título` na lista principal e só `Título` na seção "sem lugar". O formato também está invertido: o autor estava antes do título.

2. **Configuração de estantes pouco granular** — o formulário atual força todas as prateleiras a ter a mesma largura. O modelo de dados (`PrateleiraConfig.largura_cm`) já suporta larguras diferentes por prateleira, mas a UI não expõe isso.

---

## Feature 1 — Padronização de nomes no organizador

### Decisão de formato

**Novo formato:** `Título — Autor (ano)` quando há autor; `Título (ano)` quando não há.

- Título em negrito no markdown da UI.
- Sem fallback `(sem autor)` — se não há autor, não aparece nada no lugar dele.

### Implementação

Novo helper em `ui/pages/estantes.py`:

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

Três pontos de substituição em `estantes.py`:

| Localização | Código atual | Após mudança |
|---|---|---|
| Lista principal (linha 225) | `f"- {autores} — **{titulo}**{ano}"` | `f"- {_formatar_livro(livro)}"` |
| Seção "sem lugar" (linha 232) | condicional com `autores` | `f"- {_formatar_livro(livro)}"` |
| `_gerar_txt` (linha 43) | `f"  {autores} — {titulo} ({ano})"` | `f"  {_formatar_livro(livro, markdown=False)}"` |

### Limitação conhecida

Livros com título no formato de série (ex.: `"Harry Potter — Vol. 1: A Pedra Filosofal"`) resultarão em duplo `—` ao lado do autor:  
`**Harry Potter — Vol. 1: A Pedra Filosofal** — J.K. Rowling (1997)`

Isso é um problema de dado (campo `titulo`), não de exibição. Endereçar no contexto do módulo de séries, separadamente.

---

## Feature 2 — Editor granular de estantes

### Decisão de arquitetura

Substituir o formulário global (`form_config_estantes`) por um editor estruturado que expõe toda a granularidade do modelo de dados existente.

- **Sem mudança no schema** de `estantes.json` — `PrateleiraConfig.largura_cm` por prateleira já existe.
- `espessura_media_cm` permanece global (propriedade dos livros, não das prateleiras).

### Estado da UI

O editor usa `st.session_state["estante_draft"]` como rascunho:

```python
# Estrutura do rascunho
estante_draft: list[dict] = [
    {
        "nome": "Estante 1",
        "prateleiras": [
            {"nome": "A", "largura_cm": 80.0},
            {"nome": "B", "largura_cm": 60.0},
        ]
    },
    ...
]
```

Inicializado a partir de `carregar_config()` na primeira renderização (`"estante_draft" not in st.session_state`).

### Layout do editor

```
⚙️ Configurar estantes
─────────────────────────────────────────────
Espessura média dos livros (cm): [2.5 ↕]

  🗄️ Estante 1
    Nome: [Estante 1        ]
    ┌──────────┬────────────┬──────┐
    │ Prateleira│ Largura(cm)│      │
    ├──────────┼────────────┼──────┤
    │ A        │    80.0    │ [🗑️]│
    │ B        │    60.0    │ [🗑️]│
    └──────────┴────────────┴──────┘
    [+ Prateleira]       [🗑️ Remover estante]

  🗄️ Estante 2
    ...

[+ Adicionar estante]          [💾 Salvar configuração]
```

### Comportamento dos controles

- **`+ Adicionar estante`**: insere `{"nome": "Estante N+1", "prateleiras": [{"nome": "A", "largura_cm": 80.0}]}` no rascunho + `st.rerun()`.
- **`+ Prateleira`**: insere próxima letra da sequência (A→B→C… AA→AB…) com 80 cm padrão + `st.rerun()`.
- **`🗑️` (prateleira)**: remove a prateleira pelo índice + `st.rerun()`.
- **`🗑️ Remover estante`**: remove a estante pelo índice + `st.rerun()`.
- **`💾 Salvar configuração`**: lê todos os campos do `st.session_state` usando as chaves `est_{i}_nome`, `prat_{i}_{j}_nome`, `prat_{i}_{j}_largura`, reconstrói `ConfigEstantes` e chama `salvar_config()`.

### Chaves de session state para widgets

```
espessura_editor            → st.number_input espessura global
est_{i}_nome                → st.text_input nome da estante i
prat_{i}_{j}_nome           → st.text_input nome da prateleira j da estante i
prat_{i}_{j}_largura        → st.number_input largura da prateleira j da estante i
```

### Capacidade estimada em tempo real

Manter o `st.caption` de preview de capacidade total, calculado dinamicamente a partir dos valores correntes do rascunho ao renderizar cada estante.

---

## Arquivos afetados

| Arquivo | Mudança |
|---|---|
| `ui/pages/estantes.py` | Helper `_formatar_livro`, substituição dos 3 pontos de exibição, substituição do formulário pelo editor |
| `ui/utils.py` | Nenhuma |
| `catalog/organizer/` | Nenhuma |
| `data/estantes.json` | Nenhuma (schema inalterado) |

---

## Testes

- Verificar exibição de livros com autor, sem autor e com título de série na UI renderizada.
- Verificar que o `.txt` de download usa o novo formato sem markdown.
- Verificar add/remove de estante e prateleira sem perder valores já preenchidos em outros campos.
- Verificar que salvar persiste o `estantes.json` com as larguras corretas por prateleira.
- Verificar que a sugestão de organização usa as larguras corretas após salvar.
