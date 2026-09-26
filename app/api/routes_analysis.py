"""Document-analysis endpoints (V2 seams).

Both routes are live and validated, but wired to NoOp providers today: they
return a well-formed payload with `implemented: false` until a real
`StructuredExtractor` / `DocumentComparer` is dropped into the matching
`build_*` factory. This lets the frontend and API contract be built now.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.analysis.compare import DocumentComparer
from app.analysis.extraction import StructuredExtractor
from app.core.dependencies import (
    get_document_comparer,
    get_document_service,
    get_structured_extractor,
)
from app.ingestion.service import DocumentService
from app.models.domain import DocumentComparison, StructuredExtractionResult
from app.models.requests import CompareRequest, ExtractRequest

router = APIRouter(tags=["analysis"])


@router.post("/documents/{document_id}/extract", response_model=StructuredExtractionResult)
def extract_structured_fields(
    document_id: str,
    request: ExtractRequest,
    document_service: DocumentService = Depends(get_document_service),
    extractor: StructuredExtractor = Depends(get_structured_extractor),
) -> StructuredExtractionResult:
    document_service.ensure_exists(document_id)  # 404 for an unknown id
    return extractor.extract(document_id=document_id, schema=request.schema_)


@router.post("/compare", response_model=DocumentComparison)
def compare_documents(
    request: CompareRequest,
    document_service: DocumentService = Depends(get_document_service),
    comparer: DocumentComparer = Depends(get_document_comparer),
) -> DocumentComparison:
    for document_id in request.document_ids:
        document_service.ensure_exists(document_id)  # 404 if any id is unknown
    return comparer.compare(document_ids=request.document_ids, question=request.question)
