"""Retrieval eval: does Rerank earn its latency?

For each labeled question the same 30 dense candidates are scored two ways --
in raw embedding-similarity order, and after Cohere Rerank reorders them.
Both orderings are compared against the hand-labeled gold clause, so the
delta is attributable to Rerank alone (same candidate pool, same k).

Metrics: hit@k (gold clause in top k) and MRR (mean reciprocal rank of the
first gold hit, 0 when the gold clause is not in the candidate pool at all).

Usage:  python eval/run_eval.py [--index index] [--out eval/results.md]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codecite.cohere_client import CohereClient
from codecite.pipeline import rerank, retrieve
from codecite.store import get_store

K_VALUES = (1, 3, 5)
POOL = 30


def matches_gold(chunk_id: str, gold: list[str]) -> bool:
    return any(chunk_id.startswith(g) for g in gold)


def first_gold_rank(hits, gold) -> int | None:
    """1-based rank of the first gold chunk, or None if absent."""
    for i, h in enumerate(hits):
        if matches_gold(h.chunk["id"], gold):
            return i + 1
    return None


def summarize(ranks: list[int | None]) -> dict:
    n = len(ranks)
    out = {f"hit@{k}": sum(1 for r in ranks if r and r <= k) / n for k in K_VALUES}
    out["mrr"] = sum(1 / r for r in ranks if r) / n
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default="index")
    ap.add_argument("--out", default="eval/results.md")
    args = ap.parse_args()

    questions = [
        json.loads(line)
        for line in Path(__file__).with_name("questions.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    client = CohereClient()
    store = get_store(args.index)
    chunks = store.load_chunks()

    dense_ranks: list[int | None] = []
    rerank_ranks: list[int | None] = []
    rows = []
    for q in questions:
        hits = retrieve(client, store, q["question"], k=POOL, chunks=chunks)
        reranked = rerank(client, q["question"], hits, top_n=POOL)
        dr = first_gold_rank(hits, q["gold"])
        rr = first_gold_rank(reranked, q["gold"])
        dense_ranks.append(dr)
        rerank_ranks.append(rr)
        rows.append((q["id"], q["gold"][0], dr, rr))
        print(f"{q['id']}  dense rank: {dr or '-':>2}  reranked: {rr or '-':>2}  {q['question'][:60]}")

    dense = summarize(dense_ranks)
    rr = summarize(rerank_ranks)

    lines = [
        "# Retrieval eval results",
        "",
        f"{len(questions)} hand-labeled questions; {POOL} dense candidates per question; "
        "identical candidate pool with and without Rerank.",
        "",
        "| Metric | Embed only | Embed + Rerank |",
        "|---|---|---|",
    ]
    for k in K_VALUES:
        lines.append(f"| hit@{k} | {dense[f'hit@{k}']:.1%} | {rr[f'hit@{k}']:.1%} |")
    lines.append(f"| MRR | {dense['mrr']:.3f} | {rr['mrr']:.3f} |")
    lines += [
        "",
        "## Per-question ranks (rank of gold clause, 1 = best)",
        "",
        "| Question | Gold clause | Dense rank | Reranked rank |",
        "|---|---|---|---|",
    ]
    for qid, gold, dr, r in rows:
        lines.append(f"| {qid} | {gold} | {dr or 'miss'} | {r or 'miss'} |")
    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\nSummary (dense -> reranked):")
    for k in K_VALUES:
        print(f"  hit@{k}: {dense[f'hit@{k}']:.1%} -> {rr[f'hit@{k}']:.1%}")
    print(f"  MRR:   {dense['mrr']:.3f} -> {rr['mrr']:.3f}")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
