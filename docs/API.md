# API

Base URL: `http://localhost:8000` (default `uvicorn app.main:app` port).
Interactive OpenAPI docs are available at `/docs` once the server is running.

## `GET /health`

Returns provider reachability, not just "the process is up."

```json
{
  "status": "ok",
  "ollama": { "reachable": true, "model_available": true },
  "qdrant": true
}
```
`status` is `"degraded"` if Ollama is unreachable, the configured model isn't
pulled, or Qdrant can't be counted.

## `POST /documents`

Multipart upload (`file` field). Accepts `.pdf`, `.md`, `.markdown`.

```json
{
  "document": { "document_id": "...", "filename": "paper.pdf", "doc_type": "pdf", "page_count": 12, ... },
  "chunks_created": 34,
  "skipped": false
}
```
`skipped: true` means byte-identical content was already ingested (content-hash
idempotency) - no re-embedding happened.

## `GET /documents`

```json
{ "documents": [ { "document_id": "...", "filename": "paper.pdf", ... } ] }
```

## `DELETE /documents/{document_id}`

```json
{ "document_id": "...", "deleted_chunks": 34 }
```
404 if the document doesn't exist. Also removes the raw file stored for it.

## `GET /documents/{document_id}/file`

Returns the original uploaded bytes (`application/pdf` or `text/markdown`),
for a frontend that wants to render the source document (e.g. jump to a
citation's page). 404 if the document or its raw file no longer exists.

## `GET /documents/{document_id}/outline`

The document's extracted table of contents (nested by heading depth).

```json
{
  "document_id": "...",
  "outline": [
    { "title": "1. Introduction", "level": 1, "page": 1,
      "section_path": "1. Introduction", "children": [] },
    { "title": "2. Method", "level": 1, "page": 2, "section_path": "2. Method",
      "children": [ { "title": "2.1 Retrieval", "level": 2, "page": 2,
                      "section_path": "2.1 Retrieval", "children": [] } ] }
  ]
}
```

`outline` is `[]` if the document has no detectable headings, or was ingested
before outline extraction existed and has not been re-uploaded (re-uploading
byte-identical content backfills the sidecar without re-embedding). 404 for an
unknown `document_id`. `page` is `null` for Markdown.

## `GET /documents/{document_id}/tables`

```json
{ "document_id": "...", "tables": [] }
```

Always `[]` until a real `TableExtractor` is wired (`TABLE_EXTRACTION_ENABLED`,
V2). 404 for an unknown `document_id`.

## `POST /documents/{document_id}/extract`  (V2 seam)

Body: an extraction schema.

```json
{ "schema": { "fields": [ { "name": "title", "description": "the document title" } ] } }
```

Response — with the default NoOp extractor:

```json
{ "document_id": "...", "values": [], "implemented": false }
```

`implemented: false` means no real extractor is wired yet
(`STRUCTURED_EXTRACTION_ENABLED`). 404 for an unknown `document_id`.

## `POST /compare`  (V2 seam)

```json
{ "document_ids": ["<id-a>", "<id-b>"], "question": "which mentions X?" }
```

Response — with the default NoOp comparer:

```json
{ "document_ids": ["<id-a>", "<id-b>"], "question": "which mentions X?",
  "summary": "", "citations": [], "implemented": false }
```

Requires at least two `document_ids` (422 otherwise); 404 if any id is unknown.

## `POST /query`

```json
{ "question": "How does reciprocal rank fusion work?", "top_k": 5, "rerank": null }
```
`rerank: null` uses the server's `RERANK_ENABLED` default; `true`/`false`
overrides it per-request.

```json
{
  "answer": "Reciprocal rank fusion merges dense and sparse rankings by summing 1/(k+rank) ... [paper.pdf p.2]",
  "citations": [ { "filename": "paper.pdf", "page": 2, "chunk_id": "...", "quote": "...",
                   "char_start": 1840, "char_end": 2210 } ],
  "retrieved_chunks": [ ... ],
  "context": { "truncated": false, "chunks_used": 3,
               "chunk_ids": ["...", "...", "..."] },
  "model": "qwen3:1.7b",
  "timing_ms": { "retrieval_ms": 12.3, "generation_ms": 4210.5 }
}
```

`context` reports which of the `retrieved_chunks` actually fit the token budget
and reached the model — `chunk_ids` is a subset of the retrieved ids, and
`truncated` is `true` if the top chunk had to be cut or some retrieved chunks
were dropped. `citations[].char_start/char_end` are best-effort offsets of the
cited chunk in the document's cleaned text (span highlighting only).

## Error responses

Every error is `{"error": "<message>", "type": "<ExceptionClassName>"}`.

| Exception | Status |
|---|---|
| `OllamaUnavailableError` | 503 |
| `OllamaModelNotFoundError` | 503 |
| `OllamaGenerationError` | 502 |
| `DocumentNotFoundError` | 404 |
| `UnsupportedFileTypeError` | 415 |
| `ConfigurationError` | 500 |
| `EmbeddingError` | 500 |
| (any other `RagError`) | 500 |
| Pydantic validation failure (e.g. empty `question`) | 422 |
