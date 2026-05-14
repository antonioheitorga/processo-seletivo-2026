import os

from agents.retriever import retrieve


def main() -> None:

    queries = [
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

    threshold = os.getenv("RETRIEVER_THRESHOLD", "0.80")

    results = []
    for q in queries:
        r = retrieve({"query_original": q})
        rr = r["retriever_result"]
        results.append((q, rr["best_score"], rr["fallback_to_web"], rr["total_hits"]))

    web = sum(1 for _, _, fallback, _ in results if fallback)
    meets = len(results) - web

    print(f"THRESHOLD={threshold}")
    print(f"TOTAL={len(results)}")
    print(f"WEB_FALLBACK={web}")
    print(f"MEETS_THRESHOLD={meets}")
    print("---DETAIL---")
    for i, (q, score, fallback, hits) in enumerate(results, start=1):
        print(
            f"{i:02d}. score={score:.4f} | fallback_web={fallback} | "
            f"hits={hits} | {q}"
        )


if __name__ == "__main__":
    main()
