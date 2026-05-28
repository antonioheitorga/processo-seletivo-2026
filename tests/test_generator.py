"""Smoke tests do Agente Gerador.

O Gerador tem responsabilidade única: gerar texto a partir do contexto
recebido. Não calcula `fonte` nem `low_confidence` — isso é do Orquestrador.

Anti-alucinação por design: se não há contexto, retorna `result=None`
sem chamar o LLM.
"""

from unittest.mock import patch

import pytest

from agents.generator import generate


@patch("agents.generator.ChatOllama")
@patch("agents.generator.ChatPromptTemplate")
def test_generate_com_corpus(mock_prompt_cls, _mock_llm_cls):
    """Com contexto do corpus: chama o LLM e devolve answer."""
    chain = mock_prompt_cls.from_template.return_value.__or__.return_value
    chain.invoke.return_value.content = "Resposta baseada no corpus."

    state = {
        "query_reformulada": "What are DRS rules?",
        "retriever_result": {
            "hits": [
                {"content": "DRS can only be used in designated zones.", "score": 0.91, "metadata": {"section": "B"}}
            ],
        },
    }

    result = generate(state)
    gr = result["generator_result"]

    assert gr["result"] == "ok"
    assert gr["answer"] == "Resposta baseada no corpus."
    assert gr["reason"] is None
    assert result["trace"][-1]["agente"] == "generator"


@patch("agents.generator.ChatOllama")
@patch("agents.generator.ChatPromptTemplate")
def test_generate_com_web(mock_prompt_cls, _mock_llm_cls):
    """Com contexto da web: chama o LLM normalmente."""
    chain = mock_prompt_cls.from_template.return_value.__or__.return_value
    chain.invoke.return_value.content = "Resposta com base na web."

    state = {
        "query_original": "regra obscura de PU",
        "retriever_result": {"hits": []},
        "web_result": {
            "resultados": [
                {"titulo": "FIA note", "trecho": "Temporary guidance...", "url": "https://example.com/fia"}
            ],
            "encontrou": True,
        },
    }

    result = generate(state)
    gr = result["generator_result"]

    assert gr["result"] == "ok"
    assert gr["answer"] == "Resposta com base na web."


@patch("agents.generator.ChatOllama")
def test_generate_sem_contexto_aborta_llm(mock_llm_cls):
    """Anti-alucinação: corpus e web vazios → NÃO chama o LLM, retorna result=None."""
    state = {
        "query_original": "regra inexistente",
        "retriever_result": {"hits": []},
        "web_result": {"resultados": [], "encontrou": False},
    }

    result = generate(state)
    gr = result["generator_result"]

    assert gr["result"] is None
    assert gr["answer"] == ""
    assert "anti-alucinação" in gr["reason"].lower() or "anti-alucinacao" in gr["reason"].lower()
    # LLM nunca foi instanciado
    mock_llm_cls.assert_not_called()


def test_generate_state_invalido():
    with pytest.raises(ValueError, match="State inválido"):
        generate({})


@patch("agents.generator.ChatOllama")
@patch("agents.generator.ChatPromptTemplate")
def test_generate_preserva_query_original_no_prompt(mock_prompt_cls, _mock_llm_cls):
    """Garante que o prompt recebe query_original e query_reformulada separadas."""
    chain = mock_prompt_cls.from_template.return_value.__or__.return_value
    chain.invoke.return_value.content = "O DRS é..."

    state = {
        "query_original": "O que é DRS?",
        "query_reformulada": "Drag Reduction System Formula 1 2026 regulations",
        "retriever_result": {
            "hits": [{"content": "DRS context.", "score": 0.9, "metadata": {}}],
        },
    }

    generate(state)

    invoke_args = chain.invoke.call_args[0][0]
    assert invoke_args["query_original"] == "O que é DRS?"
    assert invoke_args["query_reformulada"] == "Drag Reduction System Formula 1 2026 regulations"
