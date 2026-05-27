"""Orquestrador LangGraph.

Monta o grafo do sistema RAG multiagente:
reformulator -> retriever -> {web_searcher} -> generator

A transição entre retriever e web_searcher é condicional, baseada
no flag `fallback_to_web` do retriever_result. Lógica determinística,
sem LLM.
"""

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, StateGraph

from agents.generator import generate
from agents.reformulator import reformulate
from agents.retriever import retrieve
from agents.web_searcher import search_web
from agents.judge import judge


class GraphState(TypedDict, total=False):
    query_original: str
    session_id: str
    query_reformulada: str
    retriever_result: dict
    route_decision: str
    web_result: dict
    generator_result: dict
    judge_result: dict
    needs_revision: bool
    resposta: str
    fonte: str
    low_confidence: bool
    confidence_warning: str | None
    trace: list[dict]


def router(state: GraphState) -> GraphState:
    """Nó de decisão explícito do fluxo multiagente.

    Decide a próxima rota após o retriever, sem usar LLM.
    """
    retriever_result = state.get("retriever_result") or {}
    route_decision = "web_searcher" if retriever_result.get("fallback_to_web", False) else "generator"

    return {
        "route_decision": route_decision,
        "trace": state.get("trace", []) + [{
            "agente": "router",
            "entrada": {
                "best_score": retriever_result.get("best_score"),
                "fallback_to_web": retriever_result.get("fallback_to_web", False),
            },
            "saida": route_decision,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latencia_ms": 0,
        }],
    }


def _route_after_router(state: GraphState) -> str:
    """Roteia para o próximo nó usando decisão já registrada no estado."""
    return state.get("route_decision", "generator")


def build_graph():
    """Monta e compila o grafo do sistema."""
    graph = StateGraph(GraphState)

    graph.add_node("reformulator", reformulate)
    graph.add_node("retriever", retrieve)
    graph.add_node("router", router)
    graph.add_node("web_searcher", search_web)
    graph.add_node("generator", generate)
    graph.add_node("judge", judge)

    graph.set_entry_point("reformulator")
    graph.add_edge("reformulator", "retriever")
    graph.add_edge("retriever", "router")
    graph.add_conditional_edges(
        "router",
        _route_after_router,
        {"web_searcher": "web_searcher", "generator": "generator"},
    )
    graph.add_edge("web_searcher", "generator")
    graph.add_edge("generator", "judge")
    graph.add_edge("judge", END)

    return graph.compile()


def run(query_original: str, session_id: str | None = None) -> dict:
    """Executa o grafo completo para uma query.

    Gera session_id automaticamente se não for fornecido.
    Retorna o estado final com resposta, fonte, low_confidence e trace.
    """
    sid = session_id or uuid.uuid4().hex
    initial_state: GraphState = {
        "query_original": query_original,
        "session_id": sid,
        "trace": [],
    }
    state = build_graph().invoke(initial_state)
    _export_trace(state, sid)
    return state


def _export_trace(state: GraphState, session_id: str) -> None:
    """Persiste o trace da execução em traces/{session_id}.json."""
    traces_dir = Path(os.getenv("TRACES_DIR", "./traces"))
    traces_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query_original": state.get("query_original", ""),
        "resposta": state.get("resposta", ""),
        "fonte": state.get("fonte", ""),
        "low_confidence": state.get("low_confidence", False),
        "trace": state.get("trace", []),
    }

    trace_file = traces_dir / f"{session_id}.json"
    trace_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
