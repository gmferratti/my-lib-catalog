# 📚 Biblioteca ISBN

Catalogação simples de livros através de um leitor de código de barras USB.
O script lê o ISBN escaneado, busca os metadados em APIs públicas e salva o
acervo em `CSV` (para abrir no Excel/LibreOffice) e em `JSON Lines` (para
processamento posterior).

## Requisitos

- Python 3.10 ou superior
- Biblioteca [`requests`](https://pypi.org/project/requests/)
- Um leitor de código de barras USB (qualquer modelo que se comporte como
  teclado, que é a esmagadora maioria — ele "digita" o código e dispara Enter)

## Instalação

```bash
pip install requests
```

## Uso

```bash
python main.py
```

Aponte o leitor para o código de barras na contracapa do livro. O script vai:

1. Reconhecer o ISBN (13 ou 10 dígitos)
2. Buscar metadados na Open Library e, se necessário, no Google Books
3. Mostrar o título no terminal para você conferir
4. Salvar tudo nos arquivos de saída

Para encerrar: digite `sair` ou pressione `Ctrl+C`.

### Exemplo de sessão

```
📚  Cadastro de biblioteca por código de barras
    Escaneie um livro, ou digite 'sair' / Ctrl+C para encerrar.

ISBN > 9788535914849
  ⌕ buscando metadados de 9788535914849...
  ✓ Dom Casmurro — Machado de Assis  (openlibrary)
  → salvo em biblioteca.csv  (total: 1)

ISBN > 9788532530803
  ⌕ buscando metadados de 9788532530803...
  ✓ Harry Potter e a Pedra Filosofal — J.K. Rowling  (googlebooks)
  → salvo em biblioteca.csv  (total: 2)
```

## Arquivos de saída

Ambos são criados no diretório onde o script é executado e crescem em modo
*append* — você pode interromper e retomar sem perder nada.

### `biblioteca.csv`

Pensado para visualização rápida em planilha. Colunas:

| Coluna | Descrição |
|---|---|
| `isbn` | ISBN normalizado (só dígitos) |
| `titulo` | Título do livro |
| `autores` | Autores separados por vírgula |
| `editora` | Editora(s) |
| `ano` | Ano de publicação |
| `paginas` | Número de páginas |
| `idioma` | Código do idioma (ex: `pt`, `en`) |
| `assuntos` | Categorias/assuntos |
| `capa_url` | URL da imagem da capa |
| `fonte` | `openlibrary`, `googlebooks` ou `nao_encontrado` |
| `data_cadastro` | Timestamp ISO 8601 da leitura |

### `biblioteca.jsonl`

Um objeto JSON por linha, com os mesmos campos. Útil para processar com
`pandas`, importar para um banco de dados, ou consumir em outros scripts.

```python
import json
with open("biblioteca.jsonl") as f:
    livros = [json.loads(linha) for linha in f]
```

## Funcionalidades

- ✅ Validação de ISBN (10 ou 13 dígitos)
- ✅ Detecção automática de duplicatas
- ✅ Duas fontes de metadados (Open Library + Google Books como fallback)
- ✅ Sem necessidade de chave de API
- ✅ Saída em dois formatos simultaneamente
- ✅ Modo append — pode parar e retomar a qualquer momento

## Limitações conhecidas

- **Códigos EAN-13 que não são ISBN.** Apenas códigos começando com `978` ou
  `979` são ISBNs reais. Alguns livros brasileiros antigos têm códigos `789…`
  (EAN nacional) que não constam em nenhuma das APIs.
- **Livros nacionais com metadados incompletos.** A Open Library tem cobertura
  fraca de catálogo brasileiro; o Google Books cobre melhor mas nem sempre.
  Caso queira melhorar isso, é possível adicionar a
  [Mercado Editorial API](https://api.mercadoeditorial.org/) (requer cadastro
  gratuito).
- **Conexão de internet obrigatória.** Sem rede, o script ainda registra o ISBN,
  mas com todos os campos vazios.

## Estrutura do projeto

```
.
├── biblioteca_isbn.py    # Script principal
├── README.md             # Este arquivo
├── biblioteca.csv        # (gerado) Acervo em planilha
└── biblioteca.jsonl      # (gerado) Acervo em JSON Lines
```

## Licença

Uso livre, sem garantias. Adapte como precisar.