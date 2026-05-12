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

O LAPES — Laboratório de Pesquisa em Engenharia de Software — está com as seleções abertas para 2026. O processo é composto por um desafio técnico e uma entrevista com o responsável pela área de interesse.

Há duas trilhas disponíveis. Você pode seguir pela que mais se alinha ao seu perfil ou encarar ambas, inclusive mesclando os desafios em um único projeto, se fizer sentido.

---

## Como entregar

1. Faça um fork deste repositório.
2. O repositório deve permanecer público do início ao fim do processo seletivo.
3. No README do seu fork, inclua:
   - nome(s) do(s) candidato(s) e trilha(s) escolhida(s);
   - contato: e-mail institucional e/ou telefone com WhatsApp;
   - instruções de setup e decisões técnicas, conforme o PDF de cada desafio.

O PDF de cada trilha está na pasta correspondente:

```
processo-seletivo-2026/
├── dados/    ← Trilha de Dados / IA
└── dev/      ← Trilha de Desenvolvimento
```

**Em dupla:** apenas um dos candidatos faz o fork; o segundo contribui no mesmo repositório. Ambos os nomes devem constar no README final.

---

## Trilha de Dados — Sistema Agêntico de IA

Construa um sistema multiagente capaz de responder perguntas sobre um corpus de documentos a sua escolha, combinando recuperação vetorial (RAG) com busca na web como fallback.

**Prazo:** 17 de julho de 2026, até 23:59 (BRT).
**Formato:** individual ou dupla.
**Desafio completo:** [`dados/desafio.pdf`](dados/desafio.pdf)

Dúvidas: Giovanni Braga — [e-mail institucional](mailto:giovanni23070008@aluno.cesupa.br)

---

## Trilha de Desenvolvimento — Mini E-commerce

Desenvolver uma plataforma de e-commerce simplificada. Um desafio fullstack(frontend, backend e devops), abordando conceitos como cache, rate limiting, testes automatizadoes e entre outros.

**Prazo:** 17 de julho de 2026, até 23:59 (BRT).
**Formato:** individual ou dupla.
**Desafio completo:** [`dev/desafio.pdf`](dev/desafio.pdf)

Dúvidas: Gabriel Mattos — [e-mail institucional](mailto:gabriel22070059@aluno.cesupa.br)

---

## Apresentações

As apresentações serão realizadas nas primeiras semanas de agosto. Data e horário serão definidos com cada candidato pelo responsável da respectiva trilha. Detalhes sobre formato e duração serão divulgados em breve.

---

## Avaliação

Em ambas as trilhas, a nota final é composta por **50% do desafio técnico** e **50% da entrevista** com o responsável pela área. Todos os candidatos que entregarem o desafio são convidados para a entrevista automaticamente. Mais detalhes sobre o formato da entrevista serão divulgados em breve.

Candidatos não selecionados após a entrevista recebem feedback ao final do processo.

---

## Sobre o uso de IA

O uso de ferramentas de IA generativa é permitido — faz parte do dia a dia do desenvolvimento moderno. O desafio avalia o seu conhecimento, não o da máquina. Você deve ser capaz de explicar seu código, justificar cada decisão técnica e defender sua arquitetura na apresentação. Copiar sem compreender será evidente na review.

---

## FAQ

**Existe algum pré-requisito (curso, período, vínculo institucional)?**
Não.

**Posso me inscrever nas duas trilhas?**
Sim. Você pode entregar as duas trilhas separadamente ou mesclá-las em um único projeto, se houver fluidez entre os escopos.

**Deploy público é obrigatório?**
Não. Basta o repositório rodando localmente conforme o README. Deploy automatizado é diferencial (pontuação extra), conforme detalhado no PDF do desafio.

**Atraso resulta em penalização ou desclassificação?**
Penalização. O prazo encerra em 17/07/2026 às 23:59. Commits feitos depois do prazo são aceitos, mas implicam desconto na nota do desafio.

**Como faço para tirar dúvidas durante o desafio ou reportar inconsistências?**
Por contato direto com os responsáveis abaixo. Dúvidas específicas de uma trilha vão para o responsável da área; dúvidas gerais sobre o processo podem ser endereçadas a qualquer um.

- Caio Johnston — [e-mail institucional](mailto:caio21070002@aluno.cesupa.br)
- Gabriel Mattos — [e-mail institucional](mailto:gabriel22070059@aluno.cesupa.br)
- Giovanni Braga — [e-mail institucional](mailto:giovanni23070008@aluno.cesupa.br)
- Isaac Elgrably

Gabriel e Giovanni são da turma CC7NA e podem ser procurados pessoalmente no CESUPA, nos horários da turma (tarde e noite).

Contato organizacional: contato.lapes@gmail.com

---

A todos, desejamos um bom projeto, e boa sorte.

Atenciosamente,

Caio Johnston, Gabriel Mattos, Giovanni Braga, e Isaac Elgrably.
