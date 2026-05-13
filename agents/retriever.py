"""Agente Retriever.

Realiza busca vetorial no ChromaDB usando a query reformulada
e retorna resultados filtrados por limiar de relevância.
"""

import os
import time
from datetime import datetime, timezone
from pathlib import Path



DEFAULT_COLLECTION = "fia_2026_regulations"
DEFAULT_TOP_K = 5
DEFAULT_THRESHOLD = 0.30


def _vectorstore_path() -> Path:
    """Resolve caminho do vectorstore persistente."""
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "dados" / "vectorstore"


def _embed_query(query: str) -> list[float]:
    """Gera embedding da query usando modelo configurado no .env."""
    import ollama

    embed_model = os.getenv("EMBED_MODEL", "nomic-embed-text")
    response = ollama.embeddings(model=embed_model, prompt=query)
    return response["embedding"]


def retrieve(state: dict) -> dict:
    """Executa recuperação vetorial no ChromaDB.

    Lê: state["query_reformulada"] (fallback para state["query_original"])
    Escreve: retriever_result, trace (append)
    """
    inicio = time.time()

    query = (state.get("query_reformulada") or state.get("query_original") or "").strip()
    if not query:
        raise ValueError("State inválido: informe 'query_reformulada' ou 'query_original'.")

    threshold = float(os.getenv("RETRIEVER_THRESHOLD", str(DEFAULT_THRESHOLD)))
    top_k = int(os.getenv("RETRIEVER_TOP_K", str(DEFAULT_TOP_K)))
    collection_name = os.getenv("CHROMA_COLLECTION", DEFAULT_COLLECTION)

    vectorstore_path = _vectorstore_path()
    if not vectorstore_path.exists():
        raise FileNotFoundError(
            f"Vector store não encontrado em '{vectorstore_path}'. "
            "Execute a pipeline de ingestão antes do retriever."
        )

    import chromadb

    client = chromadb.PersistentClient(path=str(vectorstore_path))
    collection = client.get_collection(collection_name)

    query_embedding = _embed_query(query)
    raw = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    docs = raw.get("documents", [[]])[0]
    metas = raw.get("metadatas", [[]])[0]
    dists = raw.get("distances", [[]])[0]

    hits = []
    for doc, meta, dist in zip(docs, metas, dists):
        score = 1 - float(dist)
        if score >= threshold:
            hits.append({
                "content": doc,
                "score": round(score, 4),
                "metadata": meta or {},
            })

    retriever_result = {
        "query": query,
        "threshold": threshold,
        "top_k": top_k,
        "total_hits": len(hits),
        "hits": hits,
    }

    return {
        "retriever_result": retriever_result,
        "trace": state.get("trace", []) + [{
            "agente": "retriever",
            "entrada": query,
            "saida": f"{len(hits)} hits acima de {threshold}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "latencia_ms": int((time.time() - inicio) * 1000),
        }],
    }
