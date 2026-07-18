"""JSON API + static host for the web UI.

    codecite serve [--index index] [--host 127.0.0.1] [--port 8000]

Two routes -- GET /api/health and POST /api/ask -- thin over pipeline.ask(),
plus the built frontend from web/dist when it exists. Requires the [web]
extra: pip install -e .[web]. The index is loaded once at startup; chunks are
immutable while serving.

No `from __future__ import annotations` here: FastAPI must evaluate the
request model annotation at runtime, and AskRequest is local to create_app.
"""

from pathlib import Path

WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"


def create_app(client, store):
    from fastapi import FastAPI, HTTPException
    from fastapi.staticfiles import StaticFiles
    from pydantic import BaseModel, Field

    from .cohere_client import CHAT_MODEL, EMBED_MODEL, RERANK_MODEL
    from .pipeline import RERANK_K, RETRIEVE_K, ask

    try:
        chunks = store.load_chunks()
    except FileNotFoundError as e:
        raise RuntimeError(
            "No index found. Run `codecite ingest` first (see README quickstart)."
        ) from e

    app = FastAPI(title="CodeCite", docs_url=None, redoc_url=None)

    class AskRequest(BaseModel):
        question: str = Field(min_length=3, max_length=500)
        use_rerank: bool = True

    models = {"embed": EMBED_MODEL, "rerank": RERANK_MODEL, "chat": CHAT_MODEL}

    @app.get("/api/health")
    def health():
        return {
            "status": "ok",
            "chunks": len(chunks),
            "backend": type(store).__name__,
            "retrieve_k": RETRIEVE_K,
            "rerank_k": RERANK_K,
            "models": models,
        }

    @app.post("/api/ask")
    def ask_route(req: AskRequest):
        try:
            r = ask(client, store, req.question, use_rerank=req.use_rerank, chunks=chunks)
        except Exception as e:  # Cohere/API failures surface as a gateway error
            raise HTTPException(status_code=502, detail=str(e)) from e
        return {
            "question": req.question,
            "use_rerank": req.use_rerank,
            "answer": r.text,
            "citations": [
                {"text": c.text, "start": c.start, "end": c.end, "sources": c.sources}
                for c in r.citations
            ],
            "hits": [
                {
                    "id": h.chunk["id"],
                    "kind": h.chunk["kind"],
                    "division": h.chunk["division"],
                    "clause_id": h.chunk["clause_id"],
                    "title": h.chunk["title"],
                    "page": h.chunk["page"],
                    "label": h.label,
                    "context": h.chunk["context"],
                    "text": h.chunk["text"],
                    "score": h.score,
                    "dense_rank": h.dense_rank,
                    "dense_score": h.dense_score,
                }
                for h in r.hits
            ],
            "timings_ms": {k: round(v * 1000, 1) for k, v in r.timings.items()},
            "corpus_size": r.corpus_size,
            "retrieved": r.retrieved,
            "models": models,
        }

    if WEB_DIST.is_dir():
        app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")

    return app
