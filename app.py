"""Interface Streamlit do F1 RAG System."""

import json
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from orchestration.orchestrator import run  # noqa: E402

# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="F1 RAG System",
    page_icon="🏎️",
    layout="centered",
)

# ---------------------------------------------------------------------------
# Estado da sessão
# ---------------------------------------------------------------------------

if "historico" not in st.session_state:
    st.session_state.historico = []  # lista de dicts {query, resposta, fonte, low_confidence, trace}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FONTE_BADGE = {
    "corpus": ("📚 Corpus FIA", "green"),
    "web": ("🌐 Web", "blue"),
    "hybrid": ("📚🌐 Corpus + Web", "violet"),
    "none": ("❌ Sem fonte", "red"),
}


def _badge(fonte: str) -> str:
    label, color = _FONTE_BADGE.get(fonte, (fonte, "gray"))
    return f":{color}[{label}]"


def _render_trace(trace: list[dict]) -> None:
    for step in trace:
        agente = step.get("agente", "?")
        latencia = step.get("latencia_ms", 0)
        entrada = step.get("entrada", "")
        saida = step.get("saida", "")

        with st.container():
            st.markdown(f"**{agente}** — `{latencia} ms`")
            col1, col2 = st.columns(2)
            with col1:
                st.caption("Entrada")
                st.code(
                    entrada if isinstance(entrada, str) else json.dumps(entrada, ensure_ascii=False, indent=2),
                    language="text",
                )
            with col2:
                st.caption("Saída")
                st.code(
                    saida if isinstance(saida, str) else json.dumps(saida, ensure_ascii=False, indent=2),
                    language="text",
                )
            st.divider()


def _render_verifier_badge(verifier_result: dict) -> None:
    if not verifier_result:
        return
    attempt = verifier_result.get("attempt", 1)
    if verifier_result.get("grounded"):
        label = "✅ Fundamentado" if attempt == 1 else f"✅ Fundamentado (tentativa {attempt})"
        st.caption(label)
    else:
        st.caption(f"⚠️ Não fundamentado após {attempt} tentativa(s) — {verifier_result.get('justification', '')}")


def _render_result(item: dict, trace_in_expander: bool = True) -> None:
    fonte = item.get("fonte", "none")
    low = item.get("low_confidence", False)

    st.markdown(f"**Fonte:** {_badge(fonte)}")
    _render_verifier_badge(item.get("verifier_result", {}))

    if low:
        st.warning("⚠️ Baixa confiança — nenhuma fonte encontrou contexto relevante. A resposta pode ser imprecisa.")

    st.markdown(item.get("resposta", ""))

    if trace_in_expander:
        with st.expander("Ver trace de execução"):
            _render_trace(item.get("trace", []))
    else:
        st.markdown("**Trace de execução**")
        _render_trace(item.get("trace", []))


# ---------------------------------------------------------------------------
# Layout principal
# ---------------------------------------------------------------------------

st.title("🏎️ F1 RAG System")
st.caption("Perguntas sobre o Regulamento FIA de Fórmula 1 2026")

# Formulário de query
with st.form("query_form", clear_on_submit=True):
    query = st.text_input("Sua pergunta", placeholder="Ex: O que é DRS e quando pode ser usado?")
    submitted = st.form_submit_button("Perguntar", type="primary")

if submitted and query.strip():
    with st.spinner("Processando..."):
        state = run(query.strip())

    item = {
        "query": query.strip(),
        "resposta": state.get("resposta", ""),
        "fonte": state.get("fonte", "none"),
        "low_confidence": state.get("low_confidence", False),
        "verifier_result": state.get("verifier_result", {}),
        "trace": state.get("trace", []),
        "session_id": state.get("session_id", ""),
    }
    st.session_state.historico.insert(0, item)

elif submitted and not query.strip():
    st.error("Digite uma pergunta antes de enviar.")

# ---------------------------------------------------------------------------
# Exibição do resultado mais recente
# ---------------------------------------------------------------------------

if st.session_state.historico:
    latest = st.session_state.historico[0]

    st.subheader("Resposta")
    _render_result(latest)

    # Histórico da sessão
    if len(st.session_state.historico) > 1:
        st.markdown("---")
        st.subheader("Histórico desta sessão")

        for item in st.session_state.historico[1:]:
            with st.expander(f"❓ {item['query'][:80]}"):
                _render_result(item, trace_in_expander=False)
