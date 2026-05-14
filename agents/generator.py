"""Agente Gerador.

Monta a resposta final usando contexto do corpus (Retriever)
e/ou contexto da web (Web Searcher), com aviso de baixa confiança
quando necessário.
"""

import os
import time
from datetime import datetime, timezone

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama


PROMPT_TEMPLATE = """You are an expert assistant for FIA Formula 1 2026 regulations.

User query:
{query}

Available context from corpus:
{corpus_context}

Available context from web:
{web_context}

Instructions:
- Answer using only the provided context.
- If context is insufficient, clearly say the answer may be uncertain.
- Prefer corpus context for regulatory details.
- Keep the answer concise and objective.

Final answer:"""


def _build_contexts(state: dict) -> tuple[str, str, str, bool, str]:
    query = (state.get("query_reformulada") or state.get("query_original") or "").strip()
    if not query:
        raise ValueError("State inválido: informe 'query_reformulada' ou 'query_original'.")

    retriever_result = state.get("retriever_result") or {}

    web_result = state.get("web_result")
    if web_result is None:
        resultados = state.get("resultados_web")
        encontrou = state.get("encontrou_web")
        if resultados is not None or encontrou is not None:
            web_result = {
                "resultados": resultados or [],
                "encontrou": bool(encontrou),
            }
        else:
            web_result = {}

    hits = retriever_result.get("hits", [])
    corpus_context = "\n\n".join([h.get("content", "") for h in hits if h.get("content")]).strip()

    web_items = web_result.get("resultados", [])
    web_context = "\n\n".join(
        [
            f"Título: {item.get('titulo', '')}\nTrecho: {item.get('trecho', '')}\nURL: {item.get('url', '')}"
            for item in web_items
        ]
    ).strip()

    fallback_to_web = bool(retriever_result.get("fallback_to_web", False))
    confidence_warning = retriever_result.get("confidence_warning") or ""
    low_confidence = fallback_to_web

    return query, corpus_context, web_context, low_confidence, confidence_warning


def generate(state: dict) -> dict:
    """Gera resposta final com contexto do corpus e/ou web.

    Lê: query_original/query_reformulada, retriever_result, web_result
    Escreve: generator_result, trace (append)
    """
    inicio = time.time()

    query, corpus_context, web_context, low_confidence, confidence_warning = _build_contexts(state)

    llm = ChatOllama(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=os.getenv("LLM_MODEL", "llama3.1:8b"),
        temperature=0.0,
    )

    chain = ChatPromptTemplate.from_template(PROMPT_TEMPLATE) | llm
    resposta = chain.invoke(
        {
            "query": query,
            "corpus_context": corpus_context or "N/A",
            "web_context": web_context or "N/A",
        }
    )
    answer = resposta.content.strip()

    if corpus_context and web_context:
        sources_used = "hybrid"
    elif corpus_context:
        sources_used = "corpus"
    elif web_context:
        sources_used = "web"
    else:
        sources_used = "none"

    confidence_notice = confidence_warning if low_confidence else None

    resposta = answer
    fonte = sources_used

    generator_result = {
        "answer": answer,
        "sources_used": sources_used,
        "low_confidence": low_confidence,
        "confidence_notice": confidence_notice,
    }

    return {
        "generator_result": generator_result,
        "resposta": resposta,
        "fonte": fonte,
        "low_confidence": low_confidence,
        "confidence_warning": confidence_notice,
        "trace": state.get("trace", [])
        + [
            {
                "agente": "generator",
                "entrada": query,
                "saida": f"resposta gerada com fonte={fonte}, low_confidence={low_confidence}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "latencia_ms": int((time.time() - inicio) * 1000),
            }
        ],
    }
