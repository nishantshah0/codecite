"""Turn parsed clauses into retrieval chunks.

One chunk per article/note, not fixed-size windows: building-code answers
live inside a single article, and clause boundaries are the citation
boundaries, so cutting across them would break both retrieval and citations.

Every chunk gets a context header (division > part > section > subsection >
article) prepended to the embedded text. The header carries the vocabulary a
question actually uses -- a query says "guardrail height on a deck", the
sentence text says "1 070 mm high" but only the headings say "Guards" -- so
embedding header+body closes that gap.

Articles longer than MAX_CHARS are split at sentence boundaries into parts
that share the same clause_id (citations stay correct; only retrieval
granularity changes).
"""

from __future__ import annotations

from .parse import PART_TITLES, Clause

MAX_CHARS = 2800


def _context(c: Clause) -> str:
    parts = [f"National Building Code of Canada 2020, Division {c.division}"]
    title = PART_TITLES.get((c.division, c.part))
    if title:
        parts.append(f"Part {c.part} ({title})")
    if c.section:
        parts.append(f"Section {c.section.rstrip('.')} ({c.section_title})")
    if c.subsection:
        parts.append(f"Subsection {c.subsection.rstrip('.')} ({c.subsection_title})")
    if c.kind == "note":
        parts.append(f"Appendix Note {c.clause_id} ({c.title})")
    else:
        parts.append(f"Article {c.clause_id.rstrip('.')} ({c.title})")
    return ", ".join(parts)


def _split_body(body_lines: list[str]) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    size = 0
    for line in body_lines:
        if buf and size + len(line) > MAX_CHARS:
            parts.append("\n".join(buf))
            buf, size = [], 0
        buf.append(line)
        size += len(line) + 1
    if buf:
        parts.append("\n".join(buf))
    return parts


def clauses_to_chunks(clauses: list[Clause]) -> list[dict]:
    chunks: list[dict] = []
    for c in clauses:
        context = _context(c)
        pieces = _split_body(c.body)
        for i, piece in enumerate(pieces):
            suffix = f"#{i + 1}" if len(pieces) > 1 else ""
            chunks.append(
                {
                    "id": f"{c.division}-{c.clause_id}{suffix}",
                    "kind": c.kind,
                    "division": c.division,
                    "clause_id": c.clause_id,
                    "title": c.title,
                    "part": c.part,
                    "section": c.section,
                    "section_title": c.section_title,
                    "subsection": c.subsection,
                    "subsection_title": c.subsection_title,
                    "page": c.page,
                    "context": context,
                    "text": piece,
                }
            )
    return chunks


def embed_text(chunk: dict) -> str:
    return chunk["context"] + "\n" + chunk["text"]
