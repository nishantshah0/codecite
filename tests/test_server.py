"""API surface exercised offline with the fake Cohere client.

Skipped when the [web] extra is not installed.
"""

from types import SimpleNamespace

import pytest

from test_pipeline import CHUNKS, EMBEDS, FakeClient

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from codecite.server import create_app  # noqa: E402
from codecite.store import LocalStore  # noqa: E402


class FakeClientWithSpans(FakeClient):
    """Citations carry character offsets, as the real SDK's do."""

    ANSWER = "Guards must be at least 1 070 mm high."

    def chat_with_documents(self, message, documents):
        self.last_documents = documents
        span = "1 070 mm high"
        start = self.ANSWER.index(span)
        content = [SimpleNamespace(text=self.ANSWER)]
        citations = [SimpleNamespace(
            text=span,
            start=start,
            end=start + len(span),
            sources=[SimpleNamespace(id="0")],
        )]
        return SimpleNamespace(message=SimpleNamespace(content=content, citations=citations))


def make_client(tmp_path, query_embedding=(1.0, 0.0, 0.0)):
    store = LocalStore(str(tmp_path / "index"))
    store.save(CHUNKS, EMBEDS)
    app = create_app(FakeClientWithSpans(query_embedding=list(query_embedding)), store)
    return TestClient(app)


def test_health_reports_index_and_models(tmp_path):
    api = make_client(tmp_path)
    body = api.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["chunks"] == len(CHUNKS)
    assert set(body["models"]) == {"embed", "rerank", "chat"}


def test_ask_returns_answer_citations_and_hits(tmp_path):
    api = make_client(tmp_path)
    resp = api.post("/api/ask", json={"question": "minimum guard height?"})
    assert resp.status_code == 200
    body = resp.json()

    assert "1 070 mm" in body["answer"]
    [cit] = body["citations"]
    assert body["answer"][cit["start"] : cit["end"]] == cit["text"]
    assert cit["sources"] == [0]

    top = body["hits"][0]
    assert top["clause_id"] == "9.8.8.3."
    assert top["dense_rank"] == 0 and top["dense_score"] is not None
    assert "Height of Guards" in top["label"]

    assert {"embed", "search", "rerank", "generate"} <= set(body["timings_ms"])
    assert body["corpus_size"] == len(CHUNKS)
    assert body["retrieved"] == len(CHUNKS)  # corpus smaller than RETRIEVE_K


def test_ask_without_rerank_keeps_dense_order_and_skips_stage(tmp_path):
    api = make_client(tmp_path)
    body = api.post("/api/ask", json={"question": "guard height?", "use_rerank": False}).json()
    assert [h["dense_rank"] for h in body["hits"]] == list(range(len(body["hits"])))
    assert "rerank" not in body["timings_ms"]


def test_ask_rejects_blank_question(tmp_path):
    api = make_client(tmp_path)
    assert api.post("/api/ask", json={"question": ""}).status_code == 422


def test_missing_index_fails_at_startup(tmp_path):
    with pytest.raises(RuntimeError, match="codecite ingest"):
        create_app(FakeClientWithSpans(query_embedding=[1.0, 0.0, 0.0]), LocalStore(str(tmp_path / "empty")))
