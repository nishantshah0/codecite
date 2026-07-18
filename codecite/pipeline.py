"""Retrieval pipeline: embed -> vector search -> rerank -> grounded generation.

Retrieval is deliberately two-stage. Dense search casts a wide net
(RETRIEVE_K candidates); Rerank reads the query against each candidate's full
text and reorders them, and only the top RERANK_K reach the generator. The
eval harness measures exactly what this second stage buys.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from .chunk import clauses_to_chunks, embed_text
from .cohere_client import EMBED_BATCH
from .extract import extract_pages
from .parse import parse_pages

RETRIEVE_K = 30
RERANK_K = 8


@dataclass
class Hit:
    chunk: dict
    score: float
    # Where dense retrieval alone ranked this chunk (0-based) and with what
    # cosine similarity -- carried through Rerank so the stages can be compared.
    dense_rank: int | None = None
    dense_score: float | None = None

    @property
    def label(self) -> str:
        c = self.chunk
        kind = "Note" if c["kind"] == "note" else "Article"
        return f"Division {c['division']}, {kind} {c['clause_id']} ({c['title']}), PDF p. {c['page']}"


@dataclass
class Citation:
    """A span of the answer text mapped to the hits that support it."""

    text: str
    start: int | None
    end: int | None
    sources: list[int]  # indices into AskResult.hits


@dataclass
class AskResult:
    text: str
    citations: list[Citation]
    hits: list[Hit]
    timings: dict[str, float]  # seconds per stage: embed, search, rerank, generate
    corpus_size: int
    retrieved: int  # dense candidates actually found (min of RETRIEVE_K, corpus)


def ingest(client, store, pdf_path: str) -> int:
    pages = extract_pages(pdf_path)
    clauses = parse_pages(pages)
    chunks = clauses_to_chunks(clauses)
    print(f"parsed {len(clauses)} clauses -> {len(chunks)} chunks; embedding...", flush=True)

    # Embedding a full corpus on a trial key can die mid-run to rate limits,
    # so progress is checkpointed after every batch and resumed on rerun.
    texts = [embed_text(c) for c in chunks]
    ckpt = Path(pdf_path).parent / ".embed_checkpoint.npz"
    embeddings: list = []
    if ckpt.exists():
        data = np.load(ckpt)
        if int(data["n_chunks"]) == len(texts):
            embeddings = list(data["embeddings"])
            print(f"resuming from checkpoint: {len(embeddings)}/{len(texts)} already embedded", flush=True)
    pace = float(os.environ.get("CODECITE_EMBED_PACE", "2"))
    while len(embeddings) < len(texts):
        batch = texts[len(embeddings) : len(embeddings) + EMBED_BATCH]
        embeddings.extend(client.embed_documents(batch))
        np.savez(ckpt, embeddings=np.asarray(embeddings, dtype=np.float32), n_chunks=len(texts))
        print(f"  embedded {len(embeddings)}/{len(texts)}", flush=True)
        time.sleep(pace)

    store.save(chunks, embeddings)
    ckpt.unlink(missing_ok=True)
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


def ask(client, store, query: str, use_rerank: bool = True, chunks: list[dict] | None = None) -> AskResult:
    """Full pipeline with per-stage timings and span-level citations.

    Stages are run inline (rather than via retrieve()/rerank()) so that embed,
    search, rerank and generate can each be timed on their own -- the web UI
    shows the trace. Pass preloaded chunks to skip re-reading the index.
    """
    timings: dict[str, float] = {}
    if chunks is None:
        chunks = store.load_chunks()

    t0 = time.perf_counter()
    q = client.embed_query(query)
    timings["embed"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    dense = [
        Hit(chunks[i], score, dense_rank=rank, dense_score=score)
        for rank, (i, score) in enumerate(store.search(q, top_k=RETRIEVE_K))
    ]
    timings["search"] = time.perf_counter() - t0

    if use_rerank:
        t0 = time.perf_counter()
        docs = [embed_text(h.chunk) for h in dense]
        hits = [
            Hit(dense[i].chunk, score, dense_rank=dense[i].dense_rank, dense_score=dense[i].dense_score)
            for i, score in client.rerank(query, docs, top_n=RERANK_K)
        ]
        timings["rerank"] = time.perf_counter() - t0
    else:
        hits = dense[:RERANK_K]

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
    t0 = time.perf_counter()
    resp = client.chat_with_documents(message, documents)
    timings["generate"] = time.perf_counter() - t0

    text = "".join(part.text for part in resp.message.content if getattr(part, "text", None))
    citations = []
    for cit in resp.message.citations or []:
        sources = []
        for src in cit.sources or []:
            idx = int(src.id)
            if 0 <= idx < len(hits):
                sources.append(idx)
        citations.append(
            Citation(
                text=cit.text,
                start=getattr(cit, "start", None),
                end=getattr(cit, "end", None),
                sources=sources,
            )
        )
    return AskResult(
        text=text,
        citations=citations,
        hits=hits,
        timings=timings,
        corpus_size=len(chunks),
        retrieved=len(dense),
    )


def answer(client, store, query: str, use_rerank: bool = True):
    """CLI-shaped pipeline output: (answer_text, citations, hits).

    citations is a list of (quoted_span, [chunk labels]) pairs taken from the
    model's citation output, so every claim maps back to specific clauses.
    """
    result = ask(client, store, query, use_rerank=use_rerank)
    citations = [(c.text, [result.hits[i].label for i in c.sources]) for c in result.citations]
    return result.text, citations, result.hits
