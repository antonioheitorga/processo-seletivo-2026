import os

from agents.retriever import retrieve

# Perguntas respondíveis pelo corpus regulatório FIA 2026.
IN_SCOPE_QUERIES = [
    "What is the minimum mass in 2026 F1 regulations?",
    "Minimum car weight section C",
    "Power unit energy recovery limits",
    "DRS usage conditions during race",
    "Parc fermé rules and restrictions",
    "Budget cap exclusions for F1 teams",
    "Aerodynamic bodywork dimensional limits",
    "Front wing flexibility tests",
    "Tyre allocation for sprint weekends",
    "Penalties for unsafe release in pit lane",
    "Fuel flow limits in technical regs",
    "ERS deployment constraints",
    "Sporting rules for formation lap",
    "Track limits enforcement and penalties",
    "Financial regulation reporting deadlines",
    "Operational regulations for pit stop procedures",
    "PU manufacturer financial obligations",
    "Overtaking rules under safety car",
    "Rain tyre usage obligations",
    "Requirements for rookie practice sessions",
]

# Perguntas sobre fatos/resultados de temporada — o corpus é regulamento puro,
# não contém resultados de corrida, campeões ou dados fora do domínio de F1.
# Devem acionar fallback web (best_score abaixo do threshold).
OUT_OF_SCOPE_QUERIES = [
    "Who won the 2025 F1 Drivers Championship and what team does he drive for in 2026?",
    "What is the capital of France?",
    "Which driver has the most world championships in F1 history?",
    "What was Max Verstappen's salary in 2024?",
    "What happened in the 2024 Abu Dhabi Grand Prix?",
]


def _run(queries: list[str]) -> list[tuple[str, float, bool, int]]:
    results = []
    for q in queries:
        r = retrieve({"query_original": q})
        rr = r["retriever_result"]
        results.append((q, rr["best_score"], rr["fallback_to_web"], rr["total_hits"]))
    return results


def _report(label: str, results: list[tuple[str, float, bool, int]]) -> None:
    web = sum(1 for _, _, fallback, _ in results if fallback)
    print(f"--- {label} (total={len(results)}, fallback_web={web}) ---")
    for i, (q, score, fallback, hits) in enumerate(results, start=1):
        print(
            f"{i:02d}. score={score:.4f} | fallback_web={fallback} | "
            f"hits={hits} | {q[:70]}"
        )


def main() -> None:
    threshold = os.getenv("RETRIEVER_THRESHOLD", "0.72")
    print(f"THRESHOLD={threshold}")

    in_scope = _run(IN_SCOPE_QUERIES)
    out_scope = _run(OUT_OF_SCOPE_QUERIES)

    _report("IN_SCOPE (esperado: fallback_web=False)", in_scope)
    _report("OUT_OF_SCOPE (esperado: fallback_web=True)", out_scope)

    misclassified_in = [q for q, _, fb, _ in in_scope if fb]
    misclassified_out = [q for q, _, fb, _ in out_scope if not fb]

    print("---RESUMO---")
    print(f"In-scope classificado como fallback (falso positivo): {len(misclassified_in)}")
    print(f"Out-of-scope NÃO classificado como fallback (falso negativo): {len(misclassified_out)}")
    if misclassified_in or misclassified_out:
        print("Threshold pode precisar de ajuste — ver listas acima.")
    else:
        print(f"Threshold {threshold} separa os dois conjuntos sem erro.")


if __name__ == "__main__":
    main()
