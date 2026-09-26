from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.domain import DocumentFilter, ExtractionSchema


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    rerank: bool | None = None
    filters: DocumentFilter | None = None


class DeleteDocumentRequest(BaseModel):
    document_id: str


class ExtractRequest(BaseModel):
    """Body for POST /documents/{id}/extract (V2). `schema_` carries the fields
    to pull; aliased so the JSON key stays `schema` without shadowing
    BaseModel.schema()."""

    schema_: ExtractionSchema = Field(alias="schema")

    model_config = {"populate_by_name": True}


class CompareRequest(BaseModel):
    """Body for POST /compare (V2)."""

    document_ids: list[str] = Field(min_length=2)
    question: str | None = None
