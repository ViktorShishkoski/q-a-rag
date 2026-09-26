"""Orchestrates load -> clean -> chunk -> embed -> dual-store upsert.

Idempotency: a JSON manifest (document_id -> ManifestEntry) is the source of
truth for "has this exact file already been ingested". Since document_id is
a content hash, re-ingesting byte-identical content is a fast no-op; changed
content gets a new document_id and is ingested as (in effect) a new document.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.analysis.outline import build_outline
from app.core.errors import DocumentNotFoundError
from app.embeddings.base import EmbeddingProvider
from app.ingestion.chunking import chunk_text
from app.ingestion.loaders import load_document
from app.ingestion.metadata import build_chunks, build_document
from app.ingestion.ocr import NoOpOcrEngine, OcrEngine
from app.ingestion.tables import NoOpTableExtractor, TableExtractor
from app.models.domain import Chunk, Document, ManifestEntry, OutlineNode, Table, TextBlock
from app.storage.bm25_store import SparseIndex
from app.storage.vector_store import VectorStore


class Manifest:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._entries: dict[str, ManifestEntry] = {}
        if self._path.exists():
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            self._entries = {k: ManifestEntry.model_validate(v) for k, v in raw.items()}

    def has(self, document_id: str) -> bool:
        return document_id in self._entries

    def get(self, document_id: str) -> ManifestEntry | None:
        return self._entries.get(document_id)

    def put(self, entry: ManifestEntry) -> None:
        self._entries[entry.document_id] = entry
        self._save()

    def remove(self, document_id: str) -> None:
        self._entries.pop(document_id, None)
        self._save()

    def list(self) -> list[ManifestEntry]:
        return list(self._entries.values())

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {k: json.loads(v.model_dump_json()) for k, v in self._entries.items()}
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def raw_file_path(raw_dir: Path, document_id: str, filename: str) -> Path:
    return raw_dir / f"{document_id}{Path(filename).suffix.lower()}"


def processed_sidecar_path(processed_dir: Path, document_id: str, kind: str) -> Path:
    """Path to a per-document derived-artefact JSON (kind is e.g. 'outline',
    'tables')."""
    return processed_dir / f"{document_id}.{kind}.json"


def _write_sidecar(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read_outline_sidecar(path: Path) -> list[OutlineNode]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [OutlineNode.model_validate(node) for node in raw]


def _read_tables_sidecar(path: Path) -> list[Table]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [Table.model_validate(t) for t in raw]


class IngestionService:
    def __init__(
        self,
        *,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
        sparse_index: SparseIndex,
        manifest: Manifest,
        chunk_size_tokens: int,
        chunk_overlap_tokens: int,
        chunk_min_tokens: int,
        embedding_batch_size: int,
        raw_dir: Path,
        processed_dir: Path,
        ocr_engine: OcrEngine | None = None,
        table_extractor: TableExtractor | None = None,
    ) -> None:
        self._embeddings = embedding_provider
        self._vector_store = vector_store
        self._sparse_index = sparse_index
        self._manifest = manifest
        self._chunk_size = chunk_size_tokens
        self._chunk_overlap = chunk_overlap_tokens
        self._chunk_min = chunk_min_tokens
        self._embed_batch_size = embedding_batch_size
        self._raw_dir = raw_dir
        self._processed_dir = processed_dir
        self._ocr_engine = ocr_engine or NoOpOcrEngine()
        self._table_extractor = table_extractor or NoOpTableExtractor()

    def ingest_document(
        self, file_bytes: bytes, filename: str, source_path: str = ""
    ) -> tuple[Document, list[Chunk], bool]:
        """Returns (document, chunks, skipped). skipped=True means the exact
        same content was already ingested and no work was done."""
        doc_type = "pdf" if filename.lower().endswith(".pdf") else "markdown"
        blocks, page_count, _warnings = load_document(
            file_bytes, filename, ocr_engine=self._ocr_engine
        )

        document = build_document(
            file_bytes=file_bytes,
            filename=filename,
            source_path=source_path or filename,
            doc_type=doc_type,
            page_count=page_count,
        )

        raw_path = raw_file_path(self._raw_dir, document.document_id, filename)
        if not raw_path.exists():
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            raw_path.write_bytes(file_bytes)

        # Outline and tables are derived artefacts written as JSON sidecars next
        # to the raw file, (re)written on every ingest attempt so a document
        # ingested before these features - or before better extraction logic -
        # is backfilled on a plain re-upload.
        self._write_outline(document.document_id, blocks)
        self._write_tables(document.document_id, file_bytes, filename, blocks)

        if self._manifest.has(document.document_id):
            return document, [], True

        drafts = chunk_text(
            blocks,
            chunk_size=self._chunk_size,
            overlap=self._chunk_overlap,
            min_tokens=self._chunk_min,
        )
        chunks = build_chunks(document, drafts)

        if chunks:
            vectors: list[list[float]] = []
            for i in range(0, len(chunks), self._embed_batch_size):
                batch = chunks[i : i + self._embed_batch_size]
                vectors.extend(self._embeddings.embed_documents([c.text for c in batch]))

            self._vector_store.upsert(chunks, vectors)
            self._sparse_index.upsert(chunks)
            self._sparse_index.save()

        self._manifest.put(
            ManifestEntry(
                document_id=document.document_id,
                filename=document.filename,
                chunk_count=len(chunks),
                ingested_at=document.ingested_at,
                page_count=page_count,
            )
        )
        return document, chunks, False

    def _write_outline(self, document_id: str, blocks: list[TextBlock]) -> None:
        # Always (re)written on an ingest attempt - unlike the raw bytes, the
        # outline is derived and can improve when extraction logic changes, so a
        # re-upload of an already-ingested document backfills the better version.
        path = processed_sidecar_path(self._processed_dir, document_id, "outline")
        outline = build_outline(blocks)
        _write_sidecar(path, [node.model_dump(mode="json") for node in outline])

    def _write_tables(
        self, document_id: str, file_bytes: bytes, filename: str, blocks: list[TextBlock]
    ) -> None:
        # NoOp extractor -> writes []. A real extractor (V2) populates the
        # sidecar that DocumentService.tables() / GET /documents/{id}/tables
        # already read.
        path = processed_sidecar_path(self._processed_dir, document_id, "tables")
        tables = self._table_extractor.extract(
            document_id=document_id, file_bytes=file_bytes, filename=filename, blocks=blocks
        )
        _write_sidecar(path, [t.model_dump(mode="json") for t in tables])


class DocumentService:
    def __init__(
        self,
        *,
        vector_store: VectorStore,
        sparse_index: SparseIndex,
        manifest: Manifest,
        raw_dir: Path,
        processed_dir: Path,
    ) -> None:
        self._vector_store = vector_store
        self._sparse_index = sparse_index
        self._manifest = manifest
        self._raw_dir = raw_dir
        self._processed_dir = processed_dir

    def list_documents(self) -> list[ManifestEntry]:
        return self._manifest.list()

    def _require(self, document_id: str) -> ManifestEntry:
        entry = self._manifest.get(document_id)
        if entry is None:
            raise DocumentNotFoundError(f"No document found with id '{document_id}'")
        return entry

    def ensure_exists(self, document_id: str) -> ManifestEntry:
        """Public guard: return the manifest entry or raise DocumentNotFoundError.
        Used by analysis endpoints that don't otherwise touch DocumentService."""
        return self._require(document_id)

    def delete_document(self, document_id: str) -> int:
        entry = self._require(document_id)
        deleted = self._vector_store.delete_document(document_id)
        self._sparse_index.delete_document(document_id)
        self._sparse_index.save()
        self._manifest.remove(document_id)
        raw_file_path(self._raw_dir, document_id, entry.filename).unlink(missing_ok=True)
        for kind in ("outline", "tables"):
            processed_sidecar_path(self._processed_dir, document_id, kind).unlink(missing_ok=True)
        return deleted

    def outline(self, document_id: str) -> list[OutlineNode]:
        """The document's extracted table of contents. Empty list if the
        document has no detectable headings (or predates outline extraction and
        has not been re-ingested)."""
        self._require(document_id)
        return _read_outline_sidecar(
            processed_sidecar_path(self._processed_dir, document_id, "outline")
        )

    def tables(self, document_id: str) -> list[Table]:
        """Tables extracted from the document. Always empty until a real
        TableExtractor is wired (V2) - the NoOp extractor produces none."""
        self._require(document_id)
        return _read_tables_sidecar(
            processed_sidecar_path(self._processed_dir, document_id, "tables")
        )

    def raw_file(self, document_id: str) -> tuple[Path, str]:
        """Returns (path, doc_type) for the raw uploaded file. Raises
        DocumentNotFoundError if the document or its raw file no longer exists."""
        entry = self._manifest.get(document_id)
        if entry is None:
            raise DocumentNotFoundError(f"No document found with id '{document_id}'")
        path = raw_file_path(self._raw_dir, document_id, entry.filename)
        if not path.exists():
            raise DocumentNotFoundError(f"Raw file for document '{document_id}' is missing on disk")
        doc_type = "pdf" if entry.filename.lower().endswith(".pdf") else "markdown"
        return path, doc_type
