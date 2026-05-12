"""
03_preprocess.py
Pré-processa os textos extraídos:
  - Limpeza: remove caracteres inválidos, ruídos e artefatos de PDF
  - Normalização: padroniza espaços, quebras de linha e formatação
Salva os resultados em processed/ como JSON.
"""

import json
import re
from pathlib import Path

EXTRACTED_DIR = Path(__file__).parent.parent / "extracted"
PROCESSED_DIR = Path(__file__).parent.parent / "processed"
PROCESSED_DIR.mkdir(exist_ok=True)


# ---------------------------------------------------------------------------
# Limpeza (Tópico 5)
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    """Remove artefatos comuns de extração de PDF."""
    # Remove caracteres de controle (exceto \n e \t)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)

    # Remove hifenização manual no final de linha (quebra de palavra)
    text = re.sub(r"-\n(\w)", r"\1", text)

    # Remove cabeçalhos/rodapés típicos de documentos FIA (números de página isolados)
    text = re.sub(r"(?m)^\s*\d{1,3}\s*$", "", text)

    # Remove linhas que contêm apenas sequências de pontos ou traços (linhas de tabela)
    text = re.sub(r"(?m)^[\s.\-_]{5,}$", "", text)

    # Remove caracteres não-ASCII que não são letras latinas estendidas ou símbolos matemáticos
    text = re.sub(r"[^\x20-\x7e\u00c0-\u024f\u2000-\u206f\u2100-\u214f°µ]", " ", text)

    return text


# ---------------------------------------------------------------------------
# Normalização (Tópico 6)
# ---------------------------------------------------------------------------

def normalize_text(text: str) -> str:
    """Normaliza espaços, linhas e formatação geral."""
    # Colapsa múltiplos espaços em um único
    text = re.sub(r"[ \t]+", " ", text)

    # Remove espaços no início/fim de cada linha
    text = re.sub(r"(?m)^ +| +$", "", text)

    # Colapsa mais de 2 linhas em branco consecutivas em duas
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Garante que cabeçalhos de artigo/cláusula fiquem em linha própria
    # Ex: "1.1 Definitions" → mantém, mas garante quebra antes se colado
    text = re.sub(r"([a-z\)\.])(\d+\.\d+)", r"\1\n\2", text)

    return text.strip()


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def preprocess_file(json_path: Path) -> dict:
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    processed_pages = []
    for page in data["pages"]:
        raw = page["text"]
        cleaned = clean_text(raw)
        normalized = normalize_text(cleaned)
        processed_pages.append({
            "page": page["page"],
            "text": normalized,
            "char_count_raw": page["char_count"],
            "char_count_clean": len(normalized),
        })

    return {
        "source_file": data["source_file"],
        "section": data["section"],
        "total_pages": data["total_pages"],
        "pages": processed_pages,
    }


def main():
    jsons = sorted(EXTRACTED_DIR.glob("*.json"))
    if not jsons:
        print("Nenhum JSON encontrado em extracted/. Execute 01_extract.py primeiro.")
        return

    print(f"Pré-processando {len(jsons)} arquivo(s)...\n")
    for jp in jsons:
        print(f"Processando: {jp.name} ...", end=" ")
        result = preprocess_file(jp)
        out_path = PROCESSED_DIR / jp.name
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        raw_total = sum(p["char_count_raw"] for p in result["pages"])
        clean_total = sum(p["char_count_clean"] for p in result["pages"])
        reduction = (1 - clean_total / raw_total) * 100 if raw_total else 0
        print(f"OK — redução de {reduction:.1f}% ({raw_total:,} → {clean_total:,} chars)")

    print(f"\nPré-processamento concluído. Arquivos salvos em: {PROCESSED_DIR}")


if __name__ == "__main__":
    main()
