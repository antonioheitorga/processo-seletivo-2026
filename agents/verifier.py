"""Agente Verificador.

Confere se a resposta do Gerador está fundamentada no contexto
recuperado (corpus e/ou web). Fecha o loop de reflexão: quando a
resposta não está fundamentada, sinaliza para o orquestrador tentar
de novo (reformular + buscar) até um número máximo de tentativas.
"""

import os
import time
from datetime import datetime, timezone

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama


PROMPT_TEMPLATE = """You are a strict fact-checking agent. Decide whether the ANSWER below is fully \
supported by the CONTEXT — do not use outside knowledge, only what is written in the context.

Question: {query_original}

Context:
{context}

Answer:
{answer}

Instructions:
- GROUNDED: every claim in the answer is supported by the context, AND the answer actually addresses the question
  with real information (not a refusal or hedge).
- NOT_GROUNDED (this includes hedges/non-answers — read this carefully, it is the most commonly missed case):
  - the answer has claims absent from the context, or contradicts it; OR
  - the answer says something like "the context doesn't mention/provide/specify this", "not available in the
    provided context", "cannot be determined", "may be uncertain" — ANY variant of "I don't know from this context"
    counts as NOT_GROUNDED, even though that statement is itself truthful. A true "I don't know" still means the
    question was not answered, and the verdict must be NOT_GROUNDED so the system tries a broader search.

Example: Question "Who won the 2025 race?", Answer "The context does not provide information about the 2025 race
results." -> VERDICT: NOT_GROUNDED (it's an honest hedge, but still not an answer to the question).

Respond strictly in this format:
VERDICT: GROUNDED or NOT_GROUNDED
JUSTIFICATION: <one short sentence>"""


def _parse_verdict(raw: str) -> tuple[bool, str]:
    """Extrai (grounded, justification) da resposta do LLM. Falha aberta: em caso de
    formato inesperado, assume NOT_GROUNDED para não passar informação sem checagem."""
    grounded = False
    justification = raw.strip()

    for line in raw.splitlines():
        line = line.strip()
        if line.upper().startswith("VERDICT:"):
            verdict = line.split(":", 1)[1].strip().upper()
            grounded = verdict.startswith("GROUNDED")
        elif line.upper().startswith("JUSTIFICATION:"):
            justification = line.split(":", 1)[1].strip()

    return grounded, justification


def verify(state: dict) -> dict:
    """Verifica se a resposta gerada está fundamentada no contexto recuperado.

    Lê: query_original, generator_result/resposta, retriever_result, web_result, retry_count
    Escreve: verifier_result, retry_count, trace (append) e, quando esgota as tentativas
    sem fundamentação, low_confidence/confidence_warning.
    """
    inicio = time.time()

    query_original = (state.get("query_original") or "").strip()
    generator_result = state.get("generator_result") or {}
    answer = (generator_result.get("answer") or state.get("resposta") or "").strip()

    retriever_result = state.get("retriever_result") or {}
    hits = retriever_result.get("hits", [])
    corpus_context = "\n\n".join(h.get("content", "") for h in hits if h.get("content")).strip()

    web_result = state.get("web_result") or {}
    web_items = web_result.get("resultados", [])
    web_context = "\n\n".join(
        f"{item.get('titulo', '')}: {item.get('trecho', '')}" for item in web_items
    ).strip()

    context = "\n\n".join(part for part in (corpus_context, web_context) if part).strip()

    max_retries = int(os.getenv("VERIFIER_MAX_RETRIES", "1"))
    retry_count = state.get("retry_count", 0)

    if not context or not answer:
        grounded = False
        justification = "Sem contexto recuperado (ou sem resposta) para fundamentar a verificação."
    else:
        llm = ChatOllama(
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
            model=os.getenv("LLM_MODEL", "llama3.1:8b"),
            temperature=0.0,
        )
        chain = ChatPromptTemplate.from_template(PROMPT_TEMPLATE) | llm
        resposta = chain.invoke(
            {"query_original": query_original, "context": context, "answer": answer}
        )
        grounded, justification = _parse_verdict(resposta.content)

    will_retry = (not grounded) and (retry_count < max_retries)
    new_retry_count = retry_count + 1 if not grounded else retry_count

    verifier_result = {
        "grounded": grounded,
        "justification": justification,
        "attempt": retry_count + 1,
        "will_retry": will_retry,
    }

    output = {
        "verifier_result": verifier_result,
        "retry_count": new_retry_count,
        "trace": state.get("trace", []) + [{
            "agente": "verifier",
            "entrada": {"query_original": query_original, "answer": answer},
            "saida": f"grounded={grounded}; will_retry={will_retry}; {justification}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latencia_ms": int((time.time() - inicio) * 1000),
        }],
    }

    if not grounded and not will_retry:
        output["low_confidence"] = True
        output["confidence_warning"] = (
            f"Verificador não conseguiu confirmar que a resposta está fundamentada no "
            f"contexto recuperado após {retry_count + 1} tentativa(s). {justification}"
        )

    return output
