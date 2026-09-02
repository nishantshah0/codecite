"""Snapshot the fixture API as static JSON for the GitHub Pages demo.

    python scripts/export_demo.py [--out web/public/demo]

GitHub Pages hosts static files only, so the deployed UI cannot call
`codecite serve`. This script runs the same fixture app as dev_server.py
(fake Cohere client, synthetic corpus) through FastAPI's test client and writes
its responses to disk:

    demo/health.json
    demo/ask/<topic>-rerank.json
    demo/ask/<topic>-dense.json

The UI built with VITE_DEMO=1 reads these instead of /api/*. Each topic
matches the keyword the fake chat client keys its canned answer on, so a
question about guards gets the guards snapshot, exactly as the dev server
would answer it. Requires the [web,dev] extras.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from dev_server import FIXTURES, FakeCohere, build_chunks, vec  # noqa: E402

from codecite.store import LocalStore  # noqa: E402

# One representative question per canned-answer topic; the ask panel's example
# chips use the same phrasings so the demo answers them verbatim.
QUESTIONS = {
    "guard": "What is the minimum height for a guardrail on a residential deck?",
    "smoke": "Do I need a smoke alarm in every bedroom?",
    "stair": "How wide does an exit stair in a house need to be?",
    "ceiling": "What is the minimum ceiling height in a basement?",
    # No topic keyword: exercises the fallback answer.
    "default": "Does a bedroom window need to open from the inside?",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default=str(ROOT / "web" / "public" / "demo"))
    args = parser.parse_args()

    try:
        from fastapi.testclient import TestClient

        from codecite.server import create_app
    except ImportError:
        print("export_demo needs the [web,dev] extras:  pip install -e .[web,dev]", file=sys.stderr)
        return 2

    store = LocalStore(str(Path(tempfile.mkdtemp(prefix="codecite-demo-")) / "index"))
    store.save(build_chunks(), [vec(f[4]) for f in FIXTURES])
    api = TestClient(create_app(FakeCohere(), store))

    out = Path(args.out)
    (out / "ask").mkdir(parents=True, exist_ok=True)

    health = api.get("/api/health")
    health.raise_for_status()
    (out / "health.json").write_text(json.dumps(health.json(), indent=2) + "\n")

    for topic, question in QUESTIONS.items():
        for mode, use_rerank in (("rerank", True), ("dense", False)):
            resp = api.post("/api/ask", json={"question": question, "use_rerank": use_rerank})
            resp.raise_for_status()
            body = resp.json()
            assert body["answer"], f"empty answer for {topic}/{mode}"
            for cit in body["citations"]:
                assert body["answer"][cit["start"] : cit["end"]] == cit["text"]
            (out / "ask" / f"{topic}-{mode}.json").write_text(json.dumps(body, indent=2) + "\n")

    n = 1 + 2 * len(QUESTIONS)
    print(f"wrote {n} demo snapshots to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
