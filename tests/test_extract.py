import fitz

from codecite.extract import _clean, extract_pages


def test_clean_rejoins_hyphenated_words_and_collapses_newlines():
    assert _clean("construc-\ntion of the\nbuilding") == "construction of the building"


def test_two_column_page_reads_left_column_first(tmp_path):
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    # left column: two blocks; right column: one block
    page.insert_textbox(fitz.Rect(50, 100, 280, 160), "LEFT TOP text")
    page.insert_textbox(fitz.Rect(50, 300, 280, 360), "LEFT BOTTOM text")
    page.insert_textbox(fitz.Rect(320, 100, 560, 160), "RIGHT text")
    pdf = tmp_path / "twocol.pdf"
    doc.save(pdf)
    doc.close()

    pages = extract_pages(str(pdf))
    text = pages[0].text
    assert text.index("LEFT TOP") < text.index("LEFT BOTTOM") < text.index("RIGHT")


def test_header_and_footer_are_dropped(tmp_path):
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_textbox(fitz.Rect(50, 5, 400, 30), "RUNNING HEADER")
    page.insert_textbox(fitz.Rect(50, 400, 400, 430), "BODY text")
    page.insert_textbox(fitz.Rect(50, 762, 400, 787), "PAGE FOOTER 123")
    pdf = tmp_path / "margins.pdf"
    doc.save(pdf)
    doc.close()

    text = extract_pages(str(pdf))[0].text
    assert "BODY" in text
    assert "HEADER" not in text
    assert "FOOTER" not in text
