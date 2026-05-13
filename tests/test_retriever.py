"""Testes do Agente Retriever."""

from unittest.mock import patch

from agents.retriever import retrieve


class _FakeCollection:
    def __init__(self, query_result):
        self._query_result = query_result

    def query(self, **_kwargs):
        return self._query_result


class _FakeClient:
    def __init__(self, query_result):
        self._query_result = query_result

    def get_collection(self, _name):
        return _FakeCollection(self._query_result)


@patch("agents.retriever.Path.exists", return_value=True)
def test_retrieve_estrutura_saida(_mock_exists):
    query_result = {
        "documents": [["doc A", "doc B"]],
        "metadatas": [[{"section": "A"}, {"section": "B"}]],
        "distances": [[0.1, 0.4]],  # scores: 0.9, 0.6
    }
    with patch("builtins.__import__") as mock_import, patch("agents.retriever.os.getenv") as getenv:
        real_import = __import__

        def _fake_import(name, *args, **kwargs):
            if name == "chromadb":
                class _FakeChromadb:
                    @staticmethod
                    def PersistentClient(path):
                        _ = path
                        return _FakeClient(query_result)
                return _FakeChromadb
            if name == "ollama":
                class _FakeOllama:
                    @staticmethod
                    def embeddings(model, prompt):
                        _ = model
                        _ = prompt
                        return {"embedding": [0.01, 0.02, 0.03]}
                return _FakeOllama
            return real_import(name, *args, **kwargs)

        mock_import.side_effect = _fake_import
        getenv.side_effect = lambda k, d=None: {
            "RETRIEVER_THRESHOLD": "0.5",
            "RETRIEVER_TOP_K": "5",
            "CHROMA_COLLECTION": "fia_2026_regulations",
            "EMBED_MODEL": "nomic-embed-text",
        }.get(k, d)

        result = retrieve({"query_reformulada": "DRS rules"})

    assert "retriever_result" in result
    rr = result["retriever_result"]
    assert rr["query"] == "DRS rules"
    assert rr["threshold"] == 0.5
    assert rr["top_k"] == 5
    assert rr["total_hits"] == 2
    assert len(rr["hits"]) == 2
    assert rr["hits"][0]["content"] == "doc A"
    assert rr["hits"][0]["score"] == 0.9

    assert len(result["trace"]) == 1
    trace = result["trace"][0]
    assert trace["agente"] == "retriever"
    assert trace["entrada"] == "DRS rules"
    assert "hits acima de" in trace["saida"]


@patch("agents.retriever.Path.exists", return_value=True)
def test_retrieve_aplica_threshold(_mock_exists):
    query_result = {
        "documents": [["doc A", "doc B"]],
        "metadatas": [[{"section": "A"}, {"section": "B"}]],
        "distances": [[0.2, 0.8]],  # scores: 0.8, 0.2
    }
    with patch("builtins.__import__") as mock_import, patch("agents.retriever.os.getenv") as getenv:
        real_import = __import__

        def _fake_import(name, *args, **kwargs):
            if name == "chromadb":
                class _FakeChromadb:
                    @staticmethod
                    def PersistentClient(path):
                        _ = path
                        return _FakeClient(query_result)
                return _FakeChromadb
            if name == "ollama":
                class _FakeOllama:
                    @staticmethod
                    def embeddings(model, prompt):
                        _ = model
                        _ = prompt
                        return {"embedding": [0.11, 0.22]}
                return _FakeOllama
            return real_import(name, *args, **kwargs)

        mock_import.side_effect = _fake_import
        getenv.side_effect = lambda k, d=None: {
            "RETRIEVER_THRESHOLD": "0.7",
            "RETRIEVER_TOP_K": "5",
        }.get(k, d)

        result = retrieve({"query_original": "engine regulations"})

    rr = result["retriever_result"]
    assert rr["total_hits"] == 1
    assert len(rr["hits"]) == 1
    assert rr["hits"][0]["content"] == "doc A"
    assert rr["hits"][0]["score"] == 0.8


@patch("agents.retriever.Path.exists", return_value=True)
def test_retrieve_appenda_trace_existente(_mock_exists):
    query_result = {
        "documents": [["doc X"]],
        "metadatas": [[{"section": "X"}]],
        "distances": [[0.3]],  # score: 0.7
    }
    trace_anterior = [{
        "agente": "reformulator",
        "entrada": "pt query",
        "saida": "en query",
        "timestamp": "2026-01-01T00:00:00+00:00",
        "latencia_ms": 12,
    }]

    with patch("builtins.__import__") as mock_import, patch("agents.retriever.os.getenv") as getenv:
        real_import = __import__

        def _fake_import(name, *args, **kwargs):
            if name == "chromadb":
                class _FakeChromadb:
                    @staticmethod
                    def PersistentClient(path):
                        _ = path
                        return _FakeClient(query_result)
                return _FakeChromadb
            if name == "ollama":
                class _FakeOllama:
                    @staticmethod
                    def embeddings(model, prompt):
                        _ = model
                        _ = prompt
                        return {"embedding": [0.5, 0.6]}
                return _FakeOllama
            return real_import(name, *args, **kwargs)

        mock_import.side_effect = _fake_import
        getenv.side_effect = lambda k, d=None: {
            "RETRIEVER_THRESHOLD": "0.1",
            "RETRIEVER_TOP_K": "3",
        }.get(k, d)

        result = retrieve({
            "query_reformulada": "en query",
            "trace": trace_anterior,
        })

    assert len(result["trace"]) == 2
    assert result["trace"][0]["agente"] == "reformulator"
    assert result["trace"][1]["agente"] == "retriever"
