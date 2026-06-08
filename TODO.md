# TODO

## ✅ Concluído

- [x] **Módulo de validação/normalização de ISBN** (`catalog/isbn.py`)
- [x] **Busca de metadados em múltiplas APIs** (`catalog/api.py`)
  - Open Library, Google Books, Mercado Livre, ISBNdb (fallback chain)
- [x] **Worker assíncrono em background** (`catalog/worker.py`)
  - Fila de processamento com threading
  - Persistência de pendentes entre sessões
- [x] **Persistência em CSV + JSON Lines** (`catalog/persistence.py`)
  - Append mode, lock thread-safe, reescrita
- [x] **CLI interativa** (`main.py`)
  - Leitura de ISBN via input/barcode scanner
  - Comandos: `sair`, `fila`, `reprocessar`
  - Reprocessamento de registros sem metadados
- [x] **Configuração centralizada** (`catalog/config.py`)

## 🔜 Pendente

- [ ] **Interface visual com Flask**
  - CRUD web do acervo
  - Busca e filtros
  - Upload de capas
  - Exportação

- [ ] **Sistema de busca dos metadados a partir do ISBN**
  - (Parcial) APIs já implementadas
  - Melhorias: cache, mais fontes, tratamento de erros

- [ ] **Organizador de prateleiras**
  - Gerenciamento de localização física (estante, prateleira)
  - Sugestão de organização por assunto/autor

- [ ] **Testes automatizados** (`tests/`)
  - ISBN validation tests
  - Persistence tests
  - API mock tests
  - Worker tests
