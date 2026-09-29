"""OCR seam for scanned PDF pages (V2).

Today `load_pdf` emits an `IngestionWarning` for any page PyMuPDF extracts no
text from and moves on. This module defines the interface a real OCR backend
must satisfy so that behaviour can be swapped for actual text recovery without
touching the loader's control flow.

`NoOpOcrEngine` is the default (wired when `OCR_ENABLED=false`): it returns
`None` for every page, so ingestion behaves exactly as it does today. A real
implementation (e.g. Tesseract via `pytesseract`, or a hosted vision model) is
a drop-in: implement `OcrEngine`, add a branch to `build_ocr_engine`, flip the
flag. It must load any heavy model lazily on first `ocr_page` call, never at
construction (see docs/DEVELOPMENT.md DI rules).
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class OcrEngine(Protocol):
    enabled: bool

    def ocr_page(self, page_image_png: bytes) -> str | None:
        """Return recovered text for a rendered page image, or None if OCR
        produced nothing usable."""
        ...


class NoOpOcrEngine:
    """Default engine - never recovers text. Ingestion of scanned pages keeps
    its current 'warn and skip' behaviour."""

    enabled = False

    def ocr_page(self, page_image_png: bytes) -> str | None:
        return None
