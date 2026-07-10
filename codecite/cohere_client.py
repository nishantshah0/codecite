"""Thin wrapper around the Cohere SDK.

Centralizes model names, batching, and retry/backoff so the rest of the
pipeline never touches the SDK directly. Tests inject a fake with the same
interface.
"""

from __future__ import annotations

import os
import time

EMBED_MODEL = os.environ.get("CODECITE_EMBED_MODEL", "embed-v4.0")
RERANK_MODEL = os.environ.get("CODECITE_RERANK_MODEL", "rerank-v3.5")
CHAT_MODEL = os.environ.get("CODECITE_CHAT_MODEL", "command-a-03-2025")

# Cohere's embed endpoint accepts at most 96 texts per call. Trial keys with
# little remaining token-per-minute allowance may only accept smaller batches;
# tune with CODECITE_EMBED_BATCH (ingest resumes from its checkpoint).
EMBED_BATCH = min(96, int(os.environ.get("CODECITE_EMBED_BATCH", "96")))


class CohereClient:
    def __init__(self, api_key: str | None = None):
        import cohere

        key = api_key or os.environ.get("COHERE_API_KEY") or os.environ.get("CO_API_KEY")
        if not key:
            raise RuntimeError(
                "COHERE_API_KEY is not set. Get a free trial key at "
                "https://dashboard.cohere.com/api-keys and run:  "
                'setx COHERE_API_KEY "your-key"  (then open a new terminal)'
            )
        self._co = cohere.ClientV2(api_key=key)

    def _with_retry(self, fn, *args, **kwargs):
        """Retry on rate limits -- trial keys throttle bursts, sometimes with
        long penalty windows, so waits stretch to minutes before giving up."""
        delay = 10.0
        for attempt in range(10):
            try:
                return fn(*args, **kwargs)
            except Exception as e:  # SDK raises TooManyRequestsError et al.
                status = getattr(e, "status_code", None)
                if status == 429 or "429" in str(e):
                    print(f"  rate-limited (attempt {attempt + 1}/10), waiting {delay:.0f}s...", flush=True)
                    time.sleep(delay)
                    delay = min(delay * 2, 180)
                    continue
                raise
        raise RuntimeError("Cohere API kept rate-limiting after 10 retries")

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), EMBED_BATCH):
            batch = texts[i : i + EMBED_BATCH]
            resp = self._with_retry(
                self._co.embed,
                texts=batch,
                model=EMBED_MODEL,
                input_type="search_document",
                embedding_types=["float"],
            )
            out.extend(resp.embeddings.float_)
        return out

    def embed_query(self, text: str) -> list[float]:
        resp = self._with_retry(
            self._co.embed,
            texts=[text],
            model=EMBED_MODEL,
            input_type="search_query",
            embedding_types=["float"],
        )
        return resp.embeddings.float_[0]

    def rerank(self, query: str, documents: list[str], top_n: int) -> list[tuple[int, float]]:
        """Return (original_index, relevance_score) sorted by score, best first."""
        resp = self._with_retry(
            self._co.rerank,
            query=query,
            documents=documents,
            model=RERANK_MODEL,
            top_n=top_n,
        )
        return [(r.index, r.relevance_score) for r in resp.results]

    def chat_with_documents(self, message: str, documents: list[dict]):
        """Grounded generation. Each document dict needs an "id" plus data fields.

        Returns the SDK response; response.message.content[].text carries the
        answer and response.message.citations maps spans to document ids.
        """
        return self._with_retry(
            self._co.chat,
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": message}],
            documents=documents,
        )
