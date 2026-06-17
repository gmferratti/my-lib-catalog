# Design: métricas "o que tenho" na aba Acervo

**Data:** 2026-06-17
**Status:** aprovado

---

## Problema

A linha de métricas atual mostra: Total no acervo · Exibindo · Com capa · Sem metadados · Editados.

"Sem metadados" e "Editados" refletem estado operacional do catálogo, não o acervo em si.
"Exibindo" é redundante com os filtros. Nenhum número responde "que tipo de livros tenho?".

---

## Solução

Substituir os 5 `st.metric()` por 3 números grandes + painel de distribuição com idioma e assuntos.

---

## Layout

### Linha superior — 3 métricas

```
Total no acervo   |   Total de páginas   |   Com capa
      64                  18.430               8
```

### Painel de distribuição — 2 colunas (logo abaixo da linha de métricas)

```
📚 Por idioma              🏷️ Top assuntos
  Português   41  ████       Fiction         12  ████
  Inglês      18  ███        Science          9  ██
  Japonês      1             Technology       7  ██
                             Literature       6  █
                             History          4  █
```

Barras proporcionais em `█` via markdown — sem dependência nova.
Livros sem idioma ou sem assuntos são excluídos das contagens respectivas.

---

## Componente `_estatisticas(registros: list[dict]) -> dict`

Nova função auxiliar em `ui/app.py`. Computa tudo uma vez sobre a lista completa
(não sobre `filtrados` — as stats refletem o acervo inteiro):

```python
{
    "total": int,
    "total_paginas": int,          # soma de paginas onde convertível para int
    "com_capa": int,
    "idiomas": [("Português", 41), ("Inglês", 18), ...],   # ordenado por count desc
    "assuntos": [("Fiction", 12), ("Science", 9), ...],    # top 5, count desc
}
```

### Normalização de idioma

| Código recebido | Exibido como |
|---|---|
| `"pt"`, `"por"`, `"pt-BR"`, `"pt-br"` | Português |
| `"en"`, `"eng"` | Inglês |
| `"es"`, `"spa"` | Espanhol |
| `"fr"`, `"fra"` | Francês |
| `"de"`, `"deu"`, `"ger"` | Alemão |
| `"ja"`, `"jpn"` | Japonês |
| qualquer outro não vazio | código bruto (ex: `"bul"`) |
| `""` ou ausente | ignorado |

### Processamento de assuntos

Split por `","` no campo `assuntos`, strip de espaços, contagem de cada termo.
Top 5 por frequência. Termos vazios ignorados. Sem normalização de língua — os dados
refletem a fonte (PT ou EN dependendo de qual API encontrou o livro).

---

## Barras proporcionais

```python
def _barra(valor: int, maximo: int, largura: int = 20) -> str:
    preenchimento = round(valor / maximo * largura) if maximo else 0
    return "█" * preenchimento
```

Renderizado via `st.markdown()` em tabela simples com colunas de texto.

---

## Arquivos modificados

| Arquivo | Mudança |
|---|---|
| `ui/app.py` | + `_estatisticas()`, + `_barra()`, refatorar `_render_acervo()` |

Nenhuma dependência nova. Nenhuma alteração em `catalog/`.

---

## Verificação

```bash
streamlit run ui/app.py
# Aba Acervo deve mostrar:
# - 3 métricas na linha superior (Total, Páginas, Com capa)
# - 2 colunas: distribuição por idioma + top 5 assuntos
# - Sem "Sem metadados", "Editados", "Exibindo"
```
