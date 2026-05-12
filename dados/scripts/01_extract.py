"""
01_extract.py
Extrai texto de todos os PDFs do corpus usando pdfplumber.
Salva cada PDF como um JSON em extracted/ com metadados por página.
"""

import json
import pdfplumber
from pathlib import Path

CORPUS_DIR = Path(__file__).parent.parent / "corpus"
OUTPUT_DIR = Path(__file__).parent.parent / "extracted"
OUTPUT_DIR.mkdir(exist_ok=True)

# Mapeamento de seções para categorias legíveis
SECTION_MAP = {
    "section_a": "general_provisions",
    "section_b": "sporting",
    "section_c": "technical",
    "section_d": "financial_f1_teams",
    "section_e": "financial_pu_manufacturers",
    "section_f": "operational",
}


def detect_section(filename: str) -> str:
    for key, label in SECTION_MAP.items():
        if key in filename:
            return label
    return "unknown"


def extract_pdf(pdf_path: Path) -> dict:
    pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            pages.append({
                "page": i,
                "text": text,
                "char_count": len(text),
            })

    return {
        "source_file": pdf_path.name,
        "section": detect_section(pdf_path.name),
        "total_pages": len(pages),
        "pages": pages,
    }


def main():
    pdfs = sorted(CORPUS_DIR.glob("*.pdf"))
    if not pdfs:
        print("Nenhum PDF encontrado em corpus/")
        return

    print(f"Encontrados {len(pdfs)} PDFs para extração.\n")
    for pdf_path in pdfs:
        print(f"Extraindo: {pdf_path.name} ...", end=" ")
        data = extract_pdf(pdf_path)
        out_path = OUTPUT_DIR / (pdf_path.stem + ".json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        total_chars = sum(p["char_count"] for p in data["pages"])
        print(f"OK — {data['total_pages']} páginas, {total_chars:,} caracteres → {out_path.name}")

    print(f"\nExtração concluída. Arquivos salvos em: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
