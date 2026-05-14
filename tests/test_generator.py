"""Smoke tests do Agente Gerador."""

from unittest.mock import patch

import pytest

from agents.generator import generate


@patch("agents.generator.ChatOllama")
@patch("agents.generator.ChatPromptTemplate")
def test_generate_corpus_only(mock_prompt_cls, _mock_llm_cls):
    chain = mock_prompt_cls.from_template.return_value.__or__.return_value
    chain.invoke.return_value.content = "Resposta baseada no corpus."

    state = {
        "query_reformulada": "What are DRS rules?",
        "retriever_result": {
            "fallback_to_web": False,
            "confidence_warning": None,
            "hits": [
                {"content": "DRS can only be used in designated zones.", "score": 0.91, "metadata": {"section": "B"}}
            ],
        },
    }

    result = generate(state)

    assert "generator_result" in result
    gr = result["generator_result"]
    assert gr["answer"] == "Resposta baseada no corpus."
    assert gr["sources_used"] == "corpus"
    assert gr["low_confidence"] is False
    assert gr["confidence_notice"] is None
    assert result["trace"][-1]["agente"] == "generator"


@patch("agents.generator.ChatOllama")
@patch("agents.generator.ChatPromptTemplate")
def test_generate_web_fallback_low_confidence(mock_prompt_cls, _mock_llm_cls):
    chain = mock_prompt_cls.from_template.return_value.__or__.return_value
    chain.invoke.return_value.content = "Resposta com base na web."

    state = {
        "query_original": "regra obscura de PU",
        "retriever_result": {
            "fallback_to_web": True,
            "confidence_warning": "Score abaixo do mínimo configurado.",
            "hits": [],
        },
        "web_result": {
            "resultados": [
                {"titulo": "FIA note", "trecho": "Temporary guidance...", "url": "https://example.com/fia"}
            ],
            "encontrou": True,
        },
    }

    result = generate(state)
    gr = result["generator_result"]

    assert gr["sources_used"] == "web"
    assert gr["low_confidence"] is True
    assert "Score abaixo" in gr["confidence_notice"]


@patch("agents.generator.ChatOllama")
@patch("agents.generator.ChatPromptTemplate")
def test_generate_hybrid(mock_prompt_cls, _mock_llm_cls):
    chain = mock_prompt_cls.from_template.return_value.__or__.return_value
    chain.invoke.return_value.content = "Resposta híbrida."

    state = {
        "query_reformulada": "engine cooling constraints",
        "retriever_result": {
            "fallback_to_web": False,
            "confidence_warning": None,
            "hits": [{"content": "Cooling rules from corpus.", "score": 0.84, "metadata": {}}],
        },
        "web_result": {
            "resultados": [{"titulo": "News", "trecho": "Recent clarification", "url": "https://example.com/news"}],
            "encontrou": True,
        },
    }

    result = generate(state)
    assert result["generator_result"]["sources_used"] == "hybrid"


def test_generate_state_invalido():
    with pytest.raises(ValueError, match="State inválido"):
        generate({})
