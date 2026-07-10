"""Integrity of the eval set against the real corpus.

Runs only when a built index is present (requires the NBC PDF + ingest);
always-on checks validate the JSONL itself.
"""

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
QUESTIONS = [
    json.loads(line)
    for line in (ROOT / "eval" / "questions.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]


def test_questions_are_well_formed():
    assert len(QUESTIONS) == 30
    assert len({q["id"] for q in QUESTIONS}) == 30
    for q in QUESTIONS:
        assert q["question"].strip().endswith("?")
        assert q["answer"].strip()
        assert q["gold"], q["id"]
        for g in q["gold"]:
            assert g[0] in "ABC" and g[1] == "-", f"bad gold id {g}"


@pytest.mark.skipif(
    not (ROOT / "index" / "chunks.jsonl").exists(),
    reason="needs a built index (run `codecite ingest` first)",
)
def test_every_gold_clause_exists_in_the_index():
    chunks = [
        json.loads(line)
        for line in (ROOT / "index" / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    ids = {c["id"] for c in chunks}
    assert len(ids) == len(chunks), "chunk ids must be unique"
    for q in QUESTIONS:
        for g in q["gold"]:
            assert any(i.startswith(g) for i in ids), f"{q['id']}: gold {g} not in index"
