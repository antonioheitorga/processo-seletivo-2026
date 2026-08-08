"""Métrica de avaliação: correção factual via LLM-as-judge.

Por que essa métrica e não outra:

- Exact match / overlap textual falha nesse domínio porque as respostas
  esperadas são multi-cláusula e parafraseáveis (ex: "726kg mais a Nominal
  Tyre Mass" pode ser respondido de várias formas corretas).
- Similaridade de embeddings (cosseno) foi cogitada, mas tem um problema
  sério para regulamento técnico: duas respostas com a mesma estrutura mas
  um número trocado (ex: "25 pontos" vs "18 pontos") ficam com similaridade
  alta mesmo estando factualmente erradas — o erro que mais importa pegar
  aqui é exatamente esse.
- LLM-as-judge comparando resposta gerada x resposta esperada pega
  divergência factual (número errado, condição omitida, cláusula trocada)
  em vez de só medir proximidade semântica de superfície. Reusa a mesma
  infraestrutura (Ollama · llama3.1:8b) já usada pelo Verificador.

Escala: 0.0 (incorreta) / 0.5 (parcialmente correta — captura o essencial
mas omite ou erra um detalhe) / 1.0 (correta e completa frente ao gabarito).
Para as perguntas de fallback (`espera_fallback=True`), o gabarito é "a
resposta não deveria vir do corpus" — a pontuação nesses casos mede se o
sistema roteou corretamente para a web e produziu uma resposta razoável a
partir dela (não se comparando contra um fato específico).
"""

import os

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import ChatOllama


PROMPT_TEMPLATE = """You are grading the correctness of an AI-generated answer for a Formula 1 \
regulations QA system, against a grading criterion for this specific question. The criterion is \
either a literal gold-standard answer to match factually, or explicit scoring instructions (used \
for questions designed to trigger web-search fallback, where there's no single fixed fact to match).

Question: {pergunta}

Grading criterion for this question:
{resposta_esperada}

Generated answer to grade:
{resposta_gerada}

Instructions:
- Score 1.0 if the generated answer is factually correct and captures the key facts/conditions of the gold answer.
- Score 0.5 if it's partially correct (right general idea, but misses or gets wrong a specific detail/number/condition).
- Score 0.0 if it's factually incorrect, contradicts the gold answer, or fails to answer.
- Judge factual correctness only — wording/length differences don't matter.

Respond strictly in this format:
SCORE: 1.0 or 0.5 or 0.0
JUSTIFICATION: <one short sentence>"""


def _parse_score(raw: str) -> tuple[float, str]:
    score = 0.0
    justification = raw.strip()

    for line in raw.splitlines():
        line = line.strip()
        if line.upper().startswith("SCORE:"):
            value = line.split(":", 1)[1].strip()
            try:
                score = float(value)
            except ValueError:
                score = 0.0
        elif line.upper().startswith("JUSTIFICATION:"):
            justification = line.split(":", 1)[1].strip()

    return score, justification


def score_answer(pergunta: str, resposta_esperada: str, resposta_gerada: str) -> dict:
    """Avalia a resposta gerada contra o gabarito. Retorna {score, justification}."""
    if not (resposta_gerada or "").strip():
        return {"score": 0.0, "justification": "Sistema não produziu resposta."}

    llm = ChatOllama(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=os.getenv("LLM_MODEL", "llama3.1:8b"),
        temperature=0.0,
    )
    chain = ChatPromptTemplate.from_template(PROMPT_TEMPLATE) | llm
    resposta = chain.invoke(
        {
            "pergunta": pergunta,
            "resposta_esperada": resposta_esperada,
            "resposta_gerada": resposta_gerada,
        }
    )
    score, justification = _parse_score(resposta.content)
    return {"score": score, "justification": justification}
