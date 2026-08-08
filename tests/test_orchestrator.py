"""Smoke tests do Orquestrador LangGraph.

Os 5 agentes são mockados — os testes verificam apenas o roteamento
do grafo (incluindo o loop de reflexão via verifier), não o
comportamento interno de cada agente.
"""

from unittest.mock import patch

from orchestration.orchestrator import _route_after_retriever, run


def test_route_after_retriever_primeira_tentativa_score_alto_vai_direto_generator():
    state = {"retriever_result": {"fallback_to_web": False}, "retry_count": 0}
    assert _route_after_retriever(state) == "generator"


def test_route_after_retriever_score_baixo_sempre_vai_web_searcher():
    state = {"retriever_result": {"fallback_to_web": True}, "retry_count": 0}
    assert _route_after_retriever(state) == "web_searcher"


def test_route_after_retriever_retentativa_forca_web_searcher_mesmo_com_score_alto():
    """Achado do benchmark: query reformulada em vocabulário formal pode 'enganar'
    o Retriever (score alto contra chunk irrelevante). Numa retentativa (o
    Verificador já reprovou a resposta baseada só em corpus), sempre busca web."""
    state = {"retriever_result": {"fallback_to_web": False}, "retry_count": 1}
    assert _route_after_retriever(state) == "web_searcher"


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


def _fake_search_web(state):
    return {
        "web_result": {
            "resultados": [{"titulo": "T", "trecho": "C", "url": "http://x"}],
            "encontrou": True,
        },
        "trace": state.get("trace", []) + [{"agente": "web_searcher"}],
    }


def _fake_generate(state):
    return {
        "generator_result": {
            "answer": "final answer",
            "sources_used": "corpus",
            "low_confidence": False,
            "confidence_notice": None,
        },
        "resposta": "final answer",
        "fonte": "corpus",
        "low_confidence": False,
        "confidence_warning": None,
        "trace": state.get("trace", []) + [{"agente": "generator"}],
    }


def _fake_verify_grounded(state):
    return {
        "verifier_result": {"grounded": True, "justification": "ok", "attempt": 1, "will_retry": False},
        "retry_count": state.get("retry_count", 0),
        "trace": state.get("trace", []) + [{"agente": "verifier"}],
    }


def _fake_verify_not_grounded_then_retry(state):
    """Reprova na 1ª tentativa (retry_count=0) e aprova na 2ª (retry_count=1)."""
    retry_count = state.get("retry_count", 0)
    if retry_count == 0:
        return {
            "verifier_result": {"grounded": False, "justification": "faltou contexto", "attempt": 1, "will_retry": True},
            "retry_count": 1,
            "trace": state.get("trace", []) + [{"agente": "verifier"}],
        }
    return {
        "verifier_result": {"grounded": True, "justification": "ok agora", "attempt": 2, "will_retry": False},
        "retry_count": retry_count,
        "trace": state.get("trace", []) + [{"agente": "verifier"}],
    }


def _fake_verify_never_grounded(state):
    """Sempre reprova; usado para validar que o loop encerra após VERIFIER_MAX_RETRIES."""
    retry_count = state.get("retry_count", 0)
    will_retry = retry_count < 1
    return {
        "verifier_result": {
            "grounded": False,
            "justification": "sem fundamentação",
            "attempt": retry_count + 1,
            "will_retry": will_retry,
        },
        "retry_count": retry_count + 1,
        "trace": state.get("trace", []) + [{"agente": "verifier"}],
        **({"low_confidence": True, "confidence_warning": "esgotou tentativas"} if not will_retry else {}),
    }


@patch("orchestration.orchestrator.verify", side_effect=_fake_verify_grounded)
@patch("orchestration.orchestrator.generate", side_effect=_fake_generate)
@patch("orchestration.orchestrator.search_web", side_effect=_fake_search_web)
@patch("orchestration.orchestrator.retrieve", side_effect=_fake_retrieve_hit)
@patch("orchestration.orchestrator.reformulate", side_effect=_fake_reformulate)
def test_fluxo_corpus(mock_ref, mock_ret, mock_web, mock_gen, mock_ver):
    final_state = run("o que é DRS?")

    assert mock_ref.called
    assert mock_ret.called
    assert mock_web.called is False
    assert mock_gen.called
    assert mock_ver.called

    agentes = [t["agente"] for t in final_state["trace"]]
    assert agentes == ["reformulator", "retriever", "generator", "verifier"]


