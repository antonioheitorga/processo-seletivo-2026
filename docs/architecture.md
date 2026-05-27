# Arquitetura — F1 RAG System

Sistema multiagente de IA para responder perguntas sobre Fórmula 1.
Combina busca vetorial em corpus próprio (RAG) com fallback para web via Tavily.

---

## Fluxo do sistema

```mermaid
flowchart TD
    U(["Usuário"]) -->|query_original| REFORM

    REFORM["Reformulador\nllama3.1:8b · temp=0.0"]
    REFORM -->|query_reformulada| RET

    RET["Retriever\nChromaDB · nomic-embed-text"]
    RET --> ROUTER["Router/Planner\nDeterminístico"]

    ROUTER -->|route_decision=generator| GEN
    ROUTER -->|route_decision=web_searcher| WS

    WS["Web Searcher\nTavily API"]
    WS --> GEN

    GEN["Gerador\nllama3.1:8b"]
    GEN --> JUDGE["Judge/Verifier\nDeterminístico"]

    JUDGE -->|approved| UI(["Streamlit"])
    JUDGE -->|needs_revision=True| UI

    style REFORM fill:#dbeafe,stroke:#3b82f6
    style RET    fill:#dcfce7,stroke:#22c55e
    style ROUTER fill:#ede9fe,stroke:#7c3aed
    style WS     fill:#fef9c3,stroke:#eab308
    style GEN    fill:#fce7f3,stroke:#ec4899
    style JUDGE  fill:#fee2e2,stroke:#ef4444
```

---

## Por que esse fluxo?

| Decisão | Motivo |
|---|---|
| Reformulador roda sempre | Garante query semanticamente otimizada para recuperação |
| Router/Planner explícito | Separa decisão de roteamento do retriever e evita lógica monolítica implícita |
| Orquestrador sem LLM | Transições determinísticas, auditáveis e mais baratas |
| Judge/Verifier no final | Valida suficiência de evidência e sinaliza revisão quando resposta não está bem fundamentada |

---

## GraphState — estado compartilhado entre os agentes

| Campo | Tipo | Escrito por | Lido por |
|---|---|---|---|
| `query_original` | `str` | Orquestrador (START) | Reformulador, Gerador |
| `session_id` | `str` | Orquestrador (START) | Todos (trace) |
| `query_reformulada` | `str` | Reformulador | Retriever, Web Searcher |
| `retriever_result` | `dict` | Retriever | Router, Gerador |
| `route_decision` | `str` | Router | Orquestrador (edge condicional) |
| `web_result` | `dict\|None` | Web Searcher | Gerador, Judge |
| `resultados_web` | `list[dict]\|None` | Orquestrador/Web Searcher (compat) | Gerador |
| `encontrou_web` | `bool\|None` | Orquestrador/Web Searcher (compat) | Gerador |
| `fonte` | `str` | Orquestrador ou Gerador | Streamlit |
| `low_confidence` | `bool` | Orquestrador ou Gerador | Streamlit |
| `confidence_warning` | `str\|None` | Retriever ou Gerador | Streamlit |
| `resposta` | `str` | Gerador | Judge, Streamlit |
| `generator_result` | `dict` | Gerador | Judge, Streamlit |
| `judge_result` | `dict` | Judge | Streamlit |
| `needs_revision` | `bool` | Judge | Streamlit |
| `trace` | `list[dict]` | Todos (append) | Streamlit, export JSON |

### `retriever_result` — shape completo

```python
{
    "query":              str,       # query que foi buscada
    "threshold":          float,     # valor do threshold usado
    "top_k":              int,       # número máximo de resultados pedidos
    "total_hits":         int,       # quantos chunks passaram o threshold
    "best_score":         float,     # score do chunk mais relevante (0.0 se nenhum)
    "fallback_to_web":    bool,      # True se nenhum chunk passou o threshold
    "confidence_warning": str|None,  # aviso quando baixa confiança
    "hits": [
        {
            "content":  str,   # texto do chunk
            "score":    float, # similaridade coseno (0.0 a 1.0)
            "metadata": dict,  # source_file, section, chunk_id, char_count
        }
    ]
}
```

### `web_result` — shape completo

```python
{
    "resultados": [
        {
            "titulo": str,
            "trecho": str,
            "url":    str,
        }
    ],
    "encontrou": bool,
}
```

### `trace` — cada agente appenda

```python
{
    "agente":      str,        # "reformulator" | "retriever" | "router" | "web_searcher" | "generator" | "judge"
    "entrada":     str | dict,
    "saida":       str | dict,
    "timestamp":   str,        # ISO 8601
    "latencia_ms": int,
}
```

---

## Contratos dos agentes

| Agente | Arquivo | Usa LLM | Lê do state | Escreve no state |
|---|---|---|---|---|
| **Reformulador** | `agents/reformulator.py` | ✅ llama3.1:8b | `query_original` | `query_reformulada`, `trace` |
| **Retriever** | `agents/retriever.py` | ❌ | `query_reformulada` | `retriever_result`, `trace` |
| **Router/Planner** | `orchestration/orchestrator.py` (node `router`) | ❌ | `retriever_result` | `route_decision`, `trace` |
| **Web Searcher** | `agents/web_searcher.py` | ❌ | `query_reformulada` | `web_result`, `trace` |
| **Gerador** | `agents/generator.py` | ✅ llama3.1:8b | `query_original/query_reformulada`, `retriever_result`, `web_result` (ou `resultados_web`/`encontrou_web`) | `generator_result`, `resposta`, `fonte`, `low_confidence`, `confidence_warning`, `trace` |
| **Judge/Verifier** | `agents/judge.py` | ❌ | `generator_result`, `retriever_result`, `web_result` | `judge_result`, `needs_revision`, `trace` |
| **Orquestrador** | `orchestration/orchestrator.py` | ❌ | estado compartilhado | encadeamento dos nós e export de trace |

---

## Stack tecnológico

| Camada | Tecnologia | Onde é usado |
|---|---|---|
| Linguagem | Python 3.11+ | Todo o projeto |
| Orquestração | LangGraph | `orchestration/orchestrator.py` |
| LLM | Ollama · `llama3.1:8b` | Reformulador, Gerador |
| Embeddings | Ollama · `nomic-embed-text` | Retriever |
| Vector store | ChromaDB | Retriever |
| Busca web | Tavily API | Web Searcher |
| Interface | Streamlit | `app.py` |
| Infraestrutura | Docker Compose | Serviço `ollama` |
| Testes | pytest | `tests/` |

---

## Variáveis de ambiente

| Variável | Default | Descrição |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Endereço do servidor Ollama |
| `LLM_MODEL` | `llama3.1:8b` | Modelo LLM para Reformulador e Gerador |
| `EMBEDDING_MODEL` | `nomic-embed-text` | Modelo de embeddings para o Retriever |
| `CHROMA_PERSIST_DIR` | `./dados/vectorstore` | Caminho do vector store persistente |
| `CHROMA_COLLECTION` | `fia_2026_regulations` | Nome da coleção no ChromaDB |
| `RETRIEVER_THRESHOLD` | `0.75` | Similaridade mínima para usar um chunk |
| `RETRIEVER_TOP_K` | `5` | Número máximo de chunks retornados |
| `TAVILY_API_KEY` | — | Chave da API Tavily (obrigatória para web search) |
| `TRACES_DIR` | `./traces` | Diretório para export de traces JSON |
