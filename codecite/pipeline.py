"""Retrieval pipeline: embed -> vector search -> rerank -> grounded generation.

Retrieval is deliberately two-stage. Dense search casts a wide net
(RETRIEVE_K candidates); Rerank reads the query against each candidate's full
text and reorders them, and only the top RERANK_K reach the generator. The
eval harness measures exactly what this second stage buys.
"""

from __future__ import annotations

from dataclasses import dataclass

from .chunk import clauses_to_chunks, embed_text
from .extract import extract_pages
from .parse import parse_pages

RETRIEVE_K = 30
RERANK_K = 8


@dataclass
class Hit:
    chunk: dict
    score: float

    @property
    def label(self) -> str:
        c = self.chunk
        kind = "Note" if c["kind"] == "note" else "Article"
        return f"Division {c['division']}, {kind} {c['clause_id']} ({c['title']}), PDF p. {c['page']}"


def ingest(client, store, pdf_path: str) -> int:
    pages = extract_pages(pdf_path)
    clauses = parse_pages(pages)
    chunks = clauses_to_chunks(clauses)
    print(f"parsed {len(clauses)} clauses -> {len(chunks)} chunks; embedding...")
    embeddings = client.embed_documents([embed_text(c) for c in chunks])
    store.save(chunks, embeddings)
    return len(chunks)


def retrieve(client, store, query: str, k: int = RETRIEVE_K, chunks: list[dict] | None = None) -> list[Hit]:
    """Dense retrieval only (first stage)."""
    if chunks is None:
        chunks = store.load_chunks()
    q = client.embed_query(query)
    return [Hit(chunks[i], score) for i, score in store.search(q, top_k=k)]


def rerank(client, query: str, hits: list[Hit], top_n: int = RERANK_K) -> list[Hit]:
    """Second stage: rerank dense candidates by full-text relevance."""
    docs = [embed_text(h.chunk) for h in hits]
    ranked = client.rerank(query, docs, top_n=top_n)
    return [Hit(hits[i].chunk, score) for i, score in ranked]


def answer(client, store, query: str, use_rerank: bool = True):
    """Full pipeline. Returns (answer_text, citations, hits).

    citations is a list of (quoted_span, [chunk labels]) pairs taken from the
    model's citation output, so every claim maps back to specific clauses.
    """
    hits = retrieve(client, store, query)
    hits = rerank(client, query, hits) if use_rerank else hits[:RERANK_K]

    documents = [
        {
            "id": str(i),
            "data": {
                "title": h.label,
                "snippet": h.chunk["context"] + "\n" + h.chunk["text"],
            },
        }
        for i, h in enumerate(hits)
    ]
    message = (
        "You are a building-code assistant. Answer the question using only the "
        "provided National Building Code of Canada 2020 excerpts. Cite the "
        "specific Article or Sentence numbers that support each statement "
        "(e.g. 'Article 9.8.8.3.' or 'Sentence 9.8.8.3.(2)'). Quantities must "
        "be quoted exactly as written in the Code. If the excerpts do not "
        f"answer the question, say so.\n\nQuestion: {query}"
    )
    resp = client.chat_with_documents(message, documents)

    text = "".join(part.text for part in resp.message.content if getattr(part, "text", None))
    citations = []
    for cit in resp.message.citations or []:
        labels = []
        for src in cit.sources or []:
            idx = int(src.id)
            if 0 <= idx < len(hits):
                labels.append(hits[idx].label)
        citations.append((cit.text, labels))
    return text, citations, hits
