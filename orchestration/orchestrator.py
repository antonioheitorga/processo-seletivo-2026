"""Orquestrador LangGraph.

Monta o grafo do sistema RAG multiagente:
reformulator -> retriever -> {web_searcher} -> generator -> verifier -> {reformulator | fim}

A transição entre retriever e web_searcher é condicional, baseada no flag
`fallback_to_web` do retriever_result. A transição após o verifier fecha o
loop de reflexão: se a resposta não estiver fundamentada no contexto
recuperado, o grafo volta para o reformulator (com o feedback do verifier)
até `VERIFIER_MAX_RETRIES` tentativas; senão, encerra. Ambas as transições
são lógica determinística sobre o resultado do agente anterior, não LLM.
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
from agents.verifier import verify
from agents.web_searcher import search_web


class GraphState(TypedDict, total=False):
    query_original: str
    session_id: str
    query_reformulada: str
    retriever_result: dict
    web_result: dict
    generator_result: dict
    verifier_result: dict
    retry_count: int
    resposta: str
    fonte: str
    low_confidence: bool
    confidence_warning: str | None
    trace: list[dict]


def _route_after_retriever(state: GraphState) -> str:
    """Decide o próximo nó após o retriever.

    Se o melhor score ficou abaixo do threshold (fallback_to_web=True),
    chama o web_searcher. Caso contrário, vai direto pro generator — a
    menos que esta seja uma retentativa do loop de reflexão
    (retry_count > 0, ou seja, o Verificador já reprovou uma resposta
    baseada só no corpus): nesse caso sempre busca na web também, mesmo
    com score acima do threshold. Motivo (achado empírico rodando o
    benchmark): o Reformulador reescreve a query em vocabulário
    regulatório formal para otimizar a busca no corpus, e isso pode
    empurrar o score de similaridade acima do threshold contra chunks
    genéricos que não respondem a pergunta (falso positivo) — se a
    primeira tentativa (só corpus) já foi reprovada pelo Verificador,
    vale a pena trazer contexto web mesmo que o Retriever "ache" que
    achou algo relevante.
    """
    retriever_result = state.get("retriever_result") or {}
    if retriever_result.get("fallback_to_web", False):
        return "web_searcher"
    if state.get("retry_count", 0) > 0:
        return "web_searcher"
    return "generator"


def _route_after_verifier(state: GraphState) -> str:
    """Decide o próximo nó após o verifier.

    Se a resposta não está fundamentada e ainda há tentativas disponíveis
    (`verifier_result.will_retry`), fecha o loop de reflexão voltando ao
    reformulator. Caso contrário, encerra o grafo.
    """
    verifier_result = state.get("verifier_result") or {}
    return "reformulator" if verifier_result.get("will_retry", False) else "end"


def build_graph():
    """Monta e compila o grafo do sistema."""
    graph = StateGraph(GraphState)

    graph.add_node("reformulator", reformulate)
    graph.add_node("retriever", retrieve)
    graph.add_node("web_searcher", search_web)
    graph.add_node("generator", generate)
    graph.add_node("verifier", verify)

    graph.set_entry_point("reformulator")
    graph.add_edge("reformulator", "retriever")
    graph.add_conditional_edges(
        "retriever",
        _route_after_retriever,
        {"web_searcher": "web_searcher", "generator": "generator"},
    )
    graph.add_edge("web_searcher", "generator")
    graph.add_edge("generator", "verifier")
    graph.add_conditional_edges(
        "verifier",
        _route_after_verifier,
        {"reformulator": "reformulator", "end": END},
    )

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
        "retry_count": 0,
    }
    state = build_graph().invoke(initial_state)
    _export_trace(state, sid)
    return state


def _export_trace(state: GraphState, session_id: str) -> None:
    """Persiste o trace da execução em traces/{session_id}.json.

    Além do trace narrativo por agente, inclui explicitamente o que foi
    recuperado (trechos + fontes de corpus e web) e se/por que o fallback
    foi acionado — exigido pelo requisito de observabilidade do desafio.
    """
    traces_dir = Path(os.getenv("TRACES_DIR", "./traces"))
    traces_dir.mkdir(parents=True, exist_ok=True)

    retriever_result = state.get("retriever_result") or {}
    web_result = state.get("web_result") or {}
    verifier_result = state.get("verifier_result") or {}
    trace_steps = state.get("trace", [])

    # web_searcher pode ter rodado por score baixo do retriever OU por
    # retentativa do loop de reflexão (ver _route_after_retriever) — o sinal
    # confiável de "o fallback foi acionado" é o agente ter rodado de fato,
    # não só o flag da 1ª passagem do retriever.
    web_searcher_rodou = any(step.get("agente") == "web_searcher" for step in trace_steps)
    fallback_acionado = bool(retriever_result.get("fallback_to_web", False)) or web_searcher_rodou
    if retriever_result.get("fallback_to_web", False):
        fallback_motivo = retriever_result.get("confidence_warning")
    elif web_searcher_rodou:
        fallback_motivo = (
            "Score do corpus passou do threshold, mas a 1ª resposta foi reprovada pelo "
            "Verificador (não fundamentada) — retentativa acionou busca web também."
        )
    else:
        fallback_motivo = "Corpus retornou hit(s) acima do threshold; fallback não foi necessário."

    payload = {
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "query_original": state.get("query_original", ""),
        "query_reformulada": state.get("query_reformulada", ""),
        "resposta": state.get("resposta", ""),
        "fonte": state.get("fonte", ""),
        "low_confidence": state.get("low_confidence", False),
        "confidence_warning": state.get("confidence_warning"),
        "fallback": {
            "acionado": fallback_acionado,
            "motivo": fallback_motivo,
            "threshold": retriever_result.get("threshold"),
            "best_score": retriever_result.get("best_score"),
        },
        "recuperado": {
            "corpus": [
                {
                    "trecho": hit.get("content", ""),
                    "score": hit.get("score"),
                    "fonte": hit.get("metadata", {}),
                }
                for hit in retriever_result.get("hits", [])
            ],
            "web": [
                {
                    "trecho": item.get("trecho", ""),
                    "titulo": item.get("titulo", ""),
                    "fonte": item.get("url", ""),
                }
                for item in web_result.get("resultados", [])
            ],
        },
        "verificacao": {
            "grounded": verifier_result.get("grounded"),
            "justificativa": verifier_result.get("justification"),
            "tentativas": verifier_result.get("attempt"),
        },
        "trace": state.get("trace", []),
    }

    trace_file = traces_dir / f"{session_id}.json"
    trace_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
