"""
04_chunk.py
Divide os textos pré-processados em chunks usando LangChain RecursiveCharacterTextSplitter.
Executa testes com diferentes chunk_sizes e exibe métricas comparativas.
Salva o melhor resultado em chunks/.
"""

import json
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter

PROCESSED_DIR = Path(__file__).parent.parent / "processed"
CHUNKS_DIR = Path(__file__).parent.parent / "chunks"
CHUNKS_DIR.mkdir(exist_ok=True)

# Separadores hierárquicos para documentos regulatórios FIA
SEPARATORS = ["\n\n", "\n", ". ", " ", ""]

# Configurações a testar (Tópico 8)
CHUNK_CONFIGS = [
    {"chunk_size": 256,  "chunk_overlap": 32},
    {"chunk_size": 512,  "chunk_overlap": 64},
    {"chunk_size": 1024, "chunk_overlap": 128},
    {"chunk_size": 2048, "chunk_overlap": 256},
]

# Configuração escolhida para salvar (melhor equilíbrio para RAG)
BEST_CONFIG = {"chunk_size": 512, "chunk_overlap": 64}


def build_full_text(data: dict) -> str:
    """Concatena todas as páginas em um único texto com separador de página."""
    parts = []
    for page in data["pages"]:
        text = page["text"].strip()
        if text:
            parts.append(f"[Página {page['page']}]\n{text}")
    return "\n\n".join(parts)


def chunk_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=SEPARATORS,
        length_function=len,
    )
    return splitter.split_text(text)


def compute_metrics(chunks: list[str], chunk_size: int) -> dict:
    sizes = [len(c) for c in chunks]
    avg = sum(sizes) / len(sizes) if sizes else 0
    over_limit = sum(1 for s in sizes if s > chunk_size)
    return {
        "n_chunks": len(chunks),
        "avg_size": round(avg, 1),
        "min_size": min(sizes, default=0),
        "max_size": max(sizes, default=0),
        "over_limit": over_limit,
    }


def run_size_tests(text: str, source: str):
    """Tópico 8: avalia diferentes chunk sizes e imprime relatório."""
    print(f"\n  Testes de chunk size para: {source}")
    print(f"  {'Config':<28} {'Chunks':>7} {'Avg':>7} {'Min':>6} {'Max':>7} {'Over':>5}")
    print(f"  {'-'*65}")
    for cfg in CHUNK_CONFIGS:
        chunks = chunk_text(text, cfg["chunk_size"], cfg["chunk_overlap"])
        m = compute_metrics(chunks, cfg["chunk_size"])
        label = f"size={cfg['chunk_size']} overlap={cfg['chunk_overlap']}"
        print(f"  {label:<28} {m['n_chunks']:>7} {m['avg_size']:>7.0f} "
              f"{m['min_size']:>6} {m['max_size']:>7} {m['over_limit']:>5}")


def process_file(json_path: Path):
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    full_text = build_full_text(data)
    source = data["source_file"]
    section = data["section"]

    # Tópico 8: testes comparativos
    run_size_tests(full_text, source)

    # Tópico 7: chunking com configuração escolhida
    chunks = chunk_text(full_text, BEST_CONFIG["chunk_size"], BEST_CONFIG["chunk_overlap"])

    output = {
        "source_file": source,
        "section": section,
        "chunk_config": BEST_CONFIG,
        "total_chunks": len(chunks),
        "chunks": [
            {"id": i, "text": chunk, "char_count": len(chunk)}
            for i, chunk in enumerate(chunks)
        ],
    }

    stem = Path(source).stem
    out_path = CHUNKS_DIR / f"{stem}_chunks.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    return len(chunks), out_path


def main():
    jsons = sorted(PROCESSED_DIR.glob("*.json"))
    if not jsons:
        print("Nenhum JSON encontrado em processed/. Execute 03_preprocess.py primeiro.")
        return

    print(f"Chunking de {len(jsons)} arquivo(s)...\n")
    print(f"Configuração de produção: chunk_size={BEST_CONFIG['chunk_size']}, "
          f"overlap={BEST_CONFIG['chunk_overlap']}\n")

    total_chunks = 0
    for jp in jsons:
        n, out = process_file(jp)
        total_chunks += n
        print(f"\n  → Salvo: {out.name} ({n} chunks)")

    print(f"\nChunking concluído. Total de chunks: {total_chunks:,} | Arquivos em: {CHUNKS_DIR}")


if __name__ == "__main__":
    main()
