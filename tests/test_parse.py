from codecite.extract import Page
from codecite.parse import parse_pages


def make_pages(*texts):
    return [Page(number=i + 1, text=t) for i, t in enumerate(texts)]


DIV_B_PART9 = (
    "Division B\n"
    "Part 9 Housing and Small Buildings\n"
    "Section 9.8. Stairs, Ramps, Handrails and Guards\n"
    "9.8.8. Guards\n"
    "9.8.8.3. Height of Guards\n"
    "1) All guards shall be not less than 1 070 mm high.\n"
    "2) Guards within dwelling units shall be not less than 900 mm high.\n"
)


def test_article_parsed_with_full_hierarchy():
    clauses = parse_pages(make_pages(DIV_B_PART9))
    assert len(clauses) == 1
    c = clauses[0]
    assert c.kind == "article"
    assert c.division == "B"
    assert c.part == 9
    assert c.clause_id == "9.8.8.3."
    assert c.title == "Height of Guards"
    assert c.section == "9.8."
    assert c.section_title == "Stairs, Ramps, Handrails and Guards"
    assert c.subsection == "9.8.8."
    assert "1 070 mm" in c.text


def test_toc_dot_leaders_and_watermark_are_ignored():
    text = (
        "Division B\n"
        "Part 9 Housing and Small Buildings\n"
        "9.8.8.3. Height of Guards ............... 9-89\n"
        "Copyright NRC 1941 - 2022 World Rights Reserved\n"
        "Section 9.8. Stairs\n"
        "9.8.8. Guards\n"
        "9.8.8.3. Height of Guards\n"
        "1) All guards shall be not less than 1 070 mm high.\n"
    )
    clauses = parse_pages(make_pages(text))
    assert len(clauses) == 1
    assert "World Rights" not in clauses[0].text


def test_attribution_section_is_skipped():
    text = (
        DIV_B_PART9
        + "Section 9.37. Objectives and Functional Statements\n"
        + "9.8.8.3. Height of Guards\n"
        + "(1) [F30-OS3.1] [F10-OS3.7]\n"
    )
    clauses = parse_pages(make_pages(text))
    assert len(clauses) == 1  # the attribution copy did not become a clause
    assert "[F30-OS3.1]" not in clauses[0].text


def test_appendix_note_parsed_and_article_regex_disabled_in_notes():
    text = (
        DIV_B_PART9
        + "Notes to Part 9 Housing and Small Buildings\n"
        + "A-9.8.8.3. Minimum Heights. Guard heights are based on waist heights.\n"
        + "9.1.1.1. Table artifact that must not become an article\n"
    )
    clauses = parse_pages(make_pages(text))
    kinds = [(c.kind, c.clause_id) for c in clauses]
    assert ("article", "9.8.8.3.") in kinds
    assert ("note", "A-9.8.8.3.") in kinds
    assert ("article", "9.1.1.1.") not in kinds
    note = next(c for c in clauses if c.kind == "note")
    assert note.title == "Minimum Heights"
    assert "waist heights" in note.text


def test_division_tracked_for_duplicate_clause_numbers():
    div_a = (
        "Division A\n"
        "Part 1 Compliance\n"
        "Section 1.4. Terms and Abbreviations\n"
        "1.4.1. Definitions\n"
        "1.4.1.2. Defined Terms\n"
        "1) The words in italics have the following meanings.\n"
    )
    div_b = (
        "Division B\n"
        "Part 1 General\n"
        "Section 1.4. Terms\n"
        "1.4.1. Definitions\n"
        "1.4.1.2. Defined Terms\n"
        "1) Other content.\n"
    )
    clauses = parse_pages(make_pages(div_a, div_b))
    assert [(c.division, c.clause_id) for c in clauses] == [
        ("A", "1.4.1.2."),
        ("B", "1.4.1.2."),
    ]


def test_appendix_reference_artifact_does_not_trigger_skip():
    text = DIV_B_PART9 + "Appendix C, values\n" + "3) More guard rules follow here.\n"
    clauses = parse_pages(make_pages(text))
    assert "More guard rules" in clauses[0].text
