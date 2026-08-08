"""Smoke tests do Agente Verificador."""

import os
from unittest.mock import patch

from agents.verifier import verify


@patch("agents.verifier.ChatOllama")
@patch("agents.verifier.ChatPromptTemplate")
def test_verify_grounded(mock_prompt_cls, _mock_llm_cls):
    chain = mock_prompt_cls.from_template.return_value.__or__.return_value
    chain.invoke.return_value.content = "VERDICT: GROUNDED\nJUSTIFICATION: Answer matches the context."

    state = {
        "query_original": "O que é DRS?",
        "generator_result": {"answer": "DRS é o sistema de redução de arrasto."},
        "retriever_result": {"hits": [{"content": "DRS can only be used in designated zones.", "score": 0.9}]},
        "retry_count": 0,
    }

    result = verify(state)
    vr = result["verifier_result"]

    assert vr["grounded"] is True
    assert vr["will_retry"] is False
    assert result["retry_count"] == 0
    assert "low_confidence" not in result
    assert result["trace"][-1]["agente"] == "verifier"


@patch("agents.verifier.ChatOllama")
@patch("agents.verifier.ChatPromptTemplate")
def test_verify_not_grounded_com_retry_disponivel(mock_prompt_cls, _mock_llm_cls):
    chain = mock_prompt_cls.from_template.return_value.__or__.return_value
    chain.invoke.return_value.content = "VERDICT: NOT_GROUNDED\nJUSTIFICATION: Answer invents a rule not in context."

    state = {
        "query_original": "Qual o peso mínimo do carro?",
        "generator_result": {"answer": "O peso mínimo é 900kg."},
        "retriever_result": {"hits": [{"content": "Some unrelated regulation text.", "score": 0.76}]},
        "retry_count": 0,
    }

    with patch.dict(os.environ, {"VERIFIER_MAX_RETRIES": "1"}):
        result = verify(state)
    vr = result["verifier_result"]

    assert vr["grounded"] is False
    assert vr["will_retry"] is True
    assert result["retry_count"] == 1
    assert "low_confidence" not in result


@patch("agents.verifier.ChatOllama")
@patch("agents.verifier.ChatPromptTemplate")
def test_verify_not_grounded_esgota_tentativas(mock_prompt_cls, _mock_llm_cls):
    chain = mock_prompt_cls.from_template.return_value.__or__.return_value
    chain.invoke.return_value.content = "VERDICT: NOT_GROUNDED\nJUSTIFICATION: Still unsupported."

    state = {
        "query_original": "pergunta difícil",
        "generator_result": {"answer": "resposta arriscada"},
        "retriever_result": {"hits": [{"content": "contexto parcial", "score": 0.7}]},
        "retry_count": 1,
    }

    with patch.dict(os.environ, {"VERIFIER_MAX_RETRIES": "1"}):
        result = verify(state)
    vr = result["verifier_result"]

    assert vr["grounded"] is False
    assert vr["will_retry"] is False
    assert result["retry_count"] == 2
    assert result["low_confidence"] is True
    assert "esgotou" not in result["confidence_warning"]  # mensagem real, não placeholder
    assert "fundamentada" in result["confidence_warning"]


def test_verify_sem_contexto_reprova_sem_chamar_llm():
    state = {
        "query_original": "pergunta qualquer",
        "generator_result": {"answer": "não sei"},
        "retriever_result": {"hits": []},
        "web_result": {"resultados": []},
        "retry_count": 0,
    }

    result = verify(state)
    vr = result["verifier_result"]

    assert vr["grounded"] is False
    assert "Sem contexto" in vr["justification"]
