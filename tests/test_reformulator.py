"""Smoke tests do Agente Reformulador."""

from unittest.mock import patch

import pytest

from agents.reformulator import reformulate


@patch("agents.reformulator.ChatOllama")
@patch("agents.reformulator.ChatPromptTemplate")
def test_reformulate_estrutura_saida(mock_prompt_cls, _mock_llm_cls):
    """Sem rede: verifica formato de retorno e trace."""
    chain = mock_prompt_cls.from_template.return_value.__or__.return_value
    chain.invoke.return_value.content = "What are the DRS rules in F1 2026?"

    result = reformulate({"query_original": "qual o limite de DRS?"})

    assert result["query_reformulada"] == "What are the DRS rules in F1 2026?"
    assert len(result["trace"]) == 1
    entry = result["trace"][0]
    assert entry["agente"] == "reformulator"
    assert entry["entrada"] == "qual o limite de DRS?"
    assert entry["saida"] == "What are the DRS rules in F1 2026?"
    assert isinstance(entry["latencia_ms"], int)
    assert entry["latencia_ms"] >= 0


@patch("agents.reformulator.ChatOllama")
@patch("agents.reformulator.ChatPromptTemplate")
def test_reformulate_strip_aplica(mock_prompt_cls, _mock_llm_cls):
    """Garante que espaços, quebras de linha e aspas são removidos da resposta."""
    chain = mock_prompt_cls.from_template.return_value.__or__.return_value
    chain.invoke.return_value.content = '\n  "reformulated query"  \n\n'

    result = reformulate({"query_original": "teste"})

    assert result["query_reformulada"] == "reformulated query"


@patch("agents.reformulator.ChatOllama")
@patch("agents.reformulator.ChatPromptTemplate")
def test_reformulate_appenda_trace_existente(mock_prompt_cls, _mock_llm_cls):
    """Verifica que trace existente é preservado (append, não substituição)."""
    chain = mock_prompt_cls.from_template.return_value.__or__.return_value
    chain.invoke.return_value.content = "reformulated"

    trace_anterior = [{"agente": "outro", "entrada": "x", "saida": "y",
                       "timestamp": "2026-01-01T00:00:00Z", "latencia_ms": 10}]

    result = reformulate({
        "query_original": "teste",
        "trace": trace_anterior,
    })

    assert len(result["trace"]) == 2
    assert result["trace"][0]["agente"] == "outro"
    assert result["trace"][1]["agente"] == "reformulator"


@pytest.mark.integration
def test_reformulate_integracao_ollama():
    """Requer Ollama rodando com llama3.1:8b. Rode com: pytest -m integration"""
    result = reformulate({"query_original": "qual o limite de DRS?"})

    assert isinstance(result["query_reformulada"], str)
    assert len(result["query_reformulada"]) > 10
    assert result["trace"][0]["latencia_ms"] > 0
