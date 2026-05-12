# Processo Seletivo LAPES 2026

## Candidatos

| Nome | Trilha | WhatsApp |
|------|--------|----------|
| Wisley Gabriel | Trilha de Dados — Sistema Agêntico de IA | +55 91 98225-0731 |
| Antonio Heitor | Trilha de Dados — Sistema Agêntico de IA | +55 91 98129-1004 |

---

## Solução — Trilha de Dados

### Situação atual do projeto

A **pipeline de ingestão de conhecimento** foi concluída. O projeto constrói uma base vetorial a partir dos 6 documentos regulatórios da FIA F1 2026, pronta para uso em um sistema RAG multiagente.

```
PDF → Extração → Limpeza → Chunking → Embeddings → ChromaDB ✅
Sistema Multiagente RAG                                       🔄 em desenvolvimento
```

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

---

## Setup

### Pré-requisitos

- Python 3.11+
- [Ollama](https://ollama.com) instalado e rodando localmente

### 1. Instalar dependências Python

```bash
cd dados/
python3 -m pip install -r requirements.txt
```

### 2. Baixar o modelo de embedding

```bash
ollama pull nomic-embed-text
```

### 3. Executar a pipeline completa

```bash
python3 pipeline.py
```

Isso executa automaticamente os 6 passos em sequência:

| Passo | Script | O que faz |
|-------|--------|-----------|
| 1 | `01_extract.py` | Lê os PDFs e extrai texto por página via pdfplumber |
| 2 | `02_validate.py` | Valida cobertura, páginas vazias e densidade de texto |
| 3 | `03_preprocess.py` | Remove ruídos, normaliza espaços e quebras de linha |
| 4 | `04_chunk.py` | Divide os textos em chunks com LangChain |
| 5 | `05_embed_ingest.py` | Gera embeddings e indexa no ChromaDB com metadados |
| 6 | `06_verify.py` | Valida o vector store com consultas semânticas de teste |

### 4. Executar passos individuais (opcional)

```bash
python3 pipeline.py --from 5   # re-ingere no ChromaDB sem re-extrair
python3 pipeline.py --only 6   # só verifica o estado atual
```

---

## Decisões Técnicas

### Corpus
6 documentos regulatórios da FIA F1 2026 (Sections A–F), totalizando 590 páginas e ~1,5M de caracteres. Todos renomeados para padrão `snake_case`.

### Extração
**pdfplumber** — escolhido sobre PyPDF2 por preservar melhor a estrutura de texto em documentos técnicos com tabelas e layout complexo.

### Pré-processamento
Limpeza via regex: remoção de caracteres de controle, hifenização de quebra de linha, rodapés numéricos e linhas decorativas. Normalização de espaços e quebras consecutivas.

### Chunking
**RecursiveCharacterTextSplitter** (LangChain) com `chunk_size=512` e `chunk_overlap=64`. Testadas 4 configurações (256, 512, 1024, 2048 chars) — 512 oferece o melhor equilíbrio entre granularidade e contexto para RAG.

- Total de chunks: **4.591** distribuídos em 6 arquivos

### Embeddings
**`nomic-embed-text`** via Ollama (local, 274 MB). Escolhido sobre `all-MiniLM-L6-v2` por ter context window de 8.192 tokens vs. 512, e sobre OpenAI por ser 100% local sem custo por token.

### Vector Store
**ChromaDB** com similaridade cosine, client persistente em `vectorstore/`. Cada chunk indexado com metadados: `source_file`, `section`, `chunk_id`, `char_count`.

- Total indexado: **4.288 chunks** (chunks com ≥ 30 chars)
- Tempo de ingestão: ~82s em hardware local

### LLM para geração (próxima etapa)
`llama3.2` ou `gemma3:4b` via Ollama — ambos já disponíveis localmente.

---


---

A todos, desejamos um bom projeto, e boa sorte.

Atenciosamente,

Caio Johnston, Gabriel Mattos, Giovanni Braga, e Isaac Elgrably.
