# Sistema de Etiquetas — Design

**Data:** 2026-06-19  
**Status:** Aprovado

---

## Objetivo

Permitir ao usuário atribuir etiquetas livres a cada livro do acervo (ex: "lazer", "doutorado", "Filosofia"), independentes dos assuntos vindos das APIs. As etiquetas são curadoria pessoal — nunca preenchidas automaticamente.

---

## Modelo de dados

### Campo novo: `etiquetas`

| Campo | Tipo | Exemplo | Notas |
|---|---|---|---|
| `etiquetas` | str | `"lazer, doutorado"` | Separadas por vírgula; vazio por padrão |

- Inserido em `CSV_HEADERS` em `catalog/config.py`, após `prateleira`
- JSONL e CSV armazenam a mesma string (mesmo padrão do campo `assuntos`)
- Valor padrão: `""` (string vazia)
- `api.py` **não** é alterado — etiquetas nunca são preenchidas pelas APIs

### Impacto na persistência

`salvar()` e `reescrever_registros()` em `catalog/storage/persistence.py` já usam `registro.get(k, "")` para todos os campos do header — nenhuma alteração necessária.

---

## Migração

Script: `scripts/migrar_etiquetas.py`

- Lê `data/biblioteca.jsonl`
- Adiciona `"etiquetas": ""` em todos os registros que não tenham o campo
- Reescreve JSONL e CSV via `reescrever_registros()`
- Idempotente: registros que já tenham o campo não são alterados
- Padrão dos scripts existentes: `migrar_capa_fonte.py`, `migrar_posicao_estante.py`

---

## UI

### Dialog de edição — `ui/utils.py` → `_dialog_editar()`

- Novo campo no form: `st.multiselect("Etiquetas", options=todas_etiquetas, default=etiquetas_atuais)`
- `todas_etiquetas`: conjunto de todas as etiquetas únicas presentes no acervo (carregadas dos registros)
- O widget permite digitar etiquetas novas não presentes na lista
- Ao salvar: join com `", "` → string gravada em `etiquetas`
- `_salvar_edicao()` inclui `"etiquetas"` no dict de campos salvos

### Cards do acervo — `ui/pages/acervo.py`

- Exibe etiquetas como badges roxos (`background:#ede7f6; color:#6a1b9a`) abaixo dos badges de fonte
- Máximo de 3 badges visíveis; se houver mais, exibe `+N` no lugar do excedente
- Livros sem etiqueta não exibem nada extra

### Filtro sidebar — `ui/pages/acervo.py`

- Nova seção "🏷️ Etiquetas" no sidebar, abaixo dos filtros existentes
- Widget: `st.multiselect` com todas as etiquetas únicas do acervo
- Lógica de filtragem: **AND** — exibe apenas livros que possuem **todas** as etiquetas selecionadas
- A seção só é renderizada se ao menos um livro tiver etiqueta cadastrada

### Ficha — `ui/pages/ficha.py`

- Exibe todas as etiquetas do livro sem truncamento
- Mesmo estilo de badge roxo dos cards

---

## Testes

| Arquivo | Mudança |
|---|---|
| `tests/test_persistence.py` | Adicionar caso: salva registro com `etiquetas` preenchido, verifica carregamento no JSONL e presença correta no CSV |
| `tests/test_api.py` | Nenhuma mudança |
| `tests/test_organizer.py` | Nenhuma mudança |

Script de migração não ganha teste automatizado (uso único, padrão dos scripts existentes).

---

## Arquivos alterados

| Arquivo | Tipo de mudança |
|---|---|
| `catalog/config.py` | Adicionar `"etiquetas"` em `CSV_HEADERS` |
| `scripts/migrar_etiquetas.py` | Novo script de migração |
| `ui/utils.py` | Campo etiquetas em `_dialog_editar()` e `_salvar_edicao()` |
| `ui/pages/acervo.py` | Badges nos cards + filtro na sidebar |
| `ui/pages/ficha.py` | Exibição das etiquetas na ficha |
| `tests/test_persistence.py` | Novo caso de teste |

---

## Fora de escopo

- Etiquetas não são preenchidas automaticamente pelas APIs
- Não há hierarquia entre etiquetas (todas são iguais)
- Não há cor customizável por etiqueta (todas usam o estilo roxo padrão)
- Filtro OR não implementado (apenas AND)
