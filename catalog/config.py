import os

CSV_FILE = "data/biblioteca.csv"
ESTANTES_FILE = "data/estantes.json"
JSON_FILE = "data/biblioteca.jsonl"
PENDING_FILE = "tmp/pendentes.txt"

CSV_HEADERS = [
    "isbn", "titulo", "autores", "editora", "ano",
    "paginas", "idioma", "assuntos", "capa_url", "fonte", "data_cadastro",
]

# Chave gratuita em https://isbndb.com/isbn-database (plano Free: 500 req/mês)
# Sem a chave, livros brasileiros dificilmente serão encontrados.
# Configure via variável de ambiente: export ISBNDB_API_KEY="sua-chave"
ISBNDB_API_KEY = os.environ.get("ISBNDB_API_KEY", "")
