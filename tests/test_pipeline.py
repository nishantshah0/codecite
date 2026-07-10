"""Pipeline logic exercised offline with a fake Cohere client."""

from types import SimpleNamespace

from codecite.pipeline import answer, rerank, retrieve
from codecite.store import LocalStore

CHUNKS = [
    {"id": "B-9.8.8.3.", "kind": "article", "division": "B", "clause_id": "9.8.8.3.",
     "title": "Height of Guards", "part": 9, "section": "9.8.", "section_title": "Stairs",
     "subsection": "9.8.8.", "subsection_title": "Guards", "page": 844,
     "context": "Article 9.8.8.3 (Height of Guards)",
     "text": "1) All guards shall be not less than 1 070 mm high."},
    {"id": "B-9.8.8.5.", "kind": "article", "division": "B", "clause_id": "9.8.8.5.",
     "title": "Openings in Guards", "part": 9, "section": "9.8.", "section_title": "Stairs",
     "subsection": "9.8.8.", "subsection_title": "Guards", "page": 845,
     "context": "Article 9.8.8.5 (Openings in Guards)",
     "text": "1) Openings shall prevent passage of a 100 mm sphere."},
    {"id": "B-9.3.1.7.", "kind": "article", "division": "B", "clause_id": "9.3.1.7.",
     "title": "Concrete Mixes", "part": 9, "section": "9.3.", "section_title": "Materials",
     "subsection": "9.3.1.", "subsection_title": "Concrete", "page": 816,
     "context": "Article 9.3.1.7 (Concrete Mixes)",
     "text": "1) Water to cementing materials shall not exceed 0.70."},
]

# one-hot embeddings: queries about guards match chunk 0, etc.
EMBEDS = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]


class FakeClient:
    """Same interface as CohereClient; deterministic, no network."""

    def __init__(self, query_embedding, rerank_order=None):
        self.query_embedding = query_embedding
        self.rerank_order = rerank_order

    def embed_documents(self, texts):
        return EMBEDS[: len(texts)]

    def embed_query(self, text):
        return self.query_embedding

    def rerank(self, query, documents, top_n):
        order = self.rerank_order or list(range(len(documents)))
        return [(i, 1.0 - 0.1 * pos) for pos, i in enumerate(order[:top_n])]

    def chat_with_documents(self, message, documents):
        self.last_documents = documents
        content = [SimpleNamespace(text="Guards must be at least 1 070 mm high.")]
        citations = [SimpleNamespace(
            text="1 070 mm high",
            sources=[SimpleNamespace(id="0")],
        )]
        return SimpleNamespace(message=SimpleNamespace(content=content, citations=citations))


def make_store(tmp_path):
    store = LocalStore(str(tmp_path / "index"))
    store.save(CHUNKS, EMBEDS)
    return store


def test_retrieve_orders_by_cosine_similarity(tmp_path):
    store = make_store(tmp_path)
    client = FakeClient(query_embedding=[0.1, 0.0, 1.0])  # closest to concrete chunk
    hits = retrieve(client, store, "water cement ratio", k=3)
    assert hits[0].chunk["id"] == "B-9.3.1.7."
    assert hits[0].score >= hits[1].score >= hits[2].score


def test_rerank_reorders_candidates(tmp_path):
    store = make_store(tmp_path)
    client = FakeClient(query_embedding=[1.0, 0.05, 0.0], rerank_order=[1, 0, 2])
    hits = retrieve(client, store, "openings in guards", k=3)
    assert hits[0].chunk["id"] == "B-9.8.8.3."  # dense gets it wrong on purpose
    reranked = rerank(client, "openings in guards", hits, top_n=3)
    assert reranked[0].chunk["id"] == "B-9.8.8.5."  # rerank fixes it


def test_answer_maps_citations_back_to_clause_labels(tmp_path):
    store = make_store(tmp_path)
    client = FakeClient(query_embedding=[1.0, 0.0, 0.0])
    text, citations, hits = answer(client, store, "minimum guard height?")
    assert "1 070 mm" in text
    [(span, labels)] = citations
    assert span == "1 070 mm high"
    assert labels == ["Division B, Article 9.8.8.3. (Height of Guards), PDF p. 844"]
    # documents handed to the model include the context header
    assert "Article 9.8.8.3" in client.last_documents[0]["data"]["snippet"]


def test_answer_without_rerank_uses_dense_order(tmp_path):
    store = make_store(tmp_path)
    client = FakeClient(query_embedding=[1.0, 0.0, 0.0], rerank_order=[2, 1, 0])
    _, _, hits = answer(client, store, "guard height", use_rerank=False)
    assert hits[0].chunk["id"] == "B-9.8.8.3."
