# Sistema de Séries e Volumes — Design Spec

## Problema

Livros de uma mesma série chegam com títulos inconsistentes das APIs:
- `"MIL PLATOS - VOL. 4 CAPITALISMO E ESQUIZOFRENIA"` (all caps, separador "/")
- `"Mil platôs"` (sem número de volume)
- `"Sociologia geral Vol.I"` (numeral romano, sem espaço)

O resultado: a mesma série aparece de formas diferentes no acervo, sem relação entre os volumes.

## Objetivo

Garantir que qualquer livro de série seja gravado e exibido no formato canônico, tanto ao escanear quanto ao editar manualmente.

---

## Formato Canônico

```
{Série} — Vol. {N}: {Subtítulo}
```

Exemplos:
- `Mil Platôs — Vol. 4: Capitalismo e Esquizofrenia`
- `Sociologia Geral — Vol. 1`
- `Python Fluente, 2ª edição — Vol. 2`

Regras:
- Numerais sempre arábicos (I → 1, II → 2, etc.)
- Separador fixo: ` — Vol. N`
- Subtítulo separado por `: ` — omitido se vazio
- Casing do nome da série: preservado como o usuário digitou no dialog (não forçamos Title Case no nome da série, pois pode ser artístico)

---

## Arquitetura

### Novo módulo: `catalog/series.py`

Duas funções públicas:

```python
def detectar_serie(titulo: str) -> dict | None:
    """
    Tenta extrair serie, volume e subtítulo de um título bruto.
    Retorna dict {"serie": str, "volume": int, "subtitulo": str}
    ou None se não detectar padrão de volume.
    """

def compor_titulo(serie: str, volume: int, subtitulo: str = "") -> str:
    """
    Compõe o título canônico a partir dos componentes.
    Ex: compor_titulo("Mil Platôs", 4, "Capitalismo e Esquizofrenia")
        → "Mil Platôs — Vol. 4: Capitalismo e Esquizofrenia"
    """
```

**Padrões reconhecidos por `detectar_serie`:**

| Padrão no título | Exemplo |
|---|---|
| `VOL. N`, `Vol. N`, `vol N`, `volume N` | `VOL. 4`, `volume 2` |
| `V. N`, `V.N` | `V. 03`, `V.03` |
| `Vol.I`, `Vol. II` (romano) | `Vol.I`, `Vol. III` |
| `Tomo N`, `Parte N` | `Tomo 2`, `Parte I` |
| Separadores entre série e volume: ` - `, ` / `, ` : `, espaço | qualquer dos acima |

Romanos suportados: I a X (cobre 99% dos casos reais).

O texto antes do padrão de volume é a série. O texto depois (se houver) é o subtítulo. Tudo é strip()ado e múltiplos espaços normalizados.

**Fronteira de módulo:** `catalog/series.py` importa apenas stdlib. Pode ser importado por `catalog/storage` e `ui/utils`.

### Hook em `catalog/storage/persistence.py`

Em `salvar()`, após montar o dict do registro, antes de gravar:

```python
from catalog.series import detectar_serie, compor_titulo

detectado = detectar_serie(registro.get("titulo", ""))
if detectado:
    registro["titulo"] = compor_titulo(**detectado)
```

Isso garante que qualquer livro salvo pelo worker de scan chega normalizado ao JSONL/CSV.

---

## UI: Edit Dialog

Em `ui/utils.py`, função `_dialog_editar`:

1. Ao abrir o dialog: `detectar_serie(titulo)` roda silenciosamente.
2. Se detectar: toggle "É parte de uma série" começa **ativado**, campos pré-preenchidos.
3. Se não detectar: toggle começa **desativado** — sem ruído para livros normais.

Layout quando toggle ativo:

```
Título  [desabilitado — preenchido automaticamente]
☑ É parte de uma série

  Série:    [ Mil Platôs              ]
  Volume nº: [ 4 ]   Subtítulo: [ Capitalismo e Esquizofrenia ]
```

Comportamento ao salvar:
- Toggle ativo: `titulo = compor_titulo(serie, volume, subtitulo)` antes de `_salvar_edicao`
- Toggle inativo: `titulo` = valor do campo texto livre (comportamento atual)

O campo `titulo` (texto livre) fica **disabled** enquanto toggle está ativo, para evitar conflito entre a edição manual e a composição automática.

---

## Migração

Script `scripts/migrar_series.py`:

- Para cada registro, roda `detectar_serie(titulo)`.
- Se detectar: reescreve `titulo` com `compor_titulo()`.
- Se **não** detectar mas o título parecer candidato a série (heurística: título idêntico a outro já no acervo, sem volume): imprime aviso para revisão manual.
- Reescreve JSONL + CSV via `reescrever_registros()`.
- Idempotente: rodar duas vezes não altera resultado.

---

## Testes

Arquivo: `tests/test_series.py`

Casos de detecção:
- `"MIL PLATOS - VOL. 4 CAPITALISMO E ESQUIZOFRENIA"` → `{serie: "MIL PLATOS", volume: 4, subtitulo: "CAPITALISMO E ESQUIZOFRENIA"}`
- `"MIL PLATOS - CAPITALISMO E ESQUIZOFRENIA / V. 03"` → volume 3
- `"MIL PLATOS - VOL. 05 - CAPITALISMO E ESQUIZOFRENIA"` → volume 5
- `"Sociologia geral Vol.I"` → `{serie: "Sociologia geral", volume: 1, subtitulo: ""}`
- `"Sociologia geral - Vol. 2: Habitus e Campo"` → `{serie: "Sociologia geral", volume: 2, subtitulo: "Habitus e Campo"}`
- `"Python Fluente, 2ª edição, volume 2 versao standard"` → `{serie: "Python Fluente, 2ª edição", volume: 2, subtitulo: ""}`
- `"Dom Casmurro"` → `None`
- `"O Senhor dos Anéis"` → `None`

Casos de composição:
- `compor_titulo("Mil Platôs", 4, "Capitalismo e Esquizofrenia")` → `"Mil Platôs — Vol. 4: Capitalismo e Esquizofrenia"`
- `compor_titulo("Sociologia Geral", 1, "")` → `"Sociologia Geral — Vol. 1"`
- `compor_titulo("Python Fluente, 2ª edição", 2, "")` → `"Python Fluente, 2ª edição — Vol. 2"`

Integração:
- `salvar()` com título bruto `"MIL PLATOS - VOL. 4"` → JSONL contém `"Mil Platos — Vol. 4"` (sem subtítulo)
- `salvar()` com título sem padrão → JSONL contém título inalterado

---

## Arquivos Modificados

| Arquivo | Mudança |
|---|---|
| `catalog/series.py` | Novo módulo |
| `catalog/storage/persistence.py` | Hook em `salvar()` |
| `ui/utils.py` | Toggle + campos no `_dialog_editar` |
| `scripts/migrar_series.py` | Novo script de migração |
| `tests/test_series.py` | Testes unitários e de integração |

Nenhuma mudança em `catalog/config.py` — o schema de campos não muda.
