# Ficha de Catálogo, Busca no Topo e Consolidação de Estantes — Design

## Objetivo

Três melhorias de UX na aba Acervo e Estantes do Streamlit:

1. **Busca no topo** — mover a barra de busca da sidebar para o topo do conteúdo da aba Acervo.
2. **Ficha de catálogo** — ao clicar em "Ver ficha" em qualquer card, a grade é substituída por uma página de detalhe completa do livro, com botão de retorno.
3. **Consolidação de estantes** — mecanismo para transformar uma sugestão ephêmera de organização em posição real gravada permanentemente em cada registro.

---

## 1. Busca no Topo

### Comportamento

- O `st.text_input` de busca (título ou autor) sai da sidebar e vai para o topo do conteúdo de `_render_acervo()`, **antes das métricas**.
- Full-width, placeholder: `"🔍 Buscar por título ou autor..."`.
- Os demais filtros da sidebar (idioma, fonte, checkbox "ocultar sem metadados", ordenação, modo edição, recarregar) permanecem inalterados.

### Layout resultante

```
[aba Acervo selecionada]

🔍 Buscar por título ou autor...      ← novo, no topo do conteúdo

Total | Exibindo | Páginas | Com capa | Sem meta   ← métricas existentes
────────────────────────────────────────────────
[grade de cards]
```

---

## 2. Ficha de Catálogo

### Navegação

- `st.session_state["isbn_selecionado"]` controla qual livro está aberto.
- Quando definido, `_render_acervo()` renderiza a ficha em vez da grade.
- Limpar o estado (`del st.session_state["isbn_selecionado"]`) + `st.rerun()` volta para a grade.

### Como abrir

- Todo card recebe um botão **"📖 Ver ficha"** sempre visível (não depende do modo edição).
- Clicar define `st.session_state["isbn_selecionado"] = isbn` e chama `st.rerun()`.
- O filtro de busca e sidebar continuam funcionando normalmente — a ficha só abre quando o botão é clicado.

### Layout da ficha

```
← Voltar ao acervo

┌────────────┬────────────────────────────────────────────┐
│            │  Título completo                           │
│  [capa]    │  Autores · Ano · Editora                   │
│  (200px)   │  ──────────────────────────────────────── │
│            │  ISBN: 9781234567890                       │
│            │  Idioma: Português   Páginas: 320          │
│            │  Assuntos: Ficção, Literatura               │
│            │  ──────────────────────────────────────── │
│            │  Metadata:  [badge fonte]                  │
│            │  Capa:      [badge capa_fonte]             │
│            │  Cadastrado: 2026-05-10T14:22:00           │
│            │  ──────────────────────────────────────── │
│            │  📍 Posição na estante                     │
│            │     Estante 2 / Prateleira B               │
│            │     (ou "Não confirmada")                  │
└────────────┴────────────────────────────────────────────┘
                           [✏️ Editar este livro]
```

- Capa renderizada com `st.image(..., width=200)`.
- Se não houver capa, placeholder `📖` na mesma área.
- "Não confirmada" exibe texto em cinza com instrução: "Gere e aplique uma sugestão na aba Estantes."
- **"✏️ Editar este livro"** abre o `_dialog_editar` existente — nenhuma lógica de edição duplicada.
- A ficha é uma função `_render_ficha(registro: dict)` extraída do `_render_acervo()`.

---

## 3. Consolidação de Estantes

### Schema — novos campos

| Campo | Tipo | Exemplo | Notas |
|---|---|---|---|
| `estante` | str | `"Estante 2"` | Vazio se não confirmada |
| `prateleira` | str | `"B"` | Vazio se não confirmada |

Adicionados ao `CSV_HEADERS` em `catalog/config.py`, imediatamente após `"data_cadastro"`.
`CLAUDE.md` atualizado com os dois campos na tabela de schema.

### Migração

Script `scripts/migrar_posicao_estante.py`:

- Lê `data/biblioteca.jsonl`.
- Para cada registro sem os campos `estante` e `prateleira`, adiciona ambos como `""`.
- Guarda (idempotente: `if "estante" not in r`).
- Reescreve JSONL e CSV via `reescrever_registros()`.

### Aplicar sugestão (aba Estantes)

Após `st.session_state["organizer_resultado"]` estar populado (sugestão gerada), exibe:

```
[✅ Aplicar esta sugestão como posição real]
```

Ao clicar:
1. Carrega todos os registros via `carregar_todos_registros()`.
2. Constrói mapa `{isbn: (estante, prateleira)}` a partir do resultado do organizer.
3. Para cada registro, atualiza `estante` e `prateleira` (livros não presentes na sugestão recebem `""` — ficaram sem lugar).
4. Chama `reescrever_registros(registros)` uma única vez.
5. Limpa cache (`st.cache_data.clear()`), exibe toast "Posições aplicadas!" e `st.rerun()`.

### Exibição na ficha

- Se `estante` e `prateleira` preenchidos: `📍 Estante 2 / Prateleira B`
- Se vazios: `📍 Posição não confirmada — gere e aplique uma sugestão na aba Estantes.` (texto em cinza)

---

## Arquivos a modificar

| Arquivo | O que muda |
|---|---|
| `catalog/config.py` | Adicionar `"estante"` e `"prateleira"` ao `CSV_HEADERS` |
| `ui/app.py` | Busca no topo; ficha `_render_ficha()`; botão "Ver ficha" nos cards; botão "Aplicar sugestão" na aba Estantes |
| `scripts/migrar_posicao_estante.py` | Novo script de migração (criar) |
| `CLAUDE.md` | Schema atualizado com `estante` e `prateleira` |

**Não muda:** `catalog/metadata/`, `catalog/storage/`, `catalog/organizer/`, `main.py`, testes existentes.

---

## Sequência de implementação

1. **Schema + migração** — `config.py` + `migrar_posicao_estante.py` + `CLAUDE.md` → rodar migração
2. **Busca no topo** — mover `st.text_input` no `_render_acervo()`
3. **Botão "Ver ficha" + `_render_ficha()`** — função de detalhe + navegação por session_state
4. **Botão "Aplicar sugestão"** — na aba Estantes, gravar posições nos registros
