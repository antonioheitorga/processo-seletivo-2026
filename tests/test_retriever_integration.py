"""Testes de integração do Agente Retriever com ChromaDB/Ollama reais."""

import os
import uuid
from pathlib import Path

import chromadb
import ollama
import pytest

from agents.retriever import retrieve


@pytest.mark.integration
def test_retriever_integracao_chroma_ollama_real(monkeypatch):
    """Valida retrieval real: embed -> busca vetorial -> filtro por threshold."""
    project_root = Path(__file__).resolve().parents[1]
    vectorstore_path = project_root / "dados" / "vectorstore"
    vectorstore_path.mkdir(parents=True, exist_ok=True)

    collection_name = f"test_retriever_{uuid.uuid4().hex[:8]}"
    client = chromadb.PersistentClient(path=str(vectorstore_path))
    collection = client.get_or_create_collection(collection_name)

    query = "What is the minimum mass of the Formula 1 car in 2026?"
    emb = ollama.embed(
        model=os.getenv("EMBED_MODEL", "nomic-embed-text"),
        input=query,
    )["embeddings"][0]

    collection.add(
        ids=["id_1"],
        embeddings=[emb],
        documents=["The minimum mass is defined in section C technical regulations."],
        metadatas=[{"source_file": "dummy.pdf", "section": "technical", "chunk_id": 1}],
    )

    monkeypatch.setenv("CHROMA_COLLECTION", collection_name)
    monkeypatch.setenv("RETRIEVER_TOP_K", "3")
    monkeypatch.setenv("RETRIEVER_THRESHOLD", "0.0")

    result = retrieve({"query_reformulada": query, "trace": []})

    assert "retriever_result" in result
    rr = result["retriever_result"]
    assert isinstance(rr, dict)
    assert "hits" in rr
    assert isinstance(rr["hits"], list)
    # Em ambiente real, a distância pode vir >1 e o score (1-dist) ficar negativo;
    # o retriever filtra por threshold, podendo resultar em 0 hits mesmo com item indexado.
    assert "best_score" in rr
    assert isinstance(rr["best_score"], float)
    assert "fallback_to_web" in rr
    assert isinstance(rr["fallback_to_web"], bool)
    assert "confidence_warning" in rr
    assert "total_hits" in rr
    assert rr["total_hits"] >= 0

    assert result["trace"][-1]["agente"] == "retriever"

    client.delete_collection(collection_name)


@pytest.mark.integration
def test_retriever_falha_quando_vectorstore_inexistente(monkeypatch):
    """Força erro de infraestrutura ao apontar vectorstore para caminho inexistente."""
    monkeypatch.setenv("CHROMA_COLLECTION", f"missing_{uuid.uuid4().hex[:8]}")

    with pytest.raises(Exception) as exc:
        retrieve({"query_original": "test"})
    assert "does not exist" in str(exc.value)


@pytest.mark.integration
@pytest.mark.timeout(20)
def test_retriever_carga_basica_multiplas_consultas(monkeypatch):
    """Teste simples de carga: várias consultas consecutivas sem erro."""
    project_root = Path(__file__).resolve().parents[1]
    vectorstore_path = project_root / "dados" / "vectorstore"
    vectorstore_path.mkdir(parents=True, exist_ok=True)

    collection_name = f"test_load_{uuid.uuid4().hex[:8]}"
    client = chromadb.PersistentClient(path=str(vectorstore_path))
    collection = client.get_or_create_collection(collection_name)

    base_texts = [
        "Aerodynamics rules define wing dimensions.",
        "Power unit regulations cover energy recovery systems.",
        "Sporting regulations define race weekend format.",
    ]

    embeddings = [
        ollama.embed(
            model=os.getenv("EMBED_MODEL", "nomic-embed-text"),
            input=txt,
        )["embeddings"][0]
        for txt in base_texts
    ]

    collection.add(
        ids=[f"id_{i}" for i in range(len(base_texts))],
        embeddings=embeddings,
        documents=base_texts,
        metadatas=[{"section": "test", "chunk_id": i} for i in range(len(base_texts))],
    )

    monkeypatch.setenv("CHROMA_COLLECTION", collection_name)
    monkeypatch.setenv("RETRIEVER_TOP_K", "2")
    monkeypatch.setenv("RETRIEVER_THRESHOLD", "0.0")

    for _ in range(10):
        out = retrieve({"query_original": "wing dimensions rules"})
        assert "retriever_result" in out
        assert isinstance(out["retriever_result"], dict)
        assert "hits" in out["retriever_result"]
        assert isinstance(out["retriever_result"]["hits"], list)
        assert "best_score" in out["retriever_result"]
        assert isinstance(out["retriever_result"]["best_score"], float)
        assert "fallback_to_web" in out["retriever_result"]
        assert isinstance(out["retriever_result"]["fallback_to_web"], bool)

    client.delete_collection(collection_name)
