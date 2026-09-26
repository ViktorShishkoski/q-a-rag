"""Table-extraction seam (V2).

`GET /documents/{id}/tables` and `DocumentService.tables()` already exist and
read a `<document_id>.tables.json` sidecar. Nothing writes that sidecar yet -
this module defines the interface that will, and a NoOp default so the wiring
is inert until a real extractor is dropped in.

A real implementation (PyMuPDF's `page.find_tables()`, Camelot, or a layout
model) implements `TableExtractor`, gets a branch in `build_table_extractor`,
and is enabled with `TABLE_EXTRACTION_ENABLED=true`. It must load any heavy
dependency lazily on first `extract` call.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.models.domain import Table, TextBlock


@runtime_checkable
class TableExtractor(Protocol):
    enabled: bool

    def extract(
        self, *, document_id: str, file_bytes: bytes, filename: str, blocks: list[TextBlock]
    ) -> list[Table]:
        """Return the tabular regions found in the document. `blocks` is the
        already-loaded structure, so a text-only extractor need not re-parse."""
        ...


class NoOpTableExtractor:
    """Default extractor - finds nothing. The tables sidecar is written as an
    empty list, and the API keeps returning `{"tables": []}`."""

    enabled = False

    def extract(
        self, *, document_id: str, file_bytes: bytes, filename: str, blocks: list[TextBlock]
    ) -> list[Table]:
        return []
