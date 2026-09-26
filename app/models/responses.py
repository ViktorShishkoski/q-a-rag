from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.domain import Citation, Document, OutlineNode, ScoredChunk, Table


class IngestResponse(BaseModel):
    document: Document
    chunks_created: int
    skipped: bool = False


class ContextInfo(BaseModel):
    """Which of the retrieved chunks actually reached the model, so a caller can
    show the exact source context an answer was grounded in."""

    truncated: bool = False
    chunks_used: int = 0
    chunk_ids: list[str] = Field(default_factory=list)


class QueryResponse(BaseModel):
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    retrieved_chunks: list[ScoredChunk] = Field(default_factory=list)
    context: ContextInfo = Field(default_factory=ContextInfo)
    model: str
    timing_ms: dict[str, float] = Field(default_factory=dict)


class OutlineResponse(BaseModel):
    document_id: str
    outline: list[OutlineNode] = Field(default_factory=list)


class TablesResponse(BaseModel):
    document_id: str
    tables: list[Table] = Field(default_factory=list)


class OllamaHealth(BaseModel):
    reachable: bool
    model_available: bool


class HealthResponse(BaseModel):
    status: str  # "ok" | "degraded"
    ollama: OllamaHealth
    qdrant: bool


class DocumentListResponse(BaseModel):
    documents: list[Document] = Field(default_factory=list)


class DeleteDocumentResponse(BaseModel):
    document_id: str
    deleted_chunks: int
