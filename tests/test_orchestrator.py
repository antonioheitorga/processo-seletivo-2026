"""Smoke tests do Orquestrador LangGraph — arquitetura hub-and-spoke.

Os agentes são mockados. Os testes verificam:
- Que o Orquestrador é o nó central (intercalado entre cada agente)
- Que o roteamento condicional funciona (corpus vs. web fallback)
- Que o Orquestrador é quem escreve `fonte`, `low_confidence` e `resposta`
- Que a anti-alucinação aborta a geração quando não há contexto
"""

from unittest.mock import patch

from orchestration.orchestrator import run


def _fake_reformulate(state):
    return {
        "query_reformulada": "reformulated query",
        "trace": state.get("trace", []) + [{"agente": "reformulator"}],
    }


def _fake_retrieve_hit(state):
    return {
        "retriever_result": {
            "fallback_to_web": False,
            "best_score": 0.85,
            "hits": [{"content": "corpus chunk", "score": 0.85, "metadata": {}}],
            "confidence_warning": None,
        },
        "trace": state.get("trace", []) + [{"agente": "retriever"}],
    }


def _fake_retrieve_miss(state):
    return {
        "retriever_result": {
            "fallback_to_web": True,
            "best_score": 0.2,
            "hits": [],
            "confidence_warning": "Score abaixo do threshold.",
        },
        "trace": state.get("trace", []) + [{"agente": "retriever"}],
    }


def _fake_search_web_hit(state):
    return {
        "web_result": {
            "resultados": [{"titulo": "T", "trecho": "C", "url": "http://x"}],
            "encontrou": True,
        },
        "trace": state.get("trace", []) + [{"agente": "web_searcher"}],
    }


def _fake_search_web_miss(state):
    return {
        "web_result": {"resultados": [], "encontrou": False},
        "trace": state.get("trace", []) + [{"agente": "web_searcher"}],
    }


def _fake_generate(state):
    return {
        "generator_result": {
            "result": "ok",
            "answer": "final answer",
            "reason": None,
        },
        "trace": state.get("trace", []) + [{"agente": "generator"}],
    }


def _fake_judge_approve(state):
    return {
        "judge_result": {
            "approved": True,
            "decision": "approve",
            "sources_used": "corpus",
            "reasons": [],
        },
        "needs_revision": False,
        "trace": state.get("trace", []) + [{"agente": "judge"}],
    }


@patch("orchestration.orchestrator.judge", side_effect=_fake_judge_approve)
@patch("orchestration.orchestrator.generate", side_effect=_fake_generate)
@patch("orchestration.orchestrator.search_web", side_effect=_fake_search_web_hit)
@patch("orchestration.orchestrator.retrieve", side_effect=_fake_retrieve_hit)
@patch("orchestration.orchestrator.reformulate", side_effect=_fake_reformulate)
def test_fluxo_corpus_intercala_orchestrator(mock_ref, mock_ret, mock_web, mock_gen, mock_judge):
    """Caminho corpus: orquestrador intercala entre cada agente, nunca chama web."""
    final_state = run("o que é DRS?")

    assert mock_ref.called
    assert mock_ret.called
    assert mock_web.called is False
    assert mock_gen.called
    assert mock_judge.called

    agentes = [t["agente"] for t in final_state["trace"]]
    # Orquestrador aparece entre cada agente — confirma hub-and-spoke
    assert agentes == [
        "orchestrator",
        "reformulator",
        "orchestrator",
        "retriever",
        "orchestrator",
        "generator",
        "orchestrator",
        "judge",
        "orchestrator",
    ]


@patch("orchestration.orchestrator.judge", side_effect=_fake_judge_approve)
@patch("orchestration.orchestrator.generate", side_effect=_fake_generate)
@patch("orchestration.orchestrator.search_web", side_effect=_fake_search_web_hit)
@patch("orchestration.orchestrator.retrieve", side_effect=_fake_retrieve_miss)
@patch("orchestration.orchestrator.reformulate", side_effect=_fake_reformulate)
def test_fluxo_web_fallback(mock_ref, mock_ret, mock_web, mock_gen, mock_judge):
    """Caminho web: orquestrador decide chamar web após corpus falhar."""
    final_state = run("pergunta fora do corpus")

    assert mock_web.called
    assert mock_judge.called
    agentes = [t["agente"] for t in final_state["trace"]]
    assert agentes == [
        "orchestrator",
        "reformulator",
        "orchestrator",
        "retriever",
        "orchestrator",
        "web_searcher",
        "orchestrator",
        "generator",
        "orchestrator",
        "judge",
        "orchestrator",
    ]
    assert final_state["fonte"] == "web"


@patch("orchestration.orchestrator.judge", side_effect=_fake_judge_approve)
@patch("orchestration.orchestrator.generate", side_effect=_fake_generate)
@patch("orchestration.orchestrator.search_web", side_effect=_fake_search_web_miss)
@patch("orchestration.orchestrator.retrieve", side_effect=_fake_retrieve_miss)
@patch("orchestration.orchestrator.reformulate", side_effect=_fake_reformulate)
def test_anti_alucinacao_aborta_geracao(mock_ref, mock_ret, mock_web, mock_gen, mock_judge):
    """Corpus vazio + web vazia: orquestrador NÃO chama generator nem judge."""
    final_state = run("pergunta sem contexto algum")

    assert mock_web.called
    assert mock_gen.called is False
    assert mock_judge.called is False

    assert final_state["fonte"] == "none"
    assert final_state["low_confidence"] is True
    assert "Não foi possível encontrar" in final_state["resposta"]


@patch("orchestration.orchestrator.judge", side_effect=_fake_judge_approve)
@patch("orchestration.orchestrator.generate", side_effect=_fake_generate)
@patch("orchestration.orchestrator.search_web", side_effect=_fake_search_web_hit)
@patch("orchestration.orchestrator.retrieve", side_effect=_fake_retrieve_hit)
@patch("orchestration.orchestrator.reformulate", side_effect=_fake_reformulate)
def test_run_gera_session_id(mock_ref, mock_ret, mock_web, mock_gen, mock_judge):
    final_state = run("qualquer query")
    assert "session_id" in final_state
    assert len(final_state["session_id"]) > 0


@patch("orchestration.orchestrator.judge", side_effect=_fake_judge_approve)
@patch("orchestration.orchestrator.generate", side_effect=_fake_generate)
@patch("orchestration.orchestrator.search_web", side_effect=_fake_search_web_hit)
@patch("orchestration.orchestrator.retrieve", side_effect=_fake_retrieve_hit)
@patch("orchestration.orchestrator.reformulate", side_effect=_fake_reformulate)
def test_state_final_completo(mock_ref, mock_ret, mock_web, mock_gen, mock_judge):
    """Orquestrador escreve resposta/fonte/low_confidence no estado final."""
    final_state = run("qualquer query", session_id="fixed-id")

    assert final_state["session_id"] == "fixed-id"
    assert final_state["resposta"] == "final answer"
    assert final_state["fonte"] == "corpus"
    assert final_state["low_confidence"] is False
    assert "generator_result" in final_state
    assert "judge_result" in final_state
    assert final_state["needs_revision"] is False
