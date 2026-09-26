"""Re-exports of request/response models for OpenAPI grouping. Kept as thin
aliases rather than redefinitions so there is exactly one source of truth
per shape (app/models)."""

from __future__ import annotations

from app.models.domain import DocumentComparison, StructuredExtractionResult
from app.models.requests import (
    CompareRequest,
    DeleteDocumentRequest,
    ExtractRequest,
    QueryRequest,
)
from app.models.responses import (
    ContextInfo,
    DeleteDocumentResponse,
    DocumentListResponse,
    HealthResponse,
    IngestResponse,
    OllamaHealth,
    OutlineResponse,
    QueryResponse,
    TablesResponse,
)

__all__ = [
    "CompareRequest",
    "ContextInfo",
    "DeleteDocumentRequest",
    "DeleteDocumentResponse",
    "DocumentComparison",
    "DocumentListResponse",
    "ExtractRequest",
    "HealthResponse",
    "IngestResponse",
    "OllamaHealth",
    "OutlineResponse",
    "QueryRequest",
    "QueryResponse",
    "StructuredExtractionResult",
    "TablesResponse",
]
