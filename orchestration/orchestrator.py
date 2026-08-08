"""Orquestrador LangGraph — arquitetura multiagente hub-and-spoke.

O Orquestrador é um nó real no grafo. Todo agente, ao terminar, retorna
ao Orquestrador, que inspeciona o estado e decide qual agente chamar
a seguir. Nenhum agente sabe que o próximo existe.

Responsabilidades do Orquestrador:
- Decidir o próximo passo baseado no estado atual
- Calcular `fonte` e `low_confidence` (responsabilidade de coordenação)
- Aplicar anti-alucinação por design: aborta geração se não há contexto verificável
- Montar a resposta final para o usuário
"""

import json
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, StateGraph

from agents.generator import generate
from agents.judge import judge
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
    judge_result: dict
    needs_revision: bool
    next_step: str
    resposta: str
    fonte: str
    low_confidence: bool
    confidence_warning: str | None
    trace: list[dict]


# ---------------------------------------------------------------------------
# Nó central — Orquestrador
# ---------------------------------------------------------------------------


def orchestrate(state: GraphState) -> dict:
    """Nó central de coordenação.

    Roda múltiplas vezes durante a execução. A cada chamada, inspeciona
    o estado para descobrir o que já foi feito e decide o próximo passo.
    """
    inicio = time.time()

    next_step, updates, reason = _decide_next(state)

    updates["next_step"] = next_step
    updates["trace"] = state.get("trace", []) + [
        {
            "agente": "orchestrator",
            "entrada": _state_snapshot(state),
            "saida": {"next_step": next_step, "reason": reason},
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latencia_ms": int((time.time() - inicio) * 1000),
        }
    ]

    return updates


def _decide_next(state: GraphState) -> tuple[str, dict, str]:
    """Lógica de decisão do Orquestrador. Retorna (próximo_passo, updates, razão)."""

    if not state.get("query_reformulada"):
        return "reformulator", {}, "query ainda não reformulada — delegando ao Reformulador"

    if not state.get("retriever_result"):
        return "retriever", {}, "busca vetorial pendente — delegando ao Retriever"

    retriever_result = state["retriever_result"]
    if retriever_result.get("fallback_to_web") and not state.get("web_result"):
        best_score = retriever_result.get("best_score")
        return (
            "web_searcher",
            {},
            f"best_score={best_score} abaixo do threshold — delegando ao Web Searcher",
        )

    # Contexto coletado: decide se gera resposta ou aborta por anti-alucinação
    fonte, low_confidence = _compute_fonte_e_confianca(state)

    if fonte == "none" and not state.get("generator_result"):
        # Anti-alucinação por design: sem fonte verificável, não chama LLM
        return (
            "done",
            {
                "fonte": "none",
                "low_confidence": True,
                "resposta": (
                    "Não foi possível encontrar informações verificáveis para responder. "
                    "Tente reformular ou perguntar sobre outro tópico do Regulamento FIA F1 2026."
                ),
                "confidence_warning": "Nenhuma fonte verificável (corpus + web vazios).",
            },
            "sem contexto verificável — abortando geração (anti-alucinação)",
        )

    if not state.get("generator_result"):
        return (
            "generator",
            {"fonte": fonte, "low_confidence": low_confidence},
            f"contexto pronto (fonte={fonte}, low_confidence={low_confidence}) — delegando ao Gerador",
        )

    if not state.get("judge_result"):
        return "judge", {}, "resposta gerada — delegando ao Judge"

    # Tudo pronto: monta resposta final para o usuário
    generator_result = state["generator_result"]
    judge_result = state["judge_result"]
    answer = generator_result.get("answer", "")
    decision = judge_result.get("decision", "approve")

    updates: dict = {"resposta": answer}
    if state.get("low_confidence"):
        updates["confidence_warning"] = (
            "Resposta baseada em contexto de baixa confiança — verifique a fonte."
        )

    return "done", updates, f"judge={decision} — finalizando resposta para o usuário"


def _state_snapshot(state: GraphState) -> dict:
    """Snapshot booleano do que já foi produzido — usado no trace."""
    return {
        "query_reformulada": bool(state.get("query_reformulada")),
        "retriever_result": bool(state.get("retriever_result")),
        "web_result": bool(state.get("web_result")),
        "generator_result": bool(state.get("generator_result")),
        "judge_result": bool(state.get("judge_result")),
    }


def _compute_fonte_e_confianca(state: GraphState) -> tuple[str, bool]:
    """Determina a fonte do contexto disponível e se há confiança suficiente."""
    retriever_result = state.get("retriever_result") or {}
    web_result = state.get("web_result") or {}

    has_corpus = bool(retriever_result.get("hits"))
    has_web = bool(web_result.get("resultados"))

    if has_corpus and has_web:
        return "hybrid", False
    if has_corpus:
        return "corpus", False
    if has_web:
        return "web", False
    return "none", True


def _route_from_orchestrator(state: GraphState) -> str:
    """Edge condicional: lê `next_step` do estado e devolve o nome do próximo nó."""
    step = state.get("next_step", "reformulator")
    return END if step == "done" else step


# ---------------------------------------------------------------------------
# Grafo
# ---------------------------------------------------------------------------


def build_graph():
    """Monta e compila o grafo hub-and-spoke.

    Todos os agentes retornam ao Orquestrador. O Orquestrador decide,
    via edge condicional, qual agente chamar a seguir.
    """
    graph = StateGraph(GraphState)

    graph.add_node("orchestrator", orchestrate)
    graph.add_node("reformulator", reformulate)
    graph.add_node("retriever", retrieve)
    graph.add_node("web_searcher", search_web)
    graph.add_node("generator", generate)
    graph.add_node("judge", judge)

    graph.set_entry_point("orchestrator")

    # Todos os agentes retornam ao Orquestrador
    graph.add_edge("reformulator", "orchestrator")
    graph.add_edge("retriever", "orchestrator")
    graph.add_edge("web_searcher", "orchestrator")
    graph.add_edge("generator", "orchestrator")
    graph.add_edge("judge", "orchestrator")

    # Orquestrador roteia condicionalmente
    graph.add_conditional_edges(
        "orchestrator",
        _route_from_orchestrator,
        {
            "reformulator": "reformulator",
            "retriever": "retriever",
            "web_searcher": "web_searcher",
            "generator": "generator",
            "judge": "judge",
            END: END,
        },
    )

    return graph.compile()


def run(query_original: str, session_id: str | None = None) -> dict:
    """Executa o grafo completo para uma query.

    Gera session_id automaticamente se não for fornecido.
    Retorna o estado final montado pelo Orquestrador.
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
