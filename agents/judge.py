"""Agente Judge/Verifier.

Valida a resposta gerada com base nos sinais de confiança do estado.
Não usa LLM: decisão determinística para manter previsibilidade.

Contrato:
- Lê: generator_result, retriever_result, web_result
- Escreve: judge_result, needs_revision, trace (append)
"""

import time
from datetime import datetime, timezone


def judge(state: dict) -> dict:
    """Avalia se a resposta pode ser aprovada para saída final."""
    inicio = time.time()

    generator_result = state.get("generator_result") or {}
    retriever_result = state.get("retriever_result") or {}
    web_result = state.get("web_result") or {}

    sources_used = state.get("fonte", "none")
    low_confidence = bool(state.get("low_confidence", False))
    answer = (generator_result.get("answer") or "").strip()

    retriever_hits = retriever_result.get("hits") or []
    web_hits = web_result.get("resultados") or []

    has_any_evidence = bool(retriever_hits or web_hits)
    has_answer = bool(answer)

    approved = has_answer and has_any_evidence and not low_confidence
    decision = "approve" if approved else "revise"

    reasons = []
    if not has_answer:
        reasons.append("empty_answer")
    if not has_any_evidence:
        reasons.append("no_evidence")
    if low_confidence:
        reasons.append("low_confidence")

    judge_result = {
        "approved": approved,
        "decision": decision,
        "sources_used": sources_used,
        "reasons": reasons,
    }

    return {
        "judge_result": judge_result,
        "needs_revision": not approved,
        "trace": state.get("trace", [])
        + [
            {
                "agente": "judge",
                "entrada": {
                    "sources_used": sources_used,
                    "retriever_hits": len(retriever_hits),
                    "web_hits": len(web_hits),
                    "low_confidence": low_confidence,
                },
                "saida": judge_result,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "latencia_ms": int((time.time() - inicio) * 1000),
            }
        ],
    }
