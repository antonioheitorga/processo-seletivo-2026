# Processo Seletivo LAPES 2026

## Candidatos

| Nome | WhatsApp |
|------|----------|
| Wisley Gabriel | +55 91 98225-0731 |
| Antonio Heitor | +55 91 98129-1004 |

---

## Solução — Trilha de Dados

### Situação atual do projeto

A **pipeline de ingestão de conhecimento** foi concluída. O projeto constrói uma base vetorial a partir dos 6 documentos regulatórios da FIA F1 2026, pronta para uso em um sistema RAG multiagente.

```
PDF → Extração → Limpeza → Chunking → Embeddings → ChromaDB ✅
Reformulador                                                  ✅
Retriever                                                     ✅
Web Searcher                                                  ✅
Gerador                                                       ✅
Orquestrador                                                  🔄 em desenvolvimento
Interface Streamlit                                           🔜
```

📐 Arquitetura completa documentada em [docs/architecture.md](docs/architecture.md).

### Estrutura do projeto

```
dados/
├── corpus/          # 6 PDFs FIA 2026 F1 Regulations
├── scripts/
│   ├── 01_extract.py       # Extração de texto (pdfplumber)
│   ├── 02_validate.py      # Validação da extração
│   ├── 03_preprocess.py    # Limpeza e normalização
│   ├── 04_chunk.py         # Chunking semântico
│   ├── 05_embed_ingest.py  # Embeddings + ingestão no ChromaDB
│   └── 06_verify.py        # Verificação do vector store
├── pipeline.py      # Orquestrador — executa todos os passos
└── requirements.txt
```

Os diretórios `extracted/`, `processed/`, `chunks/` e `vectorstore/` são gerados automaticamente pela pipeline e estão no `.gitignore`.

```
agents/
├── reformulator.py    # Reescreve a query para busca semântica
├── retriever.py       # Busca vetorial no ChromaDB com controle de confiança
├── web_searcher.py    # Fallback via Tavily quando o corpus não é suficiente
└── generator.py       # Gera resposta final com contexto corpus/web

tests/
├── test_reformulator.py
├── test_retriever.py
├── test_retriever_integration.py
├── test_web_searcher.py
├── test_generator.py
└── conftest.py        # Carrega .env antes dos testes

docs/
└── architecture.md    # Diagrama do fluxo + contratos dos agentes
```

---

## Setup

### Pré-requisitos

- Python 3.11+
- [Ollama](https://ollama.com) instalado e rodando localmente
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (opcional para subir Ollama via container)

### 1. Instalar dependências Python

Na raiz do projeto (`processo-seletivo-2026/`):

```bash
python3 -m pip install -r requirements.txt
```

### 2. Subir Ollama e baixar modelos

Opção A — Ollama local:

```bash
ollama pull llama3.1:8b
ollama pull nomic-embed-text
```

Opção B — Docker Compose:

```bash
docker compose up -d ollama
docker compose ps
docker exec -it f1-rag-ollama ollama pull llama3.1:8b
docker exec -it f1-rag-ollama ollama pull nomic-embed-text
```

### 3. Configurar variáveis de ambiente

```bash
cp .env.example .env
```

Preencha especialmente:
- `TAVILY_API_KEY` para busca web
- parâmetros de Retriever (`RETRIEVER_THRESHOLD`, `RETRIEVER_TOP_K`) se necessário

### 4. Executar pipeline de dados (opcional para rebuild da base vetorial)

```bash
cd dados/
python3 pipeline.py
```

Isso executa os 6 passos em sequência:

| Passo | Script | O que faz |
|-------|--------|-----------|
| 1 | `01_extract.py` | Lê os PDFs e extrai texto por página via pdfplumber |
| 2 | `02_validate.py` | Valida cobertura, páginas vazias e densidade de texto |
| 3 | `03_preprocess.py` | Remove ruídos, normaliza espaços e quebras de linha |
| 4 | `04_chunk.py` | Divide os textos em chunks com LangChain |
| 5 | `05_embed_ingest.py` | Gera embeddings e indexa no ChromaDB com metadados |
| 6 | `06_verify.py` | Valida o vector store com consultas semânticas de teste |

Rodar passos individuais:

```bash
python3 pipeline.py --from 5
python3 pipeline.py --only 6
```

---

## Sistema RAG Multiagente

### Sprint 1 — Reformulador (`agents/reformulator.py`)
Responsável por reescrever a query para melhorar recuperação semântica no corpus FIA 2026.

Saída principal:
- `query_reformulada`
- `trace` (append)

### Sprint 3 — Retriever (`agents/retriever.py`)
Responsável por busca vetorial no ChromaDB com avaliação de confiança.

Leituras:
- `query_reformulada`

Saída (`retriever_result`):
- `query`
- `threshold`
- `top_k`
- `best_score`
- `fallback_to_web`
- `confidence_warning`
- `total_hits`
- `hits` (`content`, `score`, `metadata`)

Também appenda em `trace`.

### Sprint 3 — Web Searcher (`agents/web_searcher.py`)
Executa fallback de busca web via Tavily quando necessário.

Saída (`web_result`):
- `resultados` (`titulo`, `trecho`, `url`)
- `encontrou`

Também appenda em `trace`.

### Sprint 4 — Gerador (`agents/generator.py`)
Gera resposta final com contexto do corpus e/ou web.

Entradas:
- `query_original` / `query_reformulada`
- `retriever_result`
- `web_result` (com compatibilidade para `resultados_web` / `encontrou_web`)

Saídas:
- `generator_result`:
  - `answer`
  - `sources_used` (`corpus`, `web`, `hybrid`, `none`)
  - `low_confidence`
  - `confidence_notice`
- campos compatíveis no state:
  - `resposta`
  - `fonte`
  - `low_confidence`
  - `confidence_warning`
- `trace` (append)

---

## Variáveis de ambiente relevantes

- `OLLAMA_BASE_URL` (default: `http://localhost:11434`)
- `LLM_MODEL` (default: `llama3.1:8b`)
- `EMBED_MODEL` (default: `nomic-embed-text`)
- `CHROMA_COLLECTION` (default: `fia_2026_regulations`)
- `RETRIEVER_THRESHOLD` (default: `0.30`)
- `RETRIEVER_TOP_K` (default: `5`)
- `TAVILY_API_KEY` (obrigatória para web search)

---

## Testes

### Testes rápidos (unitários/focados)

```bash
pytest -q tests/test_generator.py tests/test_retriever.py tests/test_web_searcher.py
```

### Suite completa

```bash
pytest -q
```

### Integração

```bash
pytest -q -m integration
```

---

## Segurança e versionamento

- **Nunca subir dados sensíveis**:
  - `.env`
  - chaves de API
  - arquivos temporários locais
- Manter `.gitignore` corretamente configurado para impedir versionamento acidental de segredos.
