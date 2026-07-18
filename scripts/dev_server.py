"""Frontend dev server: the real API over synthetic fixtures.

    python scripts/dev_server.py [--port 8000]

Runs codecite.server.create_app with a deterministic fake Cohere client and a
tiny fixture corpus, so the web UI can be developed and demoed without an API
key or the NBC index. Retrieval is real (LocalStore cosine over keyword
vectors), rerank reorders by term overlap, and canned answers carry citation
spans with true character offsets -- the same shapes the live pipeline emits.

The fixture texts are paraphrases written for this harness, not Code text.
"""

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from codecite.store import LocalStore

# Keyword buckets double as embedding dimensions; the last dimension is a
# constant bias so no vector (or query) is ever zero-length.
KEYWORDS = ["guard", "stair", "smoke", "ceiling", "window", "deck", "exit", "basement", "bedroom", "door"]

FIXTURES = [
    ("article", "9.8.8.3.", "Height of Guards", 844, "guard deck",
     "1) Guards around landings and decks are required to reach a specified minimum height.\n"
     "2) Within dwelling units, guards must be no lower than 900 mm.\n"
     "3) Where the walking surface sits more than 1 800 mm above ground, taller guards are required."),
    ("article", "9.8.8.1.", "Required Guards", 843, "guard deck window",
     "1) A guard is required wherever a walking surface has a drop of more than 600 mm to the adjacent level."),
    ("article", "9.8.8.5.", "Openings in Guards", 845, "guard",
     "1) Openings through a guard must be small enough to prevent the passage of a 100 mm sphere."),
    ("note", "A-9.8.8.1.", "Required Guards", 1343, "guard deck",
     "Guidance on where guards are expected, including decks, landings and mezzanines."),
    ("article", "9.8.2.1.", "Stair Width", 831, "stair exit",
     "1) Required exit stairs and public stairs within dwelling units must meet a minimum clear width of 860 mm."),
    ("article", "9.8.4.1.", "Stair Height and Depth", 833, "stair",
     "1) Steps must keep rise and run within the permitted range so the stair is walkable."),
    ("article", "9.10.19.3.", "Location of Smoke Alarms", 921, "smoke bedroom",
     "1) A smoke alarm is required inside every sleeping room and in the space outside grouped sleeping rooms.\n"
     "2) At least one smoke alarm is required on every storey, including basements."),
    ("article", "9.10.19.1.", "Required Smoke Alarms", 920, "smoke bedroom",
     "1) Smoke alarms conforming to the referenced standard must be installed in every dwelling unit."),
    ("article", "9.5.3.1.", "Ceiling Heights of Rooms or Spaces", 771, "ceiling basement bedroom",
     "1) Habitable rooms must meet the ceiling heights set out in the table for their occupancy.\n"
     "2) In basements, a reduced clear height is permitted under beams and ducts."),
    ("article", "9.7.1.2.", "Egress Windows", 801, "window bedroom basement",
     "1) Bedrooms without a door to the exterior require a window openable from the inside without tools."),
]


def build_chunks() -> list[dict]:
    chunks = []
    for kind, clause_id, title, page, _, text in FIXTURES:
        prefix = "Appendix Note" if kind == "note" else "Article"
        chunks.append({
            "id": f"B-{clause_id}",
            "kind": kind,
            "division": "B",
            "clause_id": clause_id,
            "title": title,
            "part": 9,
            "section": "9.x.",
            "section_title": "Housing and Small Buildings",
            "subsection": "9.x.x.",
            "subsection_title": title,
            "page": page,
            "context": f"National Building Code of Canada 2020 [dev fixture], Division B, "
                       f"Part 9 (Housing and Small Buildings), {prefix} {clause_id.rstrip('.')} ({title})",
            "text": text,
        })
    return chunks


def vec(tags: str) -> list[float]:
    words = set(tags.split())
    return [1.0 if k in words else 0.0 for k in KEYWORDS] + [0.15]


