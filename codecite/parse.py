"""Parse extracted NBC text into its clause hierarchy.

The NBC numbers everything Division > Part > Section > Subsection > Article >
Sentence, e.g. Sentence 9.8.8.3.(2) is Part 9, Section 9.8, Subsection 9.8.8,
Article 9.8.8.3, Sentence (2). Clause numbers repeat across Divisions (both
Division A and Division B have a Part 1), so every clause is tracked with its
division.

Two content kinds come out of the parse:
  * articles -- the normative text, keyed "9.8.8.3."
  * appendix notes -- explanatory notes keyed "A-9.8.8.3.", typeset inline
    ("A-9.8.8.3. Minimum Heights. Guard heights are generally based on...")

Appendices C and D (climatic tables, fire-performance ratings) are skipped:
they are numeric tables that do not survive text extraction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .extract import Page

# Part titles are fixed for the NBC 2020 (Vol 1 + Vol 2). Deriving them from
# title pages is brittle (they collide with cross-references in body text), so
# they are pinned here.
PART_TITLES = {
    ("A", 1): "Compliance",
    ("A", 2): "Objectives",
    ("A", 3): "Functional Statements",
    ("B", 1): "General",
    ("B", 2): "Farm Buildings",
    ("B", 3): "Fire Protection, Occupant Safety and Accessibility",
    ("B", 4): "Structural Design",
    ("B", 5): "Environmental Separation",
    ("B", 6): "Heating, Ventilating and Air-conditioning",
    ("B", 7): "Plumbing Services",
    ("B", 8): "Safety Measures at Construction and Demolition Sites",
    ("B", 9): "Housing and Small Buildings",
    ("C", 1): "General",
    ("C", 2): "Administrative Provisions",
}

DIVISION_RE = re.compile(r"^Division ([ABC])$")
SECTION_RE = re.compile(r"^Section (\d+\.\d+\.)\s+(\S.{0,120})$")
SUBSECTION_RE = re.compile(r"^(\d+\.\d+\.\d+\.)\s+([A-Z].{0,120})$")
ARTICLE_RE = re.compile(r"^(\d+\.\d+\.\d+\.\d+\.)\s+([A-Z].{0,180})$")
NOTE_RE = re.compile(r"^(A-\d[\d.]*(?:\(\d+\))?[\d.()and ]*?)\s+([A-Z].*)$", re.DOTALL)
# Requires "Appendix X Title..." -- a bare "Appendix C" also shows up as a
# table-cell artifact ("Appendix C, °C") in Section 9.36 and must not match.
APPENDIX_RE = re.compile(r"^Appendix [A-Z] [A-Z][a-z]")
NOTES_TO_PART_RE = re.compile(r"^Notes to Part (\d+)")
PART_HEADING_RE = re.compile(r"^Part (\d+)\s+([A-Z].{2,80})$")
DOT_LEADER_RE = re.compile(r"\.{5,}")


@dataclass
class Clause:
    kind: str  # "article" | "note"
    division: str
    clause_id: str  # "9.8.8.3." or "A-9.8.8.3."
    title: str
    part: int
    section: str = ""
    section_title: str = ""
    subsection: str = ""
    subsection_title: str = ""
    page: int = 0
    body: list[str] = field(default_factory=list)

    @property
    def text(self) -> str:
        return "\n".join(self.body).strip()


def parse_pages(pages: list[Page]) -> list[Clause]:
    clauses: list[Clause] = []
    division = ""
    part = 0
    section, section_title = "", ""
    subsection, subsection_title = "", ""
    current: Clause | None = None
    skipping_appendix = False
    # Inside a "Notes to Part N" region only A- notes are real structure;
    # article-like lines there are table artifacts and must not open clauses.
    in_notes = False

    def close():
        nonlocal current
        if current is not None and current.text:
            clauses.append(current)
        current = None

    for page in pages:
        for line in page.text.split("\n"):
            line = line.strip()
            if not line or "World Rights Reserved" in line:
                continue
            if DOT_LEADER_RE.search(line):
                continue  # table-of-contents entry

            m = DIVISION_RE.match(line)
            if m:
                division = m.group(1)
                continue
            if not division:
                continue  # front matter before Division A

            m = PART_HEADING_RE.match(line)
            if m and (division, int(m.group(1))) in PART_TITLES:
                close()
                part = int(m.group(1))
                skipping_appendix = False
                in_notes = False
                continue

            m = NOTES_TO_PART_RE.match(line)
            if m:
                close()
                part = int(m.group(1))
                skipping_appendix = False
                in_notes = True
                continue

            if APPENDIX_RE.match(line) and len(line) < 90:
                close()
                skipping_appendix = True
                continue
            if skipping_appendix:
                continue

            m = SECTION_RE.match(line) if not in_notes else None
            if m:
                close()
                section, section_title = m.group(1), m.group(2).strip()
                subsection, subsection_title = "", ""
                # Each Part ends with an "Objectives and Functional Statements"
                # section: attribution tables that re-list every article number
                # with code mappings like "[F30-OS3.1]". Indexing them would
                # shadow the real articles, so they are skipped wholesale.
                skipping_appendix = section_title.startswith(
                    "Objectives and Functional Statements"
                )
                continue

            m = ARTICLE_RE.match(line) if not in_notes else None
            if m and not m.group(2).startswith(("(", ")")):
                close()
                current = Clause(
                    kind="article",
                    division=division,
                    clause_id=m.group(1),
                    title=m.group(2).strip(),
                    part=part,
                    section=section,
                    section_title=section_title,
                    subsection=subsection,
                    subsection_title=subsection_title,
                    page=page.number,
                )
                continue

            m = SUBSECTION_RE.match(line) if not in_notes else None
            if m:
                close()
                subsection, subsection_title = m.group(1), m.group(2).strip()
                continue

            m = NOTE_RE.match(line)
            if m and line.startswith("A-"):
                close()
                note_id = m.group(1).strip()
                rest = m.group(2).strip()
                # Inline heading: title runs up to the first sentence break.
                split = re.split(r"(?<=[a-z)])\. ", rest, maxsplit=1)
                title = split[0][:110].strip().rstrip(".")
                body_start = split[1] if len(split) > 1 else ""
                current = Clause(
                    kind="note",
                    division=division,
                    clause_id=note_id,
                    title=title,
                    part=part,
                    page=page.number,
                )
                if body_start:
                    current.body.append(body_start)
                continue

            if current is not None:
                current.body.append(line)

    close()
    return clauses
