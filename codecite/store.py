"""Vector stores.

LocalStore keeps the index as two files -- chunks.jsonl (text + metadata) and
embeddings.npy -- and does exact cosine search with NumPy. At NBC scale
(thousands of chunks) exact search over a memory-mapped matrix is a few
milliseconds, so there is nothing to gain from an ANN index.

PgVectorStore is an optional Postgres/pgvector backend with the same
interface; enable it by setting CODECITE_DATABASE_URL.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np


class LocalStore:
    def __init__(self, index_dir: str = "index"):
        self.dir = Path(index_dir)
        self.chunks_path = self.dir / "chunks.jsonl"
        self.emb_path = self.dir / "embeddings.npy"

    def save(self, chunks: list[dict], embeddings: list[list[float]]) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        with open(self.chunks_path, "w", encoding="utf-8") as f:
            for c in chunks:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        mat = np.asarray(embeddings, dtype=np.float32)
        mat /= np.linalg.norm(mat, axis=1, keepdims=True)
        np.save(self.emb_path, mat)

    def load_chunks(self) -> list[dict]:
        with open(self.chunks_path, encoding="utf-8") as f:
            return [json.loads(line) for line in f]

    def search(self, query_embedding: list[float], top_k: int = 20) -> list[tuple[int, float]]:
        """Return (chunk_index, cosine_similarity) for the top_k best chunks."""
        mat = np.load(self.emb_path, mmap_mode="r")
        q = np.asarray(query_embedding, dtype=np.float32)
        q /= np.linalg.norm(q)
        sims = mat @ q
        top = np.argsort(-sims)[:top_k]
        return [(int(i), float(sims[i])) for i in top]


class PgVectorStore:
    """Same interface as LocalStore, backed by Postgres + pgvector.

    Requires `pip install codecite[pg]` and CODECITE_DATABASE_URL, e.g. a
    Supabase connection string. Kept deliberately small: one table, exact
    cosine search via the <=> operator.
    """

    def __init__(self, dsn: str | None = None, dim: int = 1536):
        import psycopg
        from pgvector.psycopg import register_vector

        self.dsn = dsn or os.environ["CODECITE_DATABASE_URL"]
        self.dim = dim
        self._psycopg = psycopg
        self._register = register_vector

    def _conn(self):
        conn = self._psycopg.connect(self.dsn)
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        self._register(conn)
        return conn

    def save(self, chunks: list[dict], embeddings: list[list[float]]) -> None:
        with self._conn() as conn:
            conn.execute("DROP TABLE IF EXISTS codecite_chunks")
            conn.execute(
                f"""CREATE TABLE codecite_chunks (
                    id integer PRIMARY KEY,
                    payload jsonb NOT NULL,
                    embedding vector({self.dim}) NOT NULL
                )"""
            )
            with conn.cursor() as cur:
                for i, (c, e) in enumerate(zip(chunks, embeddings)):
                    cur.execute(
                        "INSERT INTO codecite_chunks VALUES (%s, %s, %s)",
                        (i, json.dumps(c, ensure_ascii=False), e),
                    )
            conn.commit()

    def load_chunks(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT payload FROM codecite_chunks ORDER BY id"
            ).fetchall()
        return [r[0] for r in rows]

    def search(self, query_embedding: list[float], top_k: int = 20) -> list[tuple[int, float]]:
        with self._conn() as conn:
            rows = conn.execute(
                """SELECT id, 1 - (embedding <=> %s::vector) AS sim
                   FROM codecite_chunks ORDER BY embedding <=> %s::vector LIMIT %s""",
                (query_embedding, query_embedding, top_k),
            ).fetchall()
        return [(int(r[0]), float(r[1])) for r in rows]


def get_store(index_dir: str = "index"):
    if os.environ.get("CODECITE_DATABASE_URL"):
        return PgVectorStore()
    return LocalStore(index_dir)
