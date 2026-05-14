"""Orquestrador LangGraph.

Monta o grafo do sistema RAG multiagente:
reformulator -> retriever -> {web_searcher} -> generator

A transição entre retriever e web_searcher é condicional, baseada
no flag `fallback_to_web` do retriever_result. Lógica determinística,
sem LLM.
"""

import uuid
from typing import TypedDict

from langgraph.graph import END, StateGraph

from agents.generator import generate
from agents.reformulator import reformulate
from agents.retriever import retrieve
from agents.web_searcher import search_web


class GraphState(TypedDict, total=False):
    query_original: str
    session_id: str
    query_reformulada: str
    retriever_result: dict
    web_result: dict
    generator_result: dict
    resposta: str
    fonte: str
    low_confidence: bool
    confidence_warning: str | None
    trace: list[dict]


def _route_after_retriever(state: GraphState) -> str:
    """Decide o próximo nó após o retriever.

    Se o melhor score ficou abaixo do threshold (fallback_to_web=True),
    chama o web_searcher. Caso contrário, vai direto pro generator.
    """
    retriever_result = state.get("retriever_result") or {}
    return "web_searcher" if retriever_result.get("fallback_to_web", False) else "generator"


def build_graph():
    """Monta e compila o grafo do sistema."""
    graph = StateGraph(GraphState)

    graph.add_node("reformulator", reformulate)
    graph.add_node("retriever", retrieve)
    graph.add_node("web_searcher", search_web)
    graph.add_node("generator", generate)

    graph.set_entry_point("reformulator")
    graph.add_edge("reformulator", "retriever")
    graph.add_conditional_edges(
        "retriever",
        _route_after_retriever,
        {"web_searcher": "web_searcher", "generator": "generator"},
    )
    graph.add_edge("web_searcher", "generator")
    graph.add_edge("generator", END)

    return graph.compile()


def run(query_original: str, session_id: str | None = None) -> dict:
    """Executa o grafo completo para uma query.

    Gera session_id automaticamente se não for fornecido.
    Retorna o estado final com resposta, fonte, low_confidence e trace.
    """
    initial_state: GraphState = {
        "query_original": query_original,
        "session_id": session_id or uuid.uuid4().hex,
        "trace": [],
    }
    return build_graph().invoke(initial_state)
