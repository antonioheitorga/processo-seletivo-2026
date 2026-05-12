"""
pipeline.py
Orquestrador da pipeline de ingestão FIA 2026 F1 Regulations.
Executa todos os passos em sequência: 01 → 02 → 03 → 04 → 05 → 06

Uso:
    python3 pipeline.py            # pipeline completa
    python3 pipeline.py --from 3   # inicia a partir do passo 3
    python3 pipeline.py --only 5   # executa apenas o passo 5
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent / "scripts"

STEPS = [
    (1, "01_extract.py",     "Extração de texto dos PDFs"),
    (2, "02_validate.py",    "Validação da extração"),
    (3, "03_preprocess.py",  "Pré-processamento (limpeza + normalização)"),
    (4, "04_chunk.py",       "Chunking semântico"),
    (5, "05_embed_ingest.py","Embedding + Ingestão no ChromaDB"),
    (6, "06_verify.py",      "Verificação do Vector Store"),
]


def run_step(num: int, script: str, description: str) -> bool:
    path = SCRIPTS_DIR / script
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"  Passo {num}/{len(STEPS)} — {description}")
    print(f"{sep}\n")

    t0 = time.time()
    result = subprocess.run([sys.executable, str(path)])
    elapsed = time.time() - t0

    if result.returncode != 0:
        print(f"\n[FALHA] Passo {num} encerrado com erro (código {result.returncode}).")
        return False

    print(f"\n[OK] Passo {num} concluído em {elapsed:.1f}s")
    return True


def main():
    parser = argparse.ArgumentParser(description="Pipeline de ingestão FIA 2026")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--from", dest="from_step", type=int, default=1,
                       metavar="N", help="Inicia a partir do passo N (padrão: 1)")
    group.add_argument("--only", dest="only_step", type=int,
                       metavar="N", help="Executa apenas o passo N")
    args = parser.parse_args()

    if args.only_step:
        steps = [s for s in STEPS if s[0] == args.only_step]
        if not steps:
            print(f"Passo {args.only_step} inválido. Escolha entre 1 e {len(STEPS)}.")
            sys.exit(1)
    else:
        steps = [s for s in STEPS if s[0] >= args.from_step]

    print("\n╔══════════════════════════════════════════════════════════╗")
    print("║   Pipeline de Ingestão — FIA 2026 F1 Regulations        ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print(f"\nPassos a executar: {[s[0] for s in steps]}")

    pipeline_start = time.time()
    for num, script, description in steps:
        ok = run_step(num, script, description)
        if not ok:
            print(f"\nPipeline interrompida no passo {num}.")
            sys.exit(1)

    total = time.time() - pipeline_start
    print(f"\n{'='*60}")
    print(f"  Pipeline concluída com sucesso em {total:.1f}s")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
