"""Executa o benchmark de avaliação (avaliacao/dataset.json) contra o sistema real.

Uso:
    python3 -m avaliacao.run_eval              # roda os 20 pares (val + test)
    python3 -m avaliacao.run_eval --split test  # roda só o conjunto de teste

Para cada pergunta, roda o grafo completo (orchestration.orchestrator.run),
registra fonte recuperada, se o roteamento (RAG vs fallback) bateu com o
esperado, a resposta gerada e a pontuação de correção (avaliacao.metrica).

Os resultados do conjunto de TESTE são os reportados oficialmente (conforme
exigido pelo edital); os de validação existem para diagnóstico durante o
desenvolvimento e não entram na nota reportada.
"""

import argparse
import csv
import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from avaliacao.metrica import score_answer  # noqa: E402
from orchestration.orchestrator import run  # noqa: E402

BASE_DIR = Path(__file__).parent
DATASET_PATH = BASE_DIR / "dataset.json"


def _run_item(item: dict) -> dict:
    state = run(item["pergunta"])

    retriever_result = state.get("retriever_result") or {}
    verifier_result = state.get("verifier_result") or {}
    fallback_acionado = bool(retriever_result.get("fallback_to_web", False)) or state.get("fonte") in ("web", "hybrid")

    avaliacao = score_answer(
        pergunta=item["pergunta"],
        resposta_esperada=item["resposta_esperada"],
        resposta_gerada=state.get("resposta", ""),
    )

    return {
        "id": item["id"],
        "split": item["split"],
        "pergunta": item["pergunta"],
        "fonte_recuperada": state.get("fonte", "none"),
        "rag_ou_fallback": "fallback" if fallback_acionado else "rag",
        "espera_fallback": item["espera_fallback"],
        "roteamento_correto": fallback_acionado == item["espera_fallback"],
        "resposta_gerada": state.get("resposta", ""),
        "pontuacao": avaliacao["score"],
        "justificativa_score": avaliacao["justification"],
        "grounded": verifier_result.get("grounded"),
        "low_confidence": state.get("low_confidence", False),
        "session_id": state.get("session_id", ""),
    }


def _write_csv(rows: list[dict], path: Path) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _write_markdown(rows: list[dict], path: Path, titulo: str) -> None:
    lines = [f"# {titulo}", ""]
    if rows:
        media = sum(r["pontuacao"] for r in rows) / len(rows)
        roteamento_ok = sum(1 for r in rows if r["roteamento_correto"])
        lines.append(f"- Perguntas: {len(rows)}")
        lines.append(f"- Pontuação média: {media:.3f}")
        lines.append(f"- Roteamento correto (RAG/fallback): {roteamento_ok}/{len(rows)}")
        lines.append("")
    lines.append("| ID | Pergunta | Fonte | RAG/Fallback | Roteamento OK | Pontuação | Resposta gerada |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in rows:
        resposta_curta = (r["resposta_gerada"] or "").replace("\n", " ")[:160]
        pergunta_curta = r["pergunta"].replace("\n", " ")
        lines.append(
            f"| {r['id']} | {pergunta_curta} | {r['fonte_recuperada']} | {r['rag_ou_fallback']} | "
            f"{'✅' if r['roteamento_correto'] else '❌'} | {r['pontuacao']} | {resposta_curta} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--split", choices=["val", "test", "all"], default="all")
    args = parser.parse_args()

    dataset = json.loads(DATASET_PATH.read_text(encoding="utf-8"))
    if args.split != "all":
        dataset = [item for item in dataset if item["split"] == args.split]

    resultados_por_split: dict[str, list[dict]] = {"val": [], "test": []}

    for i, item in enumerate(dataset, start=1):
        print(f"[{i}/{len(dataset)}] ({item['split']}) {item['pergunta']}")
        row = _run_item(item)
        resultados_por_split[item["split"]].append(row)
        print(
            f"    fonte={row['fonte_recuperada']} roteamento_ok={row['roteamento_correto']} "
            f"score={row['pontuacao']} grounded={row['grounded']}"
        )

    if resultados_por_split["val"]:
        _write_csv(resultados_por_split["val"], BASE_DIR / "resultados_validacao.csv")
        _write_markdown(resultados_por_split["val"], BASE_DIR / "resultados_validacao.md", "Resultados — Conjunto de Validação")

    if resultados_por_split["test"]:
        _write_csv(resultados_por_split["test"], BASE_DIR / "resultados_teste.csv")
        _write_markdown(
            resultados_por_split["test"], BASE_DIR / "resultados_teste.md",
            "Resultados — Conjunto de Teste (reportado oficialmente)",
        )

    print("\nConcluído. Resultados salvos em avaliacao/resultados_*.{csv,md}")


if __name__ == "__main__":
    main()
