"""PDF text extraction for the NBC 2020.

The NBC is typeset in two columns. Naive extraction interleaves the columns
line by line, which destroys clause boundaries, so we pull text blocks with
their coordinates, assign each block to a column by its x-position, and read
left column top-to-bottom, then right column.

Headers and footers (page numbers, "National Building Code of Canada 2020")
sit in the top/bottom margins and are dropped by a y-coordinate cutoff.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import fitz  # PyMuPDF


# Fraction of page height treated as header/footer margin.
HEADER_FRAC = 0.055
FOOTER_FRAC = 0.945


@dataclass
class Page:
    number: int  # 1-based PDF page number
    text: str


def _column_sorted(blocks: list[tuple], page_width: float) -> list[tuple]:
    """Order blocks: left column top-down, then right column top-down.

    A block belongs to the right column when it starts past the page midline.
    Full-width blocks (titles spanning both columns) start on the left and
    naturally sort into the left stream, which matches reading order because
    they sit above the columns they introduce.
    """
    mid = page_width / 2
    left = [b for b in blocks if b[0] < mid * 0.9]
    right = [b for b in blocks if b[0] >= mid * 0.9]
    left.sort(key=lambda b: (round(b[1], 1), b[0]))
    right.sort(key=lambda b: (round(b[1], 1), b[0]))
    return left + right


def extract_pages(pdf_path: str, start: int = 1, end: int | None = None) -> list[Page]:
    """Extract column-ordered text for pages [start, end] (1-based, inclusive)."""
    doc = fitz.open(pdf_path)
    pages: list[Page] = []
    last = min(end or doc.page_count, doc.page_count)
    for i in range(start - 1, last):
        page = doc[i]
        h, w = page.rect.height, page.rect.width
        blocks = [
            b
            for b in page.get_text("blocks")
            if b[6] == 0  # text blocks only
            and b[1] > h * HEADER_FRAC
            and b[3] < h * FOOTER_FRAC
            and b[4].strip()
        ]
        ordered = _column_sorted(blocks, w)
        text = "\n".join(_clean(b[4]) for b in ordered)
        pages.append(Page(number=i + 1, text=text))
    doc.close()
    return pages


def _clean(block_text: str) -> str:
    # Rejoin words hyphenated across line breaks, then collapse intra-block
    # newlines: a block is one logical run of text.
    t = re.sub(r"-\n(?=[a-z])", "", block_text)
    t = re.sub(r"\s*\n\s*", " ", t.strip())
    return t
