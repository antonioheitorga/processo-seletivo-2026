"""
02_validate.py
Valida os JSONs extraídos em extracted/.
Verifica: cobertura de páginas, páginas vazias, densidade de texto e consistência.
"""

import json
from pathlib import Path

EXTRACTED_DIR = Path(__file__).parent.parent / "extracted"
MIN_CHARS_PER_PAGE = 100   # páginas com menos caracteres são suspeitas
WARN_EMPTY_RATIO = 0.10     # alerta se >10% das páginas estiverem vazias


def validate_file(json_path: Path) -> dict:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    issues = []
    pages = data.get("pages", [])
    total = data.get("total_pages", 0)

    if not pages:
        issues.append("ERRO: nenhuma página encontrada no JSON.")
        return {"file": json_path.name, "ok": False, "issues": issues, "stats": {}}

    empty_pages = [p["page"] for p in pages if p["char_count"] == 0]
    sparse_pages = [p["page"] for p in pages if 0 < p["char_count"] < MIN_CHARS_PER_PAGE]
    total_chars = sum(p["char_count"] for p in pages)
    avg_chars = total_chars / total if total else 0

    if len(empty_pages) / total > WARN_EMPTY_RATIO:
        issues.append(
            f"AVISO: {len(empty_pages)} páginas vazias ({len(empty_pages)/total:.0%}) → {empty_pages[:10]}"
        )
    if sparse_pages:
        issues.append(
            f"AVISO: {len(sparse_pages)} páginas esparsas (<{MIN_CHARS_PER_PAGE} chars) → {sparse_pages[:10]}"
        )
    if avg_chars < 200:
        issues.append(f"AVISO: média muito baixa de {avg_chars:.0f} chars/página — possível PDF escaneado.")

    stats = {
        "total_pages": total,
        "empty_pages": len(empty_pages),
        "sparse_pages": len(sparse_pages),
        "total_chars": total_chars,
        "avg_chars_page": round(avg_chars, 1),
    }
    return {"file": json_path.name, "ok": len(issues) == 0, "issues": issues, "stats": stats}


def main():
    jsons = sorted(EXTRACTED_DIR.glob("*.json"))
    if not jsons:
        print("Nenhum JSON encontrado em extracted/. Execute 01_extract.py primeiro.")
        return

    print(f"Validando {len(jsons)} arquivo(s) extraídos...\n")
    all_ok = True
    for jp in jsons:
        result = validate_file(jp)
        status = "OK" if result["ok"] else "PROBLEMA"
        s = result["stats"]
        print(f"[{status}] {result['file']}")
        print(f"       Páginas: {s.get('total_pages')} | "
              f"Vazias: {s.get('empty_pages')} | "
              f"Esparsas: {s.get('sparse_pages')} | "
              f"Total chars: {s.get('total_chars', 0):,} | "
              f"Média/pág: {s.get('avg_chars_page')}")
        for issue in result["issues"]:
            print(f"       → {issue}")
            all_ok = False
        print()

    if all_ok:
        print("Validação concluída sem problemas.")
    else:
        print("Validação concluída com avisos — revise os itens acima.")


if __name__ == "__main__":
    main()
