"""Command-line interface.

    codecite ingest [--pdf data/nbc2020.pdf] [--index index]
    codecite ask "minimum guardrail height for a deck?" [--no-rerank]
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="codecite", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="parse, chunk and embed the NBC PDF")
    p_ingest.add_argument("--pdf", default="data/nbc2020.pdf")
    p_ingest.add_argument("--index", default="index")

    p_ask = sub.add_parser("ask", help="ask a question against the index")
    p_ask.add_argument("question")
    p_ask.add_argument("--index", default="index")
    p_ask.add_argument("--no-rerank", action="store_true", help="skip the Rerank stage")
    p_ask.add_argument("--show-hits", action="store_true", help="print retrieved chunks")

    args = parser.parse_args(argv)

    from .cohere_client import CohereClient
    from .store import get_store

    try:
        client = CohereClient()
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 2
    store = get_store(args.index)

    if args.command == "ingest":
        from .pipeline import ingest

        n = ingest(client, store, args.pdf)
        print(f"indexed {n} chunks")
        return 0

    from .pipeline import answer

    text, citations, hits = answer(client, store, args.question, use_rerank=not args.no_rerank)
    print(text)
    if citations:
        print("\n--- Citations ---")
        seen = set()
        for span, labels in citations:
            for label in labels:
                if label not in seen:
                    seen.add(label)
                    print(f"  {label}")
    if args.show_hits:
        print("\n--- Retrieved chunks ---")
        for h in hits:
            print(f"  {h.score:.3f}  {h.label}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
