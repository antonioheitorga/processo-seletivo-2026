"""Executa o benchmark de avaliação contra um dos splits do dataset (validação ou teste).

Para cada pergunta, roda o sistema multiagente completo (orchestration.orchestrator.run),
calcula uma pontuação e produz uma tabela de resultados em Markdown + JSON.

Metodologia (ver evaluation/README.md para a justificativa completa):

- Perguntas tipo "rag" (respondíveis pelo corpus):
    pontuação = 0.7 * correctness (LLM-as-judge, 0.0/0.5/1.0) + 0.3 * fonte_correta (0/1)
    fonte_correta = 1 se `fonte` resultante for "corpus" ou "hybrid" (não deveria
    precisar de fallback puro para web).

- Perguntas tipo "fallback" (projetadas para NÃO estar no corpus):
    pontuação = 1.0 se `fonte` resultante for "web" ou "hybrid" (fallback acionado
    corretamente), 0.0 caso contrário (sistema tentou responder só com o corpus).
    Não avaliamos a exatidão factual da resposta web (não determinística e fora
    do controle do corpus) — avaliamos se o sistema reconheceu corretamente que
    precisava do fallback, que é o comportamento sob teste neste desafio.

Uso:
    python -m evaluation.run_benchmark --split teste
    python -m evaluation.run_benchmark --split validacao
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestration.orchestrator import run as run_pipeline  # noqa: E402

DATASET_PATH = Path(__file__).resolve().parent / "dataset.json"
RESULTS_DIR = Path(__file__).resolve().parent / "results"


def _llm_judge_correctness(pergunta: str, esperado: str, gerado: str) -> float:
    """LLM-as-judge determinístico (temperature=0) via Ollama local.

    Retorna 0.0 (incorreto), 0.5 (parcialmente correto) ou 1.0 (correto).
    """
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_ollama import ChatOllama

    prompt = ChatPromptTemplate.from_template(
        """You are grading whether a generated answer matches an expected answer for a
factual question about FIA Formula 1 2026 regulations.

Question: {pergunta}
Expected answer: {esperado}
Generated answer: {gerado}

Score the generated answer against the expected answer:
- "1.0" if it conveys the same fact(s) correctly (wording may differ)
- "0.5" if it is partially correct or vague but not wrong
- "0.0" if it is incorrect, missing, or contradicts the expected answer

Respond with ONLY the score: 1.0, 0.5, or 0.0"""
    )
    llm = ChatOllama(
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        model=os.getenv("LLM_MODEL", "llama3.1:8b"),
        temperature=0.0,
    )
    chain = prompt | llm
    raw = chain.invoke({"pergunta": pergunta, "esperado": esperado, "gerado": gerado}).content.strip()
    for candidate in ("1.0", "0.5", "0.0"):
        if candidate in raw:
            return float(candidate)
    return 0.0


def _fontes_recuperadas(state: dict) -> str:
    """Lista as fontes concretas usadas (arquivos do corpus e/ou URLs web)."""
    fontes = []
    hits = (state.get("retriever_result") or {}).get("hits", [])
    for h in hits[:3]:
        src = (h.get("metadata") or {}).get("source_file")
        if src:
            fontes.append(src)
    web_items = (state.get("web_result") or {}).get("resultados", [])
    for item in web_items[:3]:
        url = item.get("url")
        if url:
            fontes.append(url)
    return "; ".join(dict.fromkeys(fontes)) or "—"


def avaliar_item(item: dict) -> dict:
    pergunta = item["pergunta"]
    tipo = item["tipo"]

    inicio = time.time()
    state = run_pipeline(pergunta, session_id=f"bench-{item['id']}")
    latencia_s = round(time.time() - inicio, 1)

    fonte = state.get("fonte", "none")
    resposta = state.get("resposta", "")

    if tipo == "rag":
        correctness = _llm_judge_correctness(pergunta, item["resposta_esperada"], resposta)
        fonte_correta = 1.0 if fonte in ("corpus", "hybrid") else 0.0
        pontuacao = round(0.7 * correctness + 0.3 * fonte_correta, 2)
    else:  # fallback
        fonte_correta = 1.0 if fonte in ("web", "hybrid") else 0.0
        correctness = None
        pontuacao = fonte_correta

    return {
        "id": item["id"],
        "pergunta": pergunta,
        "tipo": tipo,
        "fonte_esperada": item["fonte_esperada"],
        "fonte_obtida": fonte,
        "fonte_recuperada": _fontes_recuperadas(state),
        "resposta_gerada": resposta,
        "correctness_llm_judge": correctness,
        "pontuacao": pontuacao,
        "latencia_s": latencia_s,
        "session_id": f"bench-{item['id']}",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["validacao", "teste"], default="teste")
    args = parser.parse_args()

    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    itens = dataset["validacao"] if args.split == "validacao" else dataset["teste"]

    resultados = []
    for i, item in enumerate(itens, start=1):
        print(f"[{i}/{len(itens)}] {item['id']}: {item['pergunta'][:70]}...")
        resultado = avaliar_item(item)
        print(f"    fonte={resultado['fonte_obtida']} score={resultado['pontuacao']}")
        resultados.append(resultado)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    json_path = RESULTS_DIR / f"resultados_{args.split}.json"
    json_path.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")

    md_path = RESULTS_DIR / f"resultados_{args.split}.md"
    _write_markdown_table(resultados, args.split, md_path)

    media = sum(r["pontuacao"] for r in resultados) / len(resultados)
    media_rag = _media_por_tipo(resultados, "rag")
    media_fb = _media_por_tipo(resultados, "fallback")
    fallback_acertos = sum(
        1 for r in resultados if r["tipo"] == "fallback" and r["fonte_obtida"] in ("web", "hybrid")
    )
    fallback_total = sum(1 for r in resultados if r["tipo"] == "fallback")

    print("\n=== RESUMO ===")
    print(f"Split: {args.split}")
    print(f"Pontuação média geral: {media:.2f}")
    print(f"Pontuação média RAG: {media_rag}")
    print(f"Pontuação média Fallback: {media_fb}")
    print(f"Fallback acionado corretamente: {fallback_acertos}/{fallback_total}")
    print(f"Resultados salvos em: {json_path} e {md_path}")


def _media_por_tipo(resultados: list[dict], tipo: str) -> str:
    valores = [r["pontuacao"] for r in resultados if r["tipo"] == tipo]
    return f"{sum(valores) / len(valores):.2f}" if valores else "—"


def _write_markdown_table(resultados: list[dict], split: str, path: Path) -> None:
    linhas = [
        f"# Resultados — split {split}\n",
        "| ID | Pergunta | Tipo | Fonte esperada | Fonte obtida | Fonte recuperada | Pontuação |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in resultados:
        pergunta_curta = r["pergunta"].replace("|", "/")[:80]
        fonte_recuperada_curta = r["fonte_recuperada"][:60].replace("|", "/")
        linhas.append(
            f"| {r['id']} | {pergunta_curta} | {r['tipo']} | {r['fonte_esperada']} | "
            f"{r['fonte_obtida']} | {fonte_recuperada_curta} | {r['pontuacao']} |"
        )
    path.write_text("\n".join(linhas) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
