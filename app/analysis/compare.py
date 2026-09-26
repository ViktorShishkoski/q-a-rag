"""Cross-document comparison (V2 - interface + NoOp, minimal first cut).

Given two or more ingested document ids and an optional question, retrieve the
most relevant chunks from *each* document (scoping retrieval with
`DocumentFilter`), lay them side by side in one context, and ask the LLM for a
structured comparison with citations back to each source.

`NoOpDocumentComparer` returns a `DocumentComparison` with `implemented=False`.
A real implementation implements `DocumentComparer`, gets a branch in
`build_document_comparer`, and is enabled with `COMPARE_ENABLED=true`. The
retrieval-per-document + shared-context shape is deliberately close to
`GenerationService.answer` so it can reuse `build_context` / `extract_citations`
when it lands.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.models.domain import DocumentComparison


@runtime_checkable
class DocumentComparer(Protocol):
    def compare(
        self, *, document_ids: list[str], question: str | None = None
    ) -> DocumentComparison: ...


class NoOpDocumentComparer:
    """Default - returns an `implemented=False` comparison."""

    def compare(
        self, *, document_ids: list[str], question: str | None = None
    ) -> DocumentComparison:
        return DocumentComparison(
            document_ids=document_ids,
            question=question,
            summary="",
            citations=[],
            implemented=False,
        )