@patch("orchestration.orchestrator.verify", side_effect=_fake_verify_grounded)
@patch("orchestration.orchestrator.generate", side_effect=_fake_generate)
@patch("orchestration.orchestrator.search_web", side_effect=_fake_search_web)
@patch("orchestration.orchestrator.retrieve", side_effect=_fake_retrieve_miss)
@patch("orchestration.orchestrator.reformulate", side_effect=_fake_reformulate)
def test_fluxo_web_fallback(mock_ref, mock_ret, mock_web, mock_gen, mock_ver):
    final_state = run("pergunta fora do corpus")

    assert mock_web.called
    agentes = [t["agente"] for t in final_state["trace"]]
    assert agentes == ["reformulator", "retriever", "web_searcher", "generator", "verifier"]


@patch("orchestration.orchestrator.verify", side_effect=_fake_verify_not_grounded_then_retry)
@patch("orchestration.orchestrator.generate", side_effect=_fake_generate)
@patch("orchestration.orchestrator.search_web", side_effect=_fake_search_web)
@patch("orchestration.orchestrator.retrieve", side_effect=_fake_retrieve_hit)
@patch("orchestration.orchestrator.reformulate", side_effect=_fake_reformulate)
def test_loop_reflexao_retenta_e_aprova(mock_ref, mock_ret, mock_web, mock_gen, mock_ver):
    """Verifier reprova a 1ª resposta -> volta pro reformulator -> aprova na 2ª.

    Mesmo o retriever "achando" hits acima do threshold nas duas passagens
    (_fake_retrieve_hit), a retentativa (retry_count > 0) também aciona o
    web_searcher — a 1ª tentativa já provou que só corpus não bastou.
    """
    final_state = run("pergunta ambígua")

    assert mock_ref.call_count == 2
    assert mock_web.call_count == 1
    assert mock_gen.call_count == 2
    assert mock_ver.call_count == 2

    agentes = [t["agente"] for t in final_state["trace"]]
    assert agentes == [
        "reformulator", "retriever", "generator", "verifier",
        "reformulator", "retriever", "web_searcher", "generator", "verifier",
    ]
    assert final_state["verifier_result"]["grounded"] is True


@patch("orchestration.orchestrator.verify", side_effect=_fake_verify_never_grounded)
@patch("orchestration.orchestrator.generate", side_effect=_fake_generate)
@patch("orchestration.orchestrator.search_web", side_effect=_fake_search_web)
@patch("orchestration.orchestrator.retrieve", side_effect=_fake_retrieve_hit)
@patch("orchestration.orchestrator.reformulate", side_effect=_fake_reformulate)
def test_loop_reflexao_encerra_apos_max_retries(mock_ref, mock_ret, mock_web, mock_gen, mock_ver):
    """Verifier nunca aprova -> grafo encerra (não roda para sempre) e marca low_confidence."""
    final_state = run("pergunta sem resposta fundamentável")

    # 1 tentativa inicial + 1 retentativa (VERIFIER_MAX_RETRIES default = 1) = 2 chamadas
    assert mock_ver.call_count == 2
    assert final_state["verifier_result"]["grounded"] is False
    assert final_state["verifier_result"]["will_retry"] is False
    assert final_state["low_confidence"] is True


@patch("orchestration.orchestrator.verify", side_effect=_fake_verify_grounded)
@patch("orchestration.orchestrator.generate", side_effect=_fake_generate)
@patch("orchestration.orchestrator.search_web", side_effect=_fake_search_web)
@patch("orchestration.orchestrator.retrieve", side_effect=_fake_retrieve_hit)
@patch("orchestration.orchestrator.reformulate", side_effect=_fake_reformulate)
def test_run_gera_session_id(mock_ref, mock_ret, mock_web, mock_gen, mock_ver):
    final_state = run("qualquer query")

    assert "session_id" in final_state
    assert len(final_state["session_id"]) > 0


@patch("orchestration.orchestrator.verify", side_effect=_fake_verify_grounded)
@patch("orchestration.orchestrator.generate", side_effect=_fake_generate)
@patch("orchestration.orchestrator.search_web", side_effect=_fake_search_web)
@patch("orchestration.orchestrator.retrieve", side_effect=_fake_retrieve_hit)
@patch("orchestration.orchestrator.reformulate", side_effect=_fake_reformulate)
def test_state_final_completo(mock_ref, mock_ret, mock_web, mock_gen, mock_ver):
    final_state = run("qualquer query", session_id="fixed-id")

    assert final_state["session_id"] == "fixed-id"
    assert final_state["resposta"] == "final answer"
    assert final_state["fonte"] == "corpus"
    assert final_state["low_confidence"] is False
    assert "generator_result" in final_state
    assert final_state["verifier_result"]["grounded"] is True
