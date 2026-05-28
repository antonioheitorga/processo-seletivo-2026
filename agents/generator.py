"""Agente Gerador.

Responsabilidade única: gerar texto a partir do contexto explicitamente
recebido pelo Orquestrador.

Anti-alucinação por design: se o contexto (corpus + web) está vazio,
NÃO chama o LLM e retorna {"result": None, "reason": "..."}. O Orquestrador
decide o que fazer com essa resposta.

O cálculo de `fonte` e `low_confidence` é responsabilidade do Orquestrador,
não deste agente.
"""

import os
import time
from datetime import datetime, timezone

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama


PROMPT_TEMPLATE = """You are an expert assistant for FIA Formula 1 2026 regulations.

Original user query (preserve this language in your response):
{query_original}

Reformulated query (used for retrieval — for your reference only):
{query_reformulada}

Available context from corpus:
{corpus_context}

Available context from web:
{web_context}

Instructions:
- Answer using ONLY the provided context. Do NOT use prior knowledge.
- Respond in the SAME language as the original user query above.
- Prefer corpus context for regulatory details.
- Keep the answer concise and objective.

Final answer:"""


def _build_contexts(state: dict) -> tuple[str, str, str, str]:
    """Extrai query e contextos do estado, sem inferir nada."""
    query_original = (state.get("query_original") or "").strip()
    query_reformulada = (state.get("query_reformulada") or query_original).strip()
    if not query_reformulada:
        raise ValueError("State inválido: informe 'query_reformulada' ou 'query_original'.")
    if not query_original:
        query_original = query_reformulada

    retriever_result = state.get("retriever_result") or {}
    web_result = state.get("web_result") or {}

    hits = retriever_result.get("hits", [])
    corpus_context = "\n\n".join(
        [h.get("content", "") for h in hits if h.get("content")]
    ).strip()

    web_items = web_result.get("resultados", [])
    web_context = "\n\n".join(
        f"Título: {item.get('titulo', '')}\nTrecho: {item.get('trecho', '')}\nURL: {item.get('url', '')}"
        for item in web_items
    ).strip()

    return query_original, query_reformulada, corpus_context, web_context


def generate(state: dict) -> dict:
    """Gera resposta final usando apenas o contexto recebido.

    Lê: query_original, query_reformulada, retriever_result, web_result
    Escreve: generator_result, trace (append)
    """
    inicio = time.time()

    query_original, query_reformulada, corpus_context, web_context = _build_contexts(state)

    # Anti-alucinação por design: sem contexto, não chama o LLM
    if not corpus_context and not web_context:
        generator_result = {
            "result": None,
            "answer": "",
            "reason": "Nenhum contexto verificável recebido — geração abortada (anti-alucinação).",
        }
        saida_trace = generator_result
    else:
        llm = ChatOllama(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.getenv("LLM_MODEL", "llama3.1:8b"),
            temperature=0.0,
        )
        chain = ChatPromptTemplate.from_template(PROMPT_TEMPLATE) | llm
        resposta = chain.invoke(
            {
                "query_original": query_original,
                "query_reformulada": query_reformulada,
                "corpus_context": corpus_context or "N/A",
                "web_context": web_context or "N/A",
            }
        )
        answer = resposta.content.strip()

        generator_result = {
            "result": "ok",
            "answer": answer,
            "reason": None,
        }
        saida_trace = {
            "answer_preview": answer[:200] + ("..." if len(answer) > 200 else ""),
            "answer_length": len(answer),
        }

    return {
        "generator_result": generator_result,
        "trace": state.get("trace", [])
        + [
            {
                "agente": "generator",
                "entrada": {
                    "query_original": query_original,
                    "corpus_context_chars": len(corpus_context),
                    "web_context_chars": len(web_context),
                },
                "saida": saida_trace,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "latencia_ms": int((time.time() - inicio) * 1000),
            }
        ],
    }
