# Lista de Leitura — Design Spec

**Data:** 2026-06-19
**Status:** Aprovado

---

## Resumo

Novo módulo de lista de leitura para o my-lib-catalog. Permite ao usuário manter uma fila ordenada de livros a ler, registrar progresso de leitura (página atual), e consultar um histórico de livros lidos e abandonados. Opera exclusivamente sobre livros já cadastrados no acervo (referenciados por ISBN).

---

## Modelo de dados

Novo arquivo `data/lista_leitura.json` — lido inteiro em memória (análogo a `estantes.json`):

```json
{
  "itens": [
    {
      "isbn": "9781098115784",
      "status": "na_fila",
      "ordem": 1,
      "progresso_paginas": 0,
      "data_adicao": "2026-06-19T10:00:00",
      "data_inicio": null,
      "data_conclusao": null,
      "data_abandono": null
    }
  ]
}
```

### Campos

| Campo | Tipo | Descrição |
|---|---|---|
| `isbn` | str | ISBN do livro — chave estrangeira para `biblioteca.jsonl` |
| `status` | str | `na_fila` \| `lendo` \| `lido` \| `abandonado` |
| `ordem` | int | Posição na fila; relevante apenas para `na_fila` |
| `progresso_paginas` | int | Página atual (0 se não iniciado) |
| `data_adicao` | str | ISO 8601 — quando foi adicionado à lista |
| `data_inicio` | str \| null | ISO 8601 — quando o status mudou para `lendo` |
| `data_conclusao` | str \| null | ISO 8601 — quando o status mudou para `lido` |
| `data_abandono` | str \| null | ISO 8601 — quando o status mudou para `abandonado` |

### Transições de status

```
na_fila  →  lendo  →  lido
                   →  abandonado
lendo    →  na_fila  (desistir de continuar por enquanto)
```

O campo `progresso_paginas` é mantido ao retornar para `na_fila` — o progresso não é perdido.

---

## Módulo `catalog/reading`

```
catalog/reading/
    __init__.py      # exporta a API pública
    storage.py       # CRUD do lista_leitura.json
```

### API pública (`storage.py`)

| Função | Assinatura | Descrição |
|---|---|---|
| `carregar` | `() → list[dict]` | Lê o JSON, retorna todos os itens |
| `adicionar` | `(isbn: str) → None` | Insere com status `na_fila`, ordem = len(fila) + 1 |
| `atualizar_status` | `(isbn: str, novo_status: str) → None` | Muda status e preenche a data correspondente; ao sair de `na_fila`, compacta `ordem` dos demais itens na fila |
| `atualizar_progresso` | `(isbn: str, pagina: int) → None` | Atualiza `progresso_paginas` |
| `reordenar` | `(isbn: str, direcao: str) → None` | Move item `"cima"` ou `"baixo"` na fila |
| `remover` | `(isbn: str) → None` | Remove da lista (não afeta o acervo); compacta `ordem` dos itens restantes em `na_fila` |

### Fronteiras de módulo

- `catalog/reading` pode importar de: `catalog/config`, stdlib
- `catalog/reading` **não pode** importar de: `catalog/metadata`, `catalog/scanning`, `catalog/organizer`, `main`
- `ui/pages/leitura.py` importa de: `catalog/reading.storage`, `catalog/storage` (para metadados do livro)

### Persistência

- Arquivo: `data/lista_leitura.json` (caminho definido em `catalog/config.py` como `LEITURA_FILE`)
- Leitura: carrega o JSON completo a cada operação (volume pequeno, sem otimização necessária)
- Escrita: reescreve o JSON completo (análogo a `estantes.json`)
- Thread safety: lock próprio (`threading.Lock`) em `catalog/reading/storage.py` — não importa de `catalog/storage` para respeitar as fronteiras de módulo

---

## UI

### Nova página `ui/pages/leitura.py`

Adicionada ao menu de navegação em `ui/app.py` com ícone 📋.

#### Seção 1 — 📖 Lendo agora

- Cards dos livros com `status = lendo`
- Cada card mostra: capa (se disponível), título, autor, barra de progresso visual
- Input de página atual (number input, máx = total de páginas do livro)
- Botões: **"✅ Marcar como lido"** e **"🚫 Abandonar"**
- Múltiplos livros em andamento simultâneo são permitidos (sem limite)

#### Seção 2 — 📋 Na fila

- Lista compacta em ordem definida pelo campo `ordem`
- Cada item mostra: posição, capa miniatura (se disponível), título, autor
- Botões: **▲** / **▼** (reordenar), **"▶ Começar a ler"** (move para `lendo`), **"✕ Remover"**

#### Seção 3 — 📚 Histórico *(collapsible)*

- Tabela com `status = lido` ou `status = abandonado`
- Colunas: título, autor, status, data de conclusão/abandono, páginas lidas / total
- Ordem: mais recente primeiro

### Integração com `ui/pages/ficha.py`

Na ficha individual de cada livro, adicionar seção "Lista de leitura":
- Se o livro **não está** na lista: botão "➕ Adicionar à fila de leitura"
- Se o livro **está na lista**: mostra status atual, barra de progresso e percentual lido (`progresso_paginas / paginas × 100`), e no modo edição, ações rápidas de atualização
- Se `paginas` for zero ou ausente, exibe apenas as páginas absolutas sem percentual

### Proteção por senha

Todas as ações de escrita (adicionar, mudar status, atualizar progresso, reordenar, remover) requerem modo edição autenticado — igual ao padrão da página Acervo.

---

## Arquivos afetados

| Arquivo | Mudança |
|---|---|
| `catalog/config.py` | Adiciona `LEITURA_FILE = "data/lista_leitura.json"` |
| `catalog/reading/__init__.py` | Novo |
| `catalog/reading/storage.py` | Novo |
| `ui/app.py` | Adiciona `leitura.py` à navegação |
| `ui/pages/leitura.py` | Novo |
| `ui/pages/ficha.py` | Adiciona seção de status de leitura |
| `tests/test_reading.py` | Novo — testes do módulo `catalog/reading` |

---

## Testes

- `test_reading.py` cobre:
  - `adicionar`: livro novo aparece com `status = na_fila`
  - `adicionar` duplicado: levanta `ValueError`
  - `atualizar_status`: transições válidas preenchem a data correta
  - `atualizar_progresso`: atualiza página; ignora valor maior que total de páginas (não valida aqui — responsabilidade da UI)
  - `reordenar`: cima/baixo atualiza `ordem` corretamente; sem efeito nas bordas
  - `remover`: item desaparece; ISBNs restantes mantêm ordem consistente

---

## O que está fora do escopo

- Datas-alvo ou prazos de leitura (não solicitado)
- Wish list / livros sem ISBN (não solicitado)
- Integração com a CLI de escaneamento (não faz sentido no contexto de leitura)
- Estatísticas avançadas (ritmo de leitura, projeção de conclusão)
