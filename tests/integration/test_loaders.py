from pathlib import Path

import fitz

from app.ingestion.loaders import load_document, load_markdown, load_pdf

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _blank_page_pdf() -> bytes:
    doc = fitz.open()
    doc.new_page()  # one page, no text -> triggers the scanned-page path
    data: bytes = doc.tobytes()
    doc.close()
    return data


class _FakeOcrEngine:
    enabled = True

    def __init__(self, text: str) -> None:
        self._text = text
        self.calls = 0

    def ocr_page(self, page_image_png: bytes) -> str | None:
        self.calls += 1
        assert page_image_png[:8] == b"\x89PNG\r\n\x1a\n"  # a real rendered PNG
        return self._text


def test_blank_pdf_page_warns_when_no_ocr_engine():
    blocks, page_count, warnings = load_pdf(_blank_page_pdf(), "blank.pdf")
    assert page_count == 1
    assert blocks == []
    assert len(warnings) == 1
    assert "OCR is not implemented" in warnings[0].message


def test_ocr_engine_recovers_text_for_a_blank_page():
    engine = _FakeOcrEngine("Recovered heading\nand some body text.")
    blocks, page_count, warnings = load_pdf(_blank_page_pdf(), "scan.pdf", ocr_engine=engine)
    assert engine.calls == 1
    assert warnings == []
    assert any("Recovered heading" in b.text for b in blocks)


def test_load_pdf_extracts_pages_and_sections():
    pdf_bytes = (FIXTURES / "sample.pdf").read_bytes()
    blocks, page_count, warnings = load_pdf(pdf_bytes, "sample.pdf")

    assert page_count == 3
    assert warnings == []
    assert any(b.page == 1 for b in blocks)
    assert any(b.page == 2 for b in blocks)
    assert any(b.page == 3 for b in blocks)

    full_text = " ".join(b.text for b in blocks)
    assert "retrieval" in full_text.lower()
    assert "reciprocal rank fusion" in full_text.lower()

    # At least one heading-derived section should have been picked up.
    assert any(b.section is not None for b in blocks)


def test_load_markdown_builds_heading_hierarchy():
    md_text = (FIXTURES / "sample.md").read_text(encoding="utf-8")
    blocks = load_markdown(md_text)

    sections = {b.section for b in blocks if b.section}
    assert "Widget Framework" in sections
    assert "Widget Framework > Installation > Requirements" in sections
    assert "Widget Framework > Configuration > Environment Variables" in sections

    for b in blocks:
        assert b.page is None

    full_text = " ".join(b.text for b in blocks)
    assert "widget.toml" in full_text


def test_load_document_dispatches_by_extension():
    pdf_blocks, page_count, _ = load_document((FIXTURES / "sample.pdf").read_bytes(), "sample.pdf")
    assert page_count == 3
    assert len(pdf_blocks) > 0

    md_blocks, page_count_md, _ = load_document((FIXTURES / "sample.md").read_bytes(), "sample.md")
    assert page_count_md is None
    assert len(md_blocks) > 0


def test_load_document_rejects_unsupported_extension():
    import pytest

    from app.core.errors import UnsupportedFileTypeError

    with pytest.raises(UnsupportedFileTypeError):
        load_document(b"whatever", "sample.txt")
