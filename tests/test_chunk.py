from codecite.chunk import MAX_CHARS, clauses_to_chunks, embed_text
from codecite.parse import Clause


def make_clause(**overrides):
    base = dict(
        kind="article",
        division="B",
        clause_id="9.8.8.3.",
        title="Height of Guards",
        part=9,
        section="9.8.",
        section_title="Stairs, Ramps, Handrails and Guards",
        subsection="9.8.8.",
        subsection_title="Guards",
        page=844,
    )
    base.update(overrides)
    c = Clause(**{k: v for k, v in base.items() if k != "body"})
    c.body = overrides.get("body", ["1) All guards shall be not less than 1 070 mm high."])
    return c


def test_context_header_carries_full_hierarchy():
    [chunk] = clauses_to_chunks([make_clause()])
    ctx = chunk["context"]
    assert "Division B" in ctx
    assert "Part 9 (Housing and Small Buildings)" in ctx
    assert "Section 9.8 (Stairs, Ramps, Handrails and Guards)" in ctx
    assert "Subsection 9.8.8 (Guards)" in ctx
    assert "Article 9.8.8.3 (Height of Guards)" in ctx
    assert embed_text(chunk).startswith(ctx)


def test_long_articles_split_but_share_clause_id():
    body = [f"{i}) Sentence number {i} " + "x" * 400 for i in range(1, 21)]
    chunks = clauses_to_chunks([make_clause(body=body)])
    assert len(chunks) > 1
    assert all(len(c["text"]) <= MAX_CHARS for c in chunks)
    assert {c["clause_id"] for c in chunks} == {"9.8.8.3."}
    assert len({c["id"] for c in chunks}) == len(chunks)  # ids stay unique
    assert all(c["id"].startswith("B-9.8.8.3.") for c in chunks)


def test_note_context_labels_appendix_note():
    note = make_clause(kind="note", clause_id="A-9.8.8.3.", title="Minimum Heights",
                       section="", subsection="")
    [chunk] = clauses_to_chunks([note])
    assert "Appendix Note A-9.8.8.3. (Minimum Heights)" in chunk["context"]
