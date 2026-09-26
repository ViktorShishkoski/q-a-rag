"""Structured field extraction (V2 - interface + NoOp).

Given an ingested document and an `ExtractionSchema` (a list of named fields
with descriptions), return one `ExtractedValue` per field, each with its
supporting citations. This reuses the retrieval + generation stack rather than
re-reading the document: retrieve chunks per field, prompt the LLM for a JSON
object, verify citations the same way `generation/citations.py` does.

`NoOpStructuredExtractor` returns a result with `implemented=False` and no
values, so `POST /documents/{id}/extract` is a live endpoint with a truthful
"not wired yet" payload. A real implementation implements `StructuredExtractor`
and gets a branch in `build_structured_extractor`.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.models.domain import ExtractionSchema, StructuredExtractionResult


@runtime_checkable
class StructuredExtractor(Protocol):
    def extract(
        self, *, document_id: str, schema: ExtractionSchema
    ) -> StructuredExtractionResult: ...


class NoOpStructuredExtractor:
    """Default - returns an empty, `implemented=False` result."""

    def extract(self, *, document_id: str, schema: ExtractionSchema) -> StructuredExtractionResult:
        return StructuredExtractionResult(document_id=document_id, values=[], implemented=False)
