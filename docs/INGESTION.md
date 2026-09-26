# Ingestion

## Supported formats

- **PDF** (`.pdf`) via PyMuPDF (`fitz`). Extracted per page; headings detected
  by relative font size (a block's max span size >= 1.15x the page's median
  span size, and short enough to plausibly be a heading). The active heading
  becomes each subsequent block's `section` until the next heading.
- **Markdown** (`.md`, `.markdown`) via a heading-stack line scanner (`^#{1,6}\s+`).
  `section` is the full heading breadcrumb, e.g. `"Widget Framework > Installation > Requirements"`.
  Markdown chunks never have a page number (`page_start`/`page_end` are `None`).

Anything else raises `UnsupportedFileTypeError` (415 over the API).

## Chunking

Structure-aware, token-accurate sliding window (`app/ingestion/chunking.py`),
measured with `tiktoken`'s `cl100k_base` encoding (see the tokenizer caveat
in `docs/ARCHITECTURE.md`).

| Setting | Default | Meaning |
|---|---|---|
| `CHUNK_SIZE_TOKENS` | 400 | Max tokens per chunk |
| `CHUNK_OVERLAP_TOKENS` | 60 | Trailing tokens repeated into the next chunk |
| `CHUNK_MIN_TOKENS` | 40 | A trailing remainder smaller than this is merged into the previous chunk instead of becoming its own fragment |

400/60 balances citation granularity (small enough to point at a specific
paragraph) against retrieval recall, while keeping 5 chunks of context well
within the default 2048-token `OLLAMA_CONTEXT_LENGTH`.

A chunk that spans multiple source blocks records `page_start`/`page_end` as
the min/max page among its constituent blocks, and `section` as the first
non-null section among them.

## Metadata preserved end-to-end

Every `Chunk` carries: `chunk_id`, `document_id`, `chunk_index`, `filename`,
`page_start`/`page_end`, `section`, `text`, `token_count`, `char_start`/`char_end`.
This is unchanged from ingestion through retrieval (`ScoredChunk.chunk`) to
the final `Citation` returned by the API.

## Derived artefacts (sidecars)

Each ingest also (re)writes per-document JSON sidecars under
`PROCESSED_STORAGE_PATH` (`./data/processed`), named
`<document_id>.<kind>.json`:

| Kind | Written by | Served at | Notes |
|---|---|---|---|
| `outline` | `build_outline` over the loader's heading blocks | `GET /documents/{id}/outline` | Nested table of contents. Cheap + deterministic; rewritten every ingest so a re-upload backfills the newest extraction logic. |
| `tables` | the configured `TableExtractor` | `GET /documents/{id}/tables` | `NoOpTableExtractor` (default) writes `[]`. A real extractor is a V2 drop-in (`TABLE_EXTRACTION_ENABLED`). |

Sidecars are deleted with the document and are safe to delete by hand (the next
re-upload regenerates them).

## Idempotency

`document_id` is `sha256(file_bytes)` - a content hash. Re-ingesting
byte-identical content is detected via `data/indexes/manifest.json` and
short-circuits before chunking/embedding (`IngestResponse.skipped: true`).
The raw bytes and the derived sidecars are still (re)written, so a re-upload is
the way to backfill outline/table extraction for an already-indexed document.
Changed content gets a new `document_id` and is ingested as, in effect, a new
document (the old one isn't automatically deleted - use `DELETE /documents/{id}`
first if you want to replace it).

## OCR (V2 seam)

Scanned PDF pages that PyMuPDF extracts no text from produce an
`IngestionWarning` (logged, not in the API response) and are skipped.

`app/ingestion/ocr.py` defines the `OcrEngine` Protocol and a `NoOpOcrEngine`
default. `load_pdf(..., ocr_engine=...)` calls it for any empty page and uses
whatever text it returns. With the default engine (`OCR_ENABLED=false`)
behaviour is unchanged; a real backend (Tesseract, a vision model) implements
the Protocol, gets a branch in `build_ocr_engine`, and must load its model
lazily on first use.
