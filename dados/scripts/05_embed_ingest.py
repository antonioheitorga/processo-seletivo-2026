"""
05_embed_ingest.py
Gera embeddings dos chunks com Ollama (nomic-embed-text)
e indexa no ChromaDB com metadados (fonte, seção, chunk_id).

Uso:
    python3 scripts/05_embed_ingest.py

Pré-requisitos:
    - Ollama rodando localmente com nomic-embed-text disponível
    - Chunks gerados em chunks/ (rodar 04_chunk.py antes)
"""

import json
import time
from pathlib import Path

import chromadb
import ollama

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
CHUNKS_DIR   = Path(__file__).parent.parent / "chunks"
VECTORSTORE  = Path(__file__).parent.parent / "vectorstore"
COLLECTION   = "fia_2026_regulations"
EMBED_MODEL  = "nomic-embed-text"
BATCH_SIZE   = 32   # chunks por chamada ao Ollama
MIN_CHARS    = 30   # ignora chunks muito curtos (marcadores de página)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_chunks(json_path: Path) -> list[dict]:
    """Carrega e filtra chunks com conteúdo suficiente."""
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    source   = data["source_file"]
    section  = data["section"]
    filtered = [
        {
            "uid":     f"{json_path.stem}_{c['id']}",
            "text":    c["text"],
            "metadata": {
                "source_file": source,
                "section":     section,
                "chunk_id":    c["id"],
                "char_count":  c["char_count"],
            },
        }
        for c in data["chunks"]
        if c["char_count"] >= MIN_CHARS
    ]
    return filtered


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Gera embeddings para um lote de textos via Ollama."""
    response = ollama.embed(model=EMBED_MODEL, input=texts)
    return response["embeddings"]


def ingest_to_chroma(collection, chunks: list[dict]) -> int:
    """Ingere chunks no ChromaDB em batches. Retorna total inserido."""
    inserted = 0
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i : i + BATCH_SIZE]
        texts     = [c["text"]     for c in batch]
        ids       = [c["uid"]      for c in batch]
        metadatas = [c["metadata"] for c in batch]

        embeddings = embed_batch(texts)

        collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        inserted += len(batch)

    return inserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Verifica conexão com Ollama
    try:
        models = [m.model for m in ollama.list().models]
        if EMBED_MODEL not in models and f"{EMBED_MODEL}:latest" not in models:
            print(f"ERRO: modelo '{EMBED_MODEL}' não encontrado no Ollama.")
            print(f"Execute: ollama pull {EMBED_MODEL}")
            return
    except Exception as e:
        print(f"ERRO: não foi possível conectar ao Ollama — {e}")
        print("Verifique se o Ollama está rodando: ollama serve")
        return

    # Inicializa ChromaDB persistente
    VECTORSTORE.mkdir(exist_ok=True)
    client = chromadb.PersistentClient(path=str(VECTORSTORE))

    # Recria a collection se já existir (re-ingestão limpa)
    existing = [c.name for c in client.list_collections()]
    if COLLECTION in existing:
        print(f"Collection '{COLLECTION}' existente encontrada — removendo para re-ingestão limpa.")
        client.delete_collection(COLLECTION)

    collection = client.create_collection(
        name=COLLECTION,
        metadata={"hnsw:space": "cosine"},
    )

    # Processa cada arquivo de chunks
    chunk_files = sorted(CHUNKS_DIR.glob("*_chunks.json"))
    if not chunk_files:
        print("Nenhum arquivo de chunks encontrado. Execute 04_chunk.py primeiro.")
        return

    print(f"Modelo de embedding : {EMBED_MODEL}")
    print(f"Vector store        : {VECTORSTORE}")
    print(f"Collection          : {COLLECTION}")
    print(f"Batch size          : {BATCH_SIZE}")
    print(f"Arquivos de chunks  : {len(chunk_files)}\n")

    total_inserted = 0
    start = time.time()

    for chunk_file in chunk_files:
        chunks = load_chunks(chunk_file)
        section = chunks[0]["metadata"]["section"] if chunks else "?"
        print(f"Ingerindo [{section}] — {len(chunks)} chunks válidos ...", end=" ", flush=True)

        t0 = time.time()
        n = ingest_to_chroma(collection, chunks)
        elapsed = time.time() - t0

        total_inserted += n
        print(f"OK ({n} inseridos, {elapsed:.1f}s)")

    total_time = time.time() - start
    final_count = collection.count()

    print(f"\n{'='*55}")
    print(f"Ingestão concluída em {total_time:.1f}s")
    print(f"Total inserido      : {total_inserted:,} chunks")
    print(f"Total no ChromaDB   : {final_count:,} documentos")
    print(f"Vector store em     : {VECTORSTORE}")
    print(f"{'='*55}")


if __name__ == "__main__":
    main()
