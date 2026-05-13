"""Agente Web Searcher.

Busca externa via Tavily quando o corpus FIA não tem a resposta.
Chamado pelo orquestrador quando o Retriever retorna fallback=True.
"""

import os
import time
from datetime import datetime, timezone

from tavily import TavilyClient


DEFAULT_MAX_RESULTS = 5


def search_web(state: dict) -> dict:
    """Busca a query reformulada na web via Tavily.

    Lê: state["query_reformulada"] (fallback para state["query_original"])
    Escreve: web_result, trace (append)
    """
    inicio = time.time()
    query = (state.get("query_reformulada") or state.get("query_original") or "").strip()
    if not query:
        raise ValueError("State inválido: informe 'query_reformulada' ou 'query_original'.")

    api_key = os.getenv("TAVILY_API_KEY")
    max_results = int(os.getenv("TAVILY_MAX_RESULTS", str(DEFAULT_MAX_RESULTS)))

    erro = None
    resultados = []

    if not api_key:
        erro = "TAVILY_API_KEY não configurada"
    else:
        try:
            client = TavilyClient(api_key=api_key)
            response = client.search(query=query, max_results=max_results)
            resultados = [
                {
                    "titulo": r.get("title", ""),
                    "trecho": r.get("content", ""),
                    "url": r.get("url", ""),
                }
                for r in response.get("results", [])
            ]
        except Exception as exc:
            erro = f"{type(exc).__name__}: {exc}"

    web_result = {
        "resultados": resultados,
        "encontrou": len(resultados) > 0,
    }

    saida_trace = (
        f"{len(resultados)} resultados" if erro is None
        else f"erro: {erro}"
    )

    return {
        "web_result": web_result,
        "trace": state.get("trace", []) + [{
            "agente": "web_searcher",
            "entrada": query,
            "saida": saida_trace,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latencia_ms": int((time.time() - inicio) * 1000),
        }],
    }
