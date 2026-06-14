# 📚 my-lib-catalog

Catalogador pessoal de biblioteca via leitor de código de barras USB.
Escaneie ISBNs sem parar — os metadados chegam em background enquanto você
continua lendo. O acervo é salvo em CSV (para planilha) e JSON Lines (para
processamento). Uma UI Streamlit permite navegar e consultar a coleção.

## Requisitos

- Python 3.12 ou superior
- Um leitor de código de barras USB (qualquer modelo que funcione como teclado)

## Instalação

```bash
# Clone e entre no diretório
git clone <repo> my-lib-catalog
cd my-lib-catalog

# Crie o ambiente virtual e instale as dependências
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

pip install -e ".[ui,dev]"         # instala requests + streamlit + pytest
```

Ou use o Makefile:

```bash
make install
```

## Uso rápido

```bash
make run        # inicia o scanner interativo
make ui         # abre a interface de consulta no navegador
make test       # roda a suite de testes
```

## Scanner (CLI)

```bash
python main.py
```

Aponte o leitor para o código de barras na contracapa. O script:

1. Valida e normaliza o ISBN (10 ou 13 dígitos)
2. Enfileira o ISBN instantaneamente — **sem esperar a rede**
3. Busca metadados em background: Open Library → Google Books → Mercado Livre → ISBNdb
4. Salva em `data/biblioteca.csv` e `data/biblioteca.jsonl`
5. Exibe o resultado no terminal assim que chegar

### Comandos durante a sessão

| Comando | Ação |
|---|---|
| `sair` / `exit` | Encerra após drenar a fila |
| `fila` | Mostra quantos ISBNs aguardam processamento |
| `reprocessar` | Tenta novamente os ISBNs sem metadados (fila deve estar vazia) |
| `Ctrl+C` | Interrompe; ISBNs pendentes são retomados na próxima sessão |

### Exemplo

```
📚  Cadastro de biblioteca — modo assíncrono
    Escaneie sem parar. Os metadados vêm em background.
    Comandos: 'sair', 'fila', 'reprocessar', Ctrl+C

ISBN [0 na fila] > 9788535914849
  → 9788535914849 enfileirado.

ISBN [1 na fila] > 9781098115784
  → 9781098115784 enfileirado.

  ✓ [9788535914849] Dom Casmurro — Machado de Assis
  ✓ [9781098115784] Machine Learning Design Patterns — Valliappa Lakshmanan, ...

ISBN [0 na fila] > sair
Sessão encerrada. 2 ISBN(s) conhecido(s).
```

## Interface de consulta (Streamlit)

```bash
streamlit run ui/app.py
# ou: make ui
```

Abra em um segundo terminal enquanto o scanner roda. A UI:

- Exibe cards com capa, título, autores e ano
- Filtra por título/autor, idioma e fonte
- Mostra tabela completa com todos os campos
- Recarrega automaticamente a cada 60 segundos

## Configuração

| Variável de ambiente | Padrão | Descrição |
|---|---|---|
| `ISBNDB_API_KEY` | `""` | Chave gratuita do [ISBNdb](https://isbndb.com/isbn-database) (500 req/mês). Melhora muito a cobertura de livros brasileiros. |

```bash
export ISBNDB_API_KEY="sua-chave-aqui"
python main.py
```

## Fontes de metadados

O sistema tenta cada fonte em ordem e usa a primeira que retornar um título:

| Ordem | Fonte | Auth | Cobertura |
|---|---|---|---|
| 1 | Open Library | Não precisa | Boa cobertura em inglês |
| 2 | Google Books | Não precisa | Boa cobertura internacional |
| 3 | Mercado Livre | Não precisa | Fallback para livros nacionais |
| 4 | ISBNdb | Chave gratuita | Ampla cobertura incluindo editoras brasileiras |

## Arquivos de saída

| Arquivo | Formato | Uso |
|---|---|---|
| `data/biblioteca.csv` | CSV com cabeçalho | Planilha (Excel / LibreOffice) |
| `data/biblioteca.jsonl` | JSON Lines | Scripts, pandas, banco de dados |
| `tmp/pendentes.txt` | Texto simples | Fila durável — recriado automaticamente |

Os diretórios `data/` e `tmp/` são criados automaticamente na primeira execução.

### Schema (11 campos)

| Campo | Tipo | Exemplo |
|---|---|---|
| `isbn` | string | `9788535914849` |
| `titulo` | string | `Dom Casmurro` |
| `autores` | string | `Machado de Assis` |
| `editora` | string | `Ática` |
| `ano` | string | `2004` |
| `paginas` | int / string | `352` |
| `idioma` | string | `pt` |
| `assuntos` | string | `Fiction, Classic` |
| `capa_url` | string | `https://...` |
| `fonte` | string | `openlibrary` |
| `data_cadastro` | string ISO 8601 | `2026-05-25T14:44:06` |

## Estrutura do projeto

```
my-lib-catalog/
├── main.py                  # CLI — entrada do usuário e orquestração
├── pyproject.toml           # Dependências e configuração do projeto
├── CLAUDE.md                # Guia para agentes de IA
├── Makefile                 # Comandos de desenvolvimento
├── catalog/
│   ├── config.py            # Caminhos e variáveis de configuração
│   ├── scanning/            # Validação e normalização de ISBN
│   ├── metadata/            # Busca de metadados (APIs) e worker
│   └── storage/             # Persistência (CSV + JSONL)
├── ui/
│   └── app.py               # Interface Streamlit (somente leitura)
├── tests/                   # Suite pytest (42 testes)
└── data/                    # Arquivos de saída (gerados)
```

## Testes

```bash
pytest              # ou: make test
pytest -v           # verbose
pytest tests/test_api.py   # somente os testes de API
```

## Limitações conhecidas

- **Códigos EAN-13 não-ISBN.** Códigos começando com `789…` (EAN nacional) não
  constam nas APIs bibliográficas.
- **Livros brasileiros sem metadados.** Open Library e Google Books têm cobertura
  fraca do catálogo nacional. O Mercado Livre é um marketplace e pode retornar
  dados imprecisos. Adicionar a chave do ISBNdb é a melhor solução.
- **Conexão obrigatória.** Sem rede, o ISBN é enfileirado e reprocessado na
  próxima sessão.

## Licença

Uso livre, sem garantias. Adapte como precisar.
