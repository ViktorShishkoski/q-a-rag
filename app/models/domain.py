"""Core domain entities shared across all layers.

Metadata rule (see docs/ARCHITECTURE.md): document ID, chunk ID,
filename, page, section, and source text must be preserved end-to-end from
ingestion through retrieval to the final citation. Every type below carries
enough of that metadata to satisfy the rule at its layer.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class Document(BaseModel):
    document_id: str  # sha256 of file bytes - content-addressed, enables idempotent re-ingestion
    filename: str
    source_path: str
    doc_type: Literal["pdf", "markdown"]
    page_count: int | None = None
    ingested_at: datetime
    content_hash: str
    chunk_count: int | None = None


class Chunk(BaseModel):
    chunk_id: str  # sha256(document_id + chunk_index + text) - deterministic
    document_id: str
    chunk_index: int
    filename: str
    page_start: int | None = None
    page_end: int | None = None
    section: str | None = None
    text: str
    token_count: int
    char_start: int
    char_end: int


class ScoredChunk(BaseModel):
    chunk: Chunk
    dense_score: float | None = None
    sparse_score: float | None = None
    fused_score: float | None = None
    rerank_score: float | None = None
    rank: int


class Citation(BaseModel):
    document_id: str
    filename: str
    page: int | None = None
    section: str | None = None
    chunk_id: str
    quote: str
    # Approximate character offsets of the cited chunk within the document's
    # normalized (cleaned) text. Best-effort, for span highlighting only - not
    # relied on for citation correctness (that is chunk_id + filename + page).
    char_start: int | None = None
    char_end: int | None = None


class IngestionWarning(BaseModel):
    document_id: str
    filename: str
    page: int | None = None
    message: str


class TextBlock(BaseModel):
    """Intermediate representation produced by loaders, consumed by the chunker."""

    text: str
    page: int | None = None
    section: str | None = None
    is_heading: bool = False


class ChunkDraft(BaseModel):
    """Chunker output before chunk_id/document linkage is assigned."""

    text: str
    page_start: int | None = None
    page_end: int | None = None
    section: str | None = None
    token_count: int
    char_start: int
    char_end: int


class DocumentFilter(BaseModel):
    document_ids: list[str] | None = None


class ManifestEntry(BaseModel):
    document_id: str
    filename: str
    chunk_count: int
    ingested_at: datetime
    page_count: int | None = None  # added post-v1; absent in older manifests


class OutlineNode(BaseModel):
    """One heading in a document's extracted table of contents.

    `title` is the heading text; `level` is 1-based nesting depth; `page` is the
    source page (None for markdown / page-less formats); `section_path` is the
    full breadcrumb ("A > B > C") matching Chunk.section so an outline entry can
    be cross-referenced against retrieved chunks. `children` nests sub-headings.
    """

    title: str
    level: int
    page: int | None = None
    section_path: str
    children: list[OutlineNode] = Field(default_factory=list)


class Table(BaseModel):
    """A tabular region extracted from a document (V2 - populated once a real
    TableExtractor is wired; the NoOp extractor produces none)."""

    document_id: str
    table_index: int
    page: int | None = None
    section: str | None = None
    caption: str | None = None
    rows: list[list[str]] = Field(default_factory=list)


class ExtractionField(BaseModel):
    """One field requested from a document by a structured-extraction call."""

    name: str
    description: str
    example: str | None = None


class ExtractionSchema(BaseModel):
    fields: list[ExtractionField] = Field(default_factory=list)


class ExtractedValue(BaseModel):
    field: str
    value: str | None = None
    citations: list[Citation] = Field(default_factory=list)


class StructuredExtractionResult(BaseModel):
    document_id: str
    values: list[ExtractedValue] = Field(default_factory=list)
    implemented: bool = True  # NoOp extractor sets this False


class DocumentComparison(BaseModel):
    """Result of comparing two or more ingested documents on a question or
    aspect (V2 - populated once a real DocumentComparer is wired; the NoOp
    comparer returns implemented=False)."""

    document_ids: list[str] = Field(default_factory=list)
    question: str | None = None
    summary: str = ""
    citations: list[Citation] = Field(default_factory=list)
    implemented: bool = True  # NoOp comparer sets this False


class GenerationResult(BaseModel):
    text: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class ContextBundle(BaseModel):
    text: str
    included_chunks: list[Chunk] = Field(default_factory=list)
    truncated: bool = False