# Canned answers as (fragment, clause_id-or-None) pairs; offsets for the
# citation spans are computed while the fragments are joined, exactly as the
# real Command citations arrive.
ANSWERS = {
    "guard": [
        ("The minimum height for a guardrail on a residential deck is ", None),
        ("900 mm", "9.8.8.3."),
        (" for decks within dwelling units. A guard is required in the first place wherever the deck surface is ", None),
        ("more than 600 mm above the adjacent level", "9.8.8.1."),
        (". Any openings through the guard must ", None),
        ("prevent the passage of a 100 mm sphere", "9.8.8.5."),
        (".", None),
    ],
    "smoke": [
        ("Yes. A smoke alarm is required ", None),
        ("inside every sleeping room", "9.10.19.3."),
        (" and in the corridor or space serving grouped bedrooms, plus ", None),
        ("at least one on every storey, including basements", "9.10.19.3."),
        (". The alarms must ", None),
        ("conform to the referenced standard", "9.10.19.1."),
        (".", None),
    ],
    "stair": [
        ("An exit stair in a house needs a ", None),
        ("minimum clear width of 860 mm", "9.8.2.1."),
        (". The steps themselves must also ", None),
        ("keep rise and run within the permitted range", "9.8.4.1."),
        (".", None),
    ],
    "ceiling": [
        ("Habitable rooms must meet the ", None),
        ("ceiling heights set out in the table for their occupancy", "9.5.3.1."),
        (", and in basements a ", None),
        ("reduced clear height is permitted under beams and ducts", "9.5.3.1."),
        (".", None),
    ],
}
DEFAULT_ANSWER = [
    ("The fixture corpus is small; based on what it holds, a guard is required wherever a surface has ", None),
    ("a drop of more than 600 mm", "9.8.8.1."),
    (". Ask about guards, stairs, smoke alarms or ceilings to exercise richer citations.", None),
]


class FakeCohere:
    """CohereClient interface over the fixtures, with believable latency."""

    def embed_query(self, text: str) -> list[float]:
        time.sleep(0.05)
        words = text.lower()
        return [1.0 if k in words else 0.0 for k in KEYWORDS] + [0.15]

    def embed_documents(self, texts):  # pragma: no cover - unused by serve
        return [vec("") for _ in texts]

    def rerank(self, query: str, documents: list[str], top_n: int):
        time.sleep(0.14)
        terms = {w for w in query.lower().split() if len(w) > 3}
        scored = []
        for i, doc in enumerate(documents):
            body = doc.lower()
            overlap = sum(1 for t in terms if t in body)
            scored.append((i, 0.35 + 0.6 * overlap / max(1, len(terms)) - 0.01 * i))
        scored.sort(key=lambda x: -x[1])
        return scored[:top_n]

    def chat_with_documents(self, message: str, documents: list[dict]):
        time.sleep(0.9)
        q = message.lower()
        script = DEFAULT_ANSWER
        for topic, fragments in ANSWERS.items():
            if topic in q:
                script = fragments
                break

        # Map clause ids to the position of their document in this request,
        # best-ranked first -- citation source ids must index into the hits.
        by_clause: dict[str, str] = {}
        for i, doc in enumerate(documents):
            title = doc["data"]["title"]
            for fx in FIXTURES:
                if f" {fx[1]} (" in title:
                    by_clause.setdefault(fx[1], str(i))

        text = ""
        citations = []
        for fragment, clause_id in script:
            start = len(text)
            text += fragment
            if clause_id and clause_id in by_clause:
                citations.append(SimpleNamespace(
                    text=fragment,
                    start=start,
                    end=start + len(fragment),
                    sources=[SimpleNamespace(id=by_clause[clause_id])],
                ))
        content = [SimpleNamespace(text=text)]
        return SimpleNamespace(message=SimpleNamespace(content=content, citations=citations))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    try:
        import uvicorn

        from codecite.server import create_app
    except ImportError:
        print("The dev server needs the [web] extra:  pip install -e .[web]", file=sys.stderr)
        return 2

    chunks = build_chunks()
    store = LocalStore(str(Path(tempfile.mkdtemp(prefix="codecite-dev-")) / "index"))
    store.save(chunks, [vec(f[4]) for f in FIXTURES])

    print(f"dev fixtures: {len(chunks)} synthetic chunks (not Code text)")
    uvicorn.run(create_app(FakeCohere(), store), host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
