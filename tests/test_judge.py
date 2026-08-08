"""Smoke tests do Judge/Verifier.

Validação determinística (sem LLM) que avalia se a resposta pode ser
aprovada com base em sinais de confiança do estado.

Critérios de aprovação:
- Tem `answer` (texto não vazio)
- Tem evidência (hits no corpus OU resultados na web)
- Não está marcado como low_confidence
"""

from agents.judge import judge


def test_judge_aprova_com_corpus_e_answer():
    """Caso feliz: resposta + hits no corpus → approved."""
    state = {
        "generator_result": {"answer": "DRS é o Drag Reduction System...", "result": "ok"},
        "retriever_result": {"hits": [{"content": "DRS context", "score": 0.85}]},
    }

    result = judge(state)
    jr = result["judge_result"]

    assert jr["approved"] is True
    assert jr["decision"] == "approve"
    assert jr["reasons"] == []
    assert result["needs_revision"] is False


def test_judge_aprova_com_web_e_answer():
    """Aprova quando evidência veio apenas da web."""
    state = {
        "generator_result": {"answer": "Resposta da web", "result": "ok"},
        "retriever_result": {"hits": []},
        "web_result": {
            "resultados": [{"titulo": "T", "trecho": "C", "url": "https://x.com"}],
        },
    }

    result = judge(state)

    assert result["judge_result"]["approved"] is True
    assert result["needs_revision"] is False


def test_judge_rejeita_sem_answer():
    """Sem texto na resposta → revise com motivo empty_answer."""
    state = {
        "generator_result": {"answer": "", "result": None},
        "retriever_result": {"hits": [{"content": "x", "score": 0.9}]},
    }

    result = judge(state)
    jr = result["judge_result"]

    assert jr["approved"] is False
    assert jr["decision"] == "revise"
    assert "empty_answer" in jr["reasons"]
    assert result["needs_revision"] is True


def test_judge_rejeita_sem_evidencia():
    """Sem hits no corpus nem na web → revise com motivo no_evidence."""
    state = {
        "generator_result": {"answer": "Resposta sem fonte", "result": "ok"},
        "retriever_result": {"hits": []},
        "web_result": {"resultados": []},
    }

    result = judge(state)
    jr = result["judge_result"]

    assert jr["approved"] is False
    assert "no_evidence" in jr["reasons"]
    assert result["needs_revision"] is True


def test_judge_rejeita_low_confidence():
    """low_confidence=True no state (escrito pelo Orquestrador) → revise."""
    state = {
        "low_confidence": True,
        "generator_result": {
            "answer": "Resposta marcada como baixa confiança",
            "result": "ok",
        },
        "retriever_result": {"hits": [{"content": "x", "score": 0.5}]},
    }

    result = judge(state)
    jr = result["judge_result"]

    assert jr["approved"] is False
    assert "low_confidence" in jr["reasons"]


def test_judge_acumula_multiplos_motivos():
    """Quando várias condições falham, todos os motivos são listados."""
    state = {
        "low_confidence": True,
        "generator_result": {"answer": ""},
        "retriever_result": {"hits": []},
        "web_result": {"resultados": []},
    }

    result = judge(state)
    reasons = result["judge_result"]["reasons"]

    assert set(reasons) == {"empty_answer", "no_evidence", "low_confidence"}


def test_judge_appenda_trace_completo():
    """Trace deve preservar entrada anterior e adicionar a do judge."""
    state = {
        "generator_result": {"answer": "ok", "result": "ok"},
        "retriever_result": {"hits": [{"content": "x", "score": 0.9}]},
        "trace": [{"agente": "generator"}],
    }

    result = judge(state)
    trace = result["trace"]

    assert len(trace) == 2
    assert trace[0]["agente"] == "generator"
    assert trace[1]["agente"] == "judge"
    assert trace[1]["latencia_ms"] >= 0
    assert trace[1]["saida"]["approved"] is True
    assert trace[1]["entrada"]["retriever_hits"] == 1


def test_judge_state_vazio_rejeita():
    """State sem nenhum dos campos esperados → revise com todos os motivos."""
    result = judge({})
    jr = result["judge_result"]

    assert jr["approved"] is False
    assert jr["decision"] == "revise"
    assert set(jr["reasons"]) == {"empty_answer", "no_evidence"}
    assert result["needs_revision"] is True
