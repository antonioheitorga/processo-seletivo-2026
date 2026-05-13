"""Agente Reformulador.

Reescreve a query original do usuário para otimizar a busca semântica
no corpus de regulamentos da FIA F1 2026.
"""

import os
import time
from datetime import datetime, timezone

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama


PROMPT_TEMPLATE = """You are a Formula 1 expert. Rewrite the user's query to optimize semantic search over FIA F1 2026 technical regulations.

Rules:
- Preserve the original meaning
- Expand acronyms (e.g., DRS -> Drag Reduction System)
- Use formal regulatory vocabulary
- Always respond in English, regardless of the input language
- Output ONLY the rewritten query: no quotes, no explanations, no prefixes

Original query: {query}

Rewritten query:"""


def reformulate(state: dict) -> dict:
    """Reformula a query original para busca semântica.

    Lê: state["query_original"]
    Escreve: query_reformulada, trace (append)
    """
    inicio = time.time()
    query_original = state["query_original"]

    llm = ChatOllama(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=os.getenv("LLM_MODEL", "llama3.1:8b"),
        temperature=0.0,
    )
    chain = ChatPromptTemplate.from_template(PROMPT_TEMPLATE) | llm
    resposta = chain.invoke({"query": query_original})
    query_reformulada = resposta.content.strip().strip('"\'').strip()

    return {
        "query_reformulada": query_reformulada,
        "trace": state.get("trace", []) + [{
            "agente": "reformulator",
            "entrada": query_original,
            "saida": query_reformulada,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latencia_ms": int((time.time() - inicio) * 1000),
        }],
    }
