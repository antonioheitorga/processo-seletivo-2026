"""Re-pontua resultados já gerados (resultados_{split}.csv) contra o dataset.json
atual, sem rodar o sistema de novo. Útil quando só o critério/gabarito de
avaliação muda, não o comportamento do sistema.

Uso:
    python3 -m avaliacao.rescore
"""

import csv
import json
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from avaliacao.metrica import score_answer  # noqa: E402
from avaliacao.run_eval import _write_csv, _write_markdown  # noqa: E402

BASE_DIR = Path(__file__).parent
DATASET_PATH = BASE_DIR / "dataset.json"


SPLIT_LABEL = {"val": "validacao", "test": "teste"}


def _rescore_split(split: str) -> None:
    csv_path = BASE_DIR / f"resultados_{SPLIT_LABEL[split]}.csv"
    if not csv_path.exists():
        print(f"(sem resultados_{split}.csv, pulando)")
        return

    dataset = {item["id"]: item for item in json.loads(DATASET_PATH.read_text(encoding="utf-8"))}

    with csv_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        item = dataset[row["id"]]
        avaliacao = score_answer(
            pergunta=row["pergunta"],
            resposta_esperada=item["resposta_esperada"],
            resposta_gerada=row["resposta_gerada"],
        )
        row["pontuacao"] = avaliacao["score"]
        row["justificativa_score"] = avaliacao["justification"]
        row["roteamento_correto"] = row["roteamento_correto"] == "True"
        for bool_field in ("espera_fallback", "grounded", "low_confidence"):
            if row.get(bool_field) in ("True", "False"):
                row[bool_field] = row[bool_field] == "True"
        print(f"  {row['id']}: score={row['pontuacao']}")

    _write_csv(rows, csv_path)
    titulo = "Resultados — Conjunto de Teste (reportado oficialmente)" if split == "test" else "Resultados — Conjunto de Validação"
    _write_markdown(rows, BASE_DIR / f"resultados_{SPLIT_LABEL[split]}.md", titulo)


def main() -> None:
    for split in ("val", "test"):
        print(f"Re-pontuando split={split}...")
        _rescore_split(split)
    print("Concluído.")


if __name__ == "__main__":
    main()
