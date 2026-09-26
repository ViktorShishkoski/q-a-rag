from __future__ import annotations

from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import FileResponse

from app.core.dependencies import get_document_service, get_ingestion_service
from app.core.errors import UnsupportedFileTypeError
from app.ingestion.service import DocumentService, IngestionService
from app.models.domain import Document
from app.models.responses import (
    DeleteDocumentResponse,
    DocumentListResponse,
    IngestResponse,
    OutlineResponse,
    TablesResponse,
)

_MEDIA_TYPES = {"pdf": "application/pdf", "markdown": "text/markdown"}

router = APIRouter(tags=["documents"])

_SUPPORTED_SUFFIXES = (".pdf", ".md", ".markdown")


@router.post("/documents", response_model=IngestResponse)
async def upload_document(
    file: UploadFile, ingestion_service: IngestionService = Depends(get_ingestion_service)
) -> IngestResponse:
    filename = file.filename or ""
    if not filename.lower().endswith(_SUPPORTED_SUFFIXES):
        raise UnsupportedFileTypeError(
            f"Unsupported file type for '{filename}': only .pdf and .md/.markdown are supported"
        )

    content = await file.read()
    document, chunks, skipped = ingestion_service.ingest_document(content, filename)
    return IngestResponse(document=document, chunks_created=len(chunks), skipped=skipped)


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(document_service: DocumentService = Depends(get_document_service)) -> DocumentListResponse:
    entries = document_service.list_documents()
    documents = [
        Document(
            document_id=e.document_id,
            filename=e.filename,
            source_path=e.filename,
            doc_type="pdf" if e.filename.lower().endswith(".pdf") else "markdown",
            page_count=e.page_count,
            ingested_at=e.ingested_at,
            content_hash=e.document_id,
            chunk_count=e.chunk_count,
        )
        for e in entries
    ]
    return DocumentListResponse(documents=documents)


@router.delete("/documents/{document_id}", response_model=DeleteDocumentResponse)
def delete_document(
    document_id: str, document_service: DocumentService = Depends(get_document_service)
) -> DeleteDocumentResponse:
    deleted = document_service.delete_document(document_id)
    return DeleteDocumentResponse(document_id=document_id, deleted_chunks=deleted)


@router.get("/documents/{document_id}/file")
def get_document_file(
    document_id: str, document_service: DocumentService = Depends(get_document_service)
) -> FileResponse:
    path, doc_type = document_service.raw_file(document_id)
    return FileResponse(path, media_type=_MEDIA_TYPES[doc_type], filename=path.name)


@router.get("/documents/{document_id}/outline", response_model=OutlineResponse)
def get_document_outline(
    document_id: str, document_service: DocumentService = Depends(get_document_service)
) -> OutlineResponse:
    return OutlineResponse(
        document_id=document_id, outline=document_service.outline(document_id)
    )


@router.get("/documents/{document_id}/tables", response_model=TablesResponse)
def get_document_tables(
    document_id: str, document_service: DocumentService = Depends(get_document_service)
) -> TablesResponse:
    return TablesResponse(
        document_id=document_id, tables=document_service.tables(document_id)
    )
