import os

CSV_FILE = "data/biblioteca.csv"
ESTANTES_FILE = "data/estantes.json"
JSON_FILE = "data/biblioteca.jsonl"
PENDING_FILE = "tmp/pendentes.txt"
CAPAS_CACHE_FILE = "data/capas_cache.json"
CAPAS_MANUAIS_FILE = "data/capas_manuais.json"

CSV_HEADERS = [
    "isbn", "titulo", "autores", "editora", "ano",
    "paginas", "idioma", "assuntos", "capa_url", "fonte", "data_cadastro",
]

# Chave gratuita em https://console.cloud.google.com/ (Books API, 1000 req/dia).
# Sem a chave, usa cota anônima compartilhada — esgota facilmente.
GOOGLE_BOOKS_API_KEY = os.environ.get("GOOGLE_BOOKS_API_KEY", "")

# Chave gratuita em https://isbndb.com/isbn-database (plano Free: 500 req/mês)
ISBNDB_API_KEY = os.environ.get("ISBNDB_API_KEY", "")
