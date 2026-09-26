"""Document loaders: turn a raw file on disk into a list of TextBlock plus
document-level metadata. Loaders never chunk or embed - they only extract
structure (page, section, heading) and raw text.
"""

from __future__ import annotations

import re

import fitz  # PyMuPDF

from app.core.errors import UnsupportedFileTypeError
from app.ingestion.cleaning import clean_text, strip_repeated_headers_footers
from app.ingestion.ocr import NoOpOcrEngine, OcrEngine
from app.models.domain import IngestionWarning, TextBlock

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)")


def load_document(
    file_bytes: bytes, filename: str, *, ocr_engine: OcrEngine | None = None
) -> tuple[list[TextBlock], int | None, list[IngestionWarning]]:
    """Dispatch to the right loader based on file extension.

    Returns (blocks, page_count, warnings). page_count is None for markdown.
    `ocr_engine` (V2) is consulted only for PDF pages with no extractable text;
    the default NoOp engine leaves today's 'warn and skip' behaviour unchanged.
    """
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return load_pdf(file_bytes, filename, ocr_engine=ocr_engine)
    if lower.endswith(".md") or lower.endswith(".markdown"):
        blocks = load_markdown(file_bytes.decode("utf-8", errors="replace"))
        return blocks, None, []
    raise UnsupportedFileTypeError(
        f"Unsupported file type for '{filename}': only .pdf and .md/.markdown are supported"
    )


def load_pdf(
    file_bytes: bytes,
    filename: str,
    document_id: str = "",
    *,
    ocr_engine: OcrEngine | None = None,
) -> tuple[list[TextBlock], int, list[IngestionWarning]]:
    """Extract text from a PDF, page by page, using font-size heuristics to
    detect headings and tracking the active section per page.

    A page with no extractable text is handed to `ocr_engine` (V2) if one is
    enabled; otherwise it produces an IngestionWarning and is skipped, exactly
    as before.
    """
    ocr = ocr_engine or NoOpOcrEngine()
    warnings: list[IngestionWarning] = []
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    try:
        page_count = doc.page_count
        page_texts: list[str] = []
        page_headings: list[list[tuple[str, float]]] = []

        for page in doc:
            page_dict = page.get_text("dict")
            spans_text: list[str] = []
            headings: list[tuple[str, float]] = []
            font_sizes: list[float] = []

            for block in page_dict.get("blocks", []):
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            font_sizes.append(span.get("size", 0.0))

            median_size = sorted(font_sizes)[len(font_sizes) // 2] if font_sizes else 0.0

            for block in page_dict.get("blocks", []):
                block_lines = []
                block_max_size = 0.0
                for line in block.get("lines", []):
                    line_text = "".join(span.get("text", "") for span in line.get("spans", []))
                    if line_text.strip():
                        block_lines.append(line_text)
                    for span in line.get("spans", []):
                        block_max_size = max(block_max_size, span.get("size", 0.0))
                block_text = "\n".join(block_lines).strip()
                if not block_text:
                    continue
                spans_text.append(block_text)
                if median_size and block_max_size >= median_size * 1.15 and len(block_text) < 120:
                    headings.append((block_text, block_max_size))

            page_text = "\n".join(spans_text)

            if not page_text.strip() and getattr(ocr, "enabled", False):
                recovered = _ocr_page(page, ocr)
                if recovered and recovered.strip():
                    page_text = recovered

            page_texts.append(page_text)
            page_headings.append(headings)

            if not page_text.strip():
                message = (
                    "Page produced no extractable text (likely a scanned image; OCR is not implemented)."
                    if not getattr(ocr, "enabled", False)
                    else "Page produced no extractable text and OCR recovered nothing."
                )
                warnings.append(
                    IngestionWarning(
                        document_id=document_id,
                        filename=filename,
                        page=page.number + 1,
                        message=message,
                    )
                )

        page_texts = strip_repeated_headers_footers(page_texts)

        blocks: list[TextBlock] = []
        current_section: str | None = None
        for page_idx, (page_text, headings) in enumerate(
            zip(page_texts, page_headings, strict=True)
        ):
            page_number = page_idx + 1
            cleaned = clean_text(page_text)
            if not cleaned:
                continue

            # Emit every heading detected on the page (in reading order), not
            # just the first - the outline builder (app/analysis/outline.py)
            # needs them all, and the trailing body block inherits the last
            # heading as its section.
            for heading_text, _size in headings:
                current_section = heading_text
                blocks.append(
                    TextBlock(
                        text=heading_text, page=page_number, section=heading_text, is_heading=True
                    )
                )

            blocks.append(
                TextBlock(text=cleaned, page=page_number, section=current_section, is_heading=False)
            )

        return blocks, page_count, warnings
    finally:
        doc.close()


def _ocr_page(page: fitz.Page, ocr: OcrEngine) -> str | None:
    """Render a PDF page to a PNG and hand it to the OCR engine. Any failure
    (render or OCR) is swallowed - a scanned page that can't be recovered just
    falls through to the existing warning path."""
    try:
        png_bytes: bytes = page.get_pixmap(dpi=200).tobytes("png")
        return ocr.ocr_page(png_bytes)
    except Exception:  # noqa: BLE001 - OCR is best-effort, never fatal to ingest
        return None


def load_markdown(text: str) -> list[TextBlock]:
    """Parse Markdown into heading-aware TextBlocks. No page numbers."""
    lines = text.split("\n")
    blocks: list[TextBlock] = []
    heading_stack: list[str] = []
    paragraph_lines: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph_lines
        if paragraph_lines:
            paragraph_text = clean_text("\n".join(paragraph_lines))
            if paragraph_text:
                section = " > ".join(heading_stack) if heading_stack else None
                blocks.append(
                    TextBlock(text=paragraph_text, page=None, section=section, is_heading=False)
                )
            paragraph_lines = []

    for line in lines:
        match = _HEADING_RE.match(line)
        if match:
            flush_paragraph()
            level = len(match.group(1))
            title = match.group(2).strip()
            heading_stack = heading_stack[: level - 1]
            heading_stack.append(title)
            section = " > ".join(heading_stack)
            blocks.append(TextBlock(text=title, page=None, section=section, is_heading=True))
        else:
            paragraph_lines.append(line)

    flush_paragraph()
    return blocks
