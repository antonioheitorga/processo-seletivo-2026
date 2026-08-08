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
Judge/Verifier                                                ✅
Orquestrador (hub-and-spoke)                                  ✅
Observabilidade (trace JSON enriquecido)                      ✅
Interface Streamlit                                           ✅
```

📐 Arquitetura completa documentada em [docs/architecture.md](docs/architecture.md).
📋 Justificativa do corpus (os 4 pontos exigidos pelo edital) em [docs/justificativa_corpus.md](docs/justificativa_corpus.md).
📊 Benchmark de avaliação (20 pares, metodologia, resultados) em [evaluation/README.md](evaluation/README.md).

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
├── generator.py       # Gera texto a partir do contexto recebido (responsabilidade única)
└── judge.py           # Valida a resposta com base em sinais de confiança

orchestration/
└── orchestrator.py    # Nó central hub-and-spoke — decide o próximo agente a cada passo

tests/
├── test_reformulator.py
├── test_retriever.py
├── test_retriever_integration.py
├── test_web_searcher.py
├── test_generator.py
├── test_judge.py
├── test_orchestrator.py
└── conftest.py        # Carrega .env antes dos testes

docs/
├── architecture.md            # Diagrama do fluxo + contratos dos agentes
└── justificativa_corpus.md    # Justificativa do corpus (4 pontos exigidos pelo edital)

evaluation/
├── dataset.json        # 20 pares pergunta/resposta (validação + teste)
├── run_benchmark.py     # Executa o pipeline completo e pontua cada resposta
├── README.md            # Metodologia de avaliação
└── results/              # Resultados gerados (JSON + Markdown) por split
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
Responsabilidade única: gerar texto a partir do contexto recebido. Não calcula
métricas de fonte nem flags de confiança — isso é do Orquestrador.

Anti-alucinação por design: se corpus e web estão ambos vazios, NÃO chama o LLM
e retorna `{"result": null, "reason": ...}`.

Entradas:
- `query_original`, `query_reformulada`
- `retriever_result`, `web_result`

Saída (`generator_result`):
- `result` — `"ok"` ou `None` (quando contexto vazio)
- `answer` — texto da resposta (vazio se `result=None`)
- `reason` — motivo do `None` quando aplicável

Também appenda em `trace`.

### Sprint 4 — Judge/Verifier (`agents/judge.py`)
Valida a resposta gerada com base em sinais de confiança. Determinístico (sem LLM).
Aprova quando há `answer` + evidência (corpus ou web) + não-low_confidence.

Saída (`judge_result`):
- `approved` — bool
- `decision` — `"approve"` ou `"revise"`
- `sources_used` — eco do generator
- `reasons` — lista de motivos quando rejeitado (`empty_answer`, `no_evidence`, `low_confidence`)

Também escreve `needs_revision` e appenda em `trace`.

### Sprint 4 — Orquestrador (`orchestration/orchestrator.py`)
Nó central hub-and-spoke. Todo agente, ao terminar, retorna ao Orquestrador,
que inspeciona o estado e decide qual chamar a seguir. Roteamento determinístico
(sem LLM), com `reason` por decisão registrado no trace.

Responsabilidades:
- Decidir o próximo agente baseado no estado atual
- Calcular `fonte` (`corpus` / `web` / `hybrid` / `none`) e `low_confidence`
- Aplicar anti-alucinação por design (aborta geração se corpus + web vazios)
- Montar a resposta final para o usuário

Componentes expostos:
- `GraphState` — TypedDict com todos os campos do estado compartilhado
- `build_graph()` — monta e compila o grafo
- `run(query_original, session_id=None)` — helper que dispara o grafo e gera `session_id` automaticamente via `uuid4` se não fornecido

Exemplo de uso:

```python
from dotenv import load_dotenv
load_dotenv()

from orchestration.orchestrator import run

resultado = run("What is DRS?")
print(resultado["fonte"])           # "corpus" | "web" | "hybrid" | "none"
print(resultado["resposta"])
print(resultado["low_confidence"])  # bool
print(resultado["trace"])           # lista com entrada de cada agente + orquestrador intercalado
```

---

## Como executar o sistema

Com o Ollama rodando, o `.env` configurado e as dependências instaladas:

```bash
streamlit run app.py
```

A interface sobe em `http://localhost:8501`. Cada query executada gera um arquivo `traces/{session_id}.json` com o trace completo (query, resposta, fonte, latência por agente).

---

## Variáveis de ambiente relevantes

- `OLLAMA_BASE_URL` (default: `http://localhost:11434`)
- `LLM_MODEL` (default: `llama3.1:8b`)
- `EMBED_MODEL` (default: `nomic-embed-text`)
- `CHROMA_COLLECTION` (default: `fia_2026_regulations`)
- `RETRIEVER_THRESHOLD` (default: `0.78`, calibrado empiricamente — ver `evaluation/README.md`)
- `RETRIEVER_TOP_K` (default: `5`)
- `TAVILY_API_KEY` (obrigatória para web search)
- `TRACES_DIR` (default: `./traces`) — pasta onde o trace de cada execução é salvo

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


