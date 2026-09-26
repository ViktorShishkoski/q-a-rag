# Project Walkthrough

A complete, top-to-bottom tour of the **Q&A RAG** system: what it is, how the code
is organised, how data flows through it, and how to run, test, extend, and debug it.

This document is a companion to the focused docs already in `docs/`
(`ARCHITECTURE.md`, `API.md`, `INGESTION.md`, `OLLAMA.md`, `EVALUATION.md`,
`TROUBLESHOOTING.md`). Where those go deep on one topic, this one connects
everything end to end.

---

## 1. What this project is

A **local-first, low-resource Retrieval-Augmented Generation (RAG) backend** for
technical documentation and research papers, plus a small React frontend.

You give it PDFs and Markdown files. It:

1. **Ingests** them — extracts text and structure, cleans it, splits it into
   token-bounded chunks, embeds those chunks, and stores them in two indexes
   (a dense vector index and a sparse keyword index).
2. **Answers questions** — retrieves the most relevant chunks from both indexes,
   fuses the rankings, optionally reranks them, assembles a token-budgeted
   context, prompts a local LLM (via Ollama), and returns the answer **with
   verifiable citations** back to the exact source file/page.

Design priorities, in order:

- **Runs offline on a laptop.** Embedded Qdrant (no server), a pickled BM25
  index, a ~1.7B quantised LLM, `OLLAMA_KEEP_ALIVE=0` so the model unloads
  between calls. No cloud services, no LLM-judge in evaluation.
- **Swappable components.** Every backend (embeddings, vector store, sparse
  index, reranker, LLM) sits behind a `Protocol`. Choosing one is a config
  change, never a code change in the pipeline packages.
- **Citations you can trust.** Metadata (document id, filename, page, section,
  source text) is preserved end-to-end. A citation tag the model invents that
  doesn't resolve to a chunk actually shown to it is dropped, not returned.
- **Idempotent ingestion.** `document_id = sha256(file_bytes)`. Re-ingesting the
  same bytes is a fast no-op.

---

## 2. Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.11 | Pinned for wheel availability (torch, qdrant-client, sentence-transformers) |
| API framework | FastAPI + Uvicorn | ASGI, lifespan-managed service container |
| Config | pydantic-settings | `Settings` from env / `.env` |
| PDF extraction | PyMuPDF (`fitz`) | Per-page text + font-size heading heuristics |
| Tokeniser | `tiktoken` `cl100k_base` | Offline approximation of qwen3's tokeniser |
| Dense index | Qdrant (embedded, `path=`) | Cosine distance, local SQLite-backed storage |
| Sparse index | `rank_bm25.BM25Okapi` | Pickled `(chunks, model)` to one file |
| Default embeddings | `sentence-transformers` `BAAI/bge-small-en-v1.5` (384-d) | Lazy load; weights auto-download once from HF |
| Alt embeddings | Ollama `nomic-embed-text` | No torch; needs a manual `ollama pull` |
| Generation | Ollama `qwen3:1.7b` | `think=false`, `num_ctx=2048`, `num_predict=256` |
| Reranker (optional) | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Lazy load, gated by `RERANK_ENABLED` |
| Frontend | React 19 + Vite + Tailwind v4 + TanStack Query + shadcn-style UI | `react-pdf` for the source viewer |
| Lint / types / tests | Ruff, Mypy (strict on `app/`), Pytest | See `CLAUDE.md` for exact commands |

---

## 3. Repository layout

```
Q&A RAG/
├── app/                     # the backend (fully type-annotated, strict mypy)
│   ├── main.py              # FastAPI app assembly + lifespan + static mount
│   ├── core/               # cross-cutting: config, DI, errors, logging
│   ├── models/             # Pydantic domain entities + request/response shapes
│   ├── ingestion/          # load → clean → chunk → metadata → orchestrate (+ ocr, tables seams)
│   ├── embeddings/         # EmbeddingProvider protocol + 3 implementations
│   ├── storage/            # VectorStore + SparseIndex protocols + impls
│   ├── retrieval/          # dense + sparse + RRF fusion + rerank + orchestrate
│   ├── generation/         # context budget → prompt → LLM → citation extract
│   ├── analysis/           # per-document features: outline (V1), extraction + compare (V2 seams)
│   ├── api/                # thin HTTP routers (health, documents, query, analysis)
│   └── evaluation/         # offline benchmark harness + metrics + reporting
├── scripts/                # CLI entry points (check_ollama, ingest, query, …)
├── tests/
│   ├── unit/               # pure-logic, no model loads, no network
│   ├── integration/        # real ML models / live Ollama / API-level
│   └── fixtures/           # sample.pdf, sample.md, PDF generator
├── frontend/               # React SPA (Vite). Built output served by the API.
├── data/                   # gitignored runtime state (indexes, raw files, reports)
│   ├── raw/                # original uploaded bytes, named <document_id><ext>
│   ├── processed/          # derived sidecars: <document_id>.outline.json, .tables.json
│   ├── indexes/            # qdrant/, bm25/index.pkl, manifest.json
│   └── evaluation/         # eval_dataset.json (committed) + generated reports
├── docs/                   # this file + the focused topic docs
├── pyproject.toml          # deps, ruff, mypy, pytest config
├── .env.example            # every setting with its default + inline caveats
└── CLAUDE.md               # build/run/test/lint command reference
```

**Package dependency rule (enforced by convention, visible in imports):**
`ingestion/`, `retrieval/`, and `generation/` never import FastAPI, and never
import each other. They talk only through the `Protocol` interfaces and the
service classes. This is what lets `scripts/` and a future non-HTTP caller
reuse the exact same services the API uses.

---

## 4. Configuration — `app/core/config.py`

One `Settings` class (pydantic-settings), loaded from environment variables or a
`.env` file. `get_settings()` returns a fresh instance; the DI layer wraps it in
`lru_cache` so the process builds it once.

Groups (see `.env.example` for the annotated full list):

| Group | Keys | Purpose |
|---|---|---|
| Ollama | `OLLAMA_BASE_URL`, `OLLAMA_GENERATION_MODEL`, `OLLAMA_CONTEXT_LENGTH`, `OLLAMA_NUM_PREDICT`, `OLLAMA_KEEP_ALIVE`, `OLLAMA_THINK`, `OLLAMA_TIMEOUT_S`, `OLLAMA_NUM_PARALLEL`* | Generation model + how it's called |
| Embeddings | `EMBEDDING_PROVIDER` (`sentence_transformers`\|`ollama`\|`mock`), `EMBEDDING_MODEL`, `EMBEDDING_OLLAMA_MODEL`, `EMBEDDING_DIM`, `EMBEDDING_BATCH_SIZE` | Which embedder, and its output dimension |
| Storage | `QDRANT_PATH`, `QDRANT_COLLECTION`, `BM25_INDEX_PATH`, `MANIFEST_PATH`, `RAW_STORAGE_PATH` | Where indexes and originals live |
| Chunking | `CHUNK_SIZE_TOKENS` (400), `CHUNK_OVERLAP_TOKENS` (60), `CHUNK_MIN_TOKENS` (40) | Sliding-window sizing |
| Retrieval | `RETRIEVAL_CANDIDATE_K` (20), `RRF_K` (60), `RERANK_ENABLED` (false), `RERANK_MODEL`, `RERANK_CANDIDATE_POOL` | Candidate depth + fusion + rerank |
| Generation budget | `GENERATION_PROVIDER` (`ollama`\|`mock`), `PROMPT_OVERHEAD_TOKENS` (150), `CONTEXT_SAFETY_MARGIN` (0.85) | Context-window budgeting |
| Misc | `LOG_LEVEL` | stdlib logging level |

\* `OLLAMA_NUM_PARALLEL` is **read but never sent** in an API request — Ollama
only honours it as an OS env var before `ollama serve` starts. It lives in
`Settings` purely so `.env.example` has one place listing every Ollama knob.
See `docs/OLLAMA.md`.

**Context budget math** (in `dependencies.py`):

```
reserved = OLLAMA_NUM_PREDICT + PROMPT_OVERHEAD_TOKENS          # 256 + 150 = 406
budget   = (OLLAMA_CONTEXT_LENGTH - reserved) * CONTEXT_SAFETY_MARGIN
         = (2048 - 406) * 0.85 ≈ 1395 tokens   (floored at 100)
```

That `budget` is the token ceiling for the assembled retrieval context. The
0.85 margin absorbs the tiktoken-vs-qwen3 tokeniser mismatch.

---

## 5. Core infrastructure — `app/core/`

### `config.py`
Covered above.

### `dependencies.py` — the composition root
This is where abstract config becomes concrete objects.

- `build_embedding_provider`, `build_vector_store`, `build_sparse_index`,
  `build_manifest`, `build_reranker`, `build_generation_provider` — each maps a
  `Settings` value to one concrete implementation.
- **`ServiceContainer`** — constructed once from `Settings`. Builds every
  provider and then the four service objects:
  - `IngestionService` — ingest a document end to end
  - `DocumentService` — list / delete / fetch-raw-file
  - `RetrievalService` — hybrid search
  - `GenerationService` — context + prompt + LLM + citations
- `build_services(settings)` → `ServiceContainer`.
- `get_services(request)` reads the container off `request.app.state.services`.
- `get_ingestion_service`, `get_retrieval_service`, … — FastAPI `Depends`
  shims. Routes depend on **these functions**, not on `ServiceContainer`
  directly, so a test can override any single one. In practice overriding
  `get_services` (or passing a `container_factory` to `create_app`) is enough.

Providers that load an ML model (`sentence_transformers`, `CrossEncoderReranker`)
do so **lazily on first use**, so importing `app` or constructing the container
does not eagerly load hundreds of MB.

### `errors.py` — one exception hierarchy
Every application error subclasses `RagError`. `ERROR_STATUS_MAP` maps each to an
HTTP status; `status_code_for(exc)` resolves by `isinstance` (so subclasses
inherit a mapping). `app.main` registers one exception handler that turns any
`RagError` into `{"error": <message>, "type": <ClassName>}` with that status.

| Exception | Status | Raised when |
|---|---|---|
| `OllamaUnavailableError` | 503 | Connection refused / timeout / DNS |
| `OllamaModelNotFoundError` | 503 | Configured model not in `/api/tags` |
| `OllamaGenerationError` | 502 | Ollama reached but `/api/generate` non-200 |
| `DocumentNotFoundError` | 404 | Unknown `document_id` |
| `UnsupportedFileTypeError` | 415 | Not `.pdf` / `.md` / `.markdown` |
| `ConfigurationError` | 500 | Invalid/inconsistent config |
| `EmbeddingError` | 500 | Embedder failed / dim mismatch |
| any other `RagError` | 500 | — |

### `logging.py`
Minimal: one `StreamHandler` to stdout, `"%(asctime)s %(levelname)s %(name)s: %(message)s"`,
idempotent (`if root.handlers: ...`) so test re-imports don't stack handlers.
No external logging service — local-first.

---

## 6. Domain models — `app/models/`

### `domain.py` — entities shared by every layer

| Model | Role | Key fields |
|---|---|---|
| `Document` | An ingested source file | `document_id` (= sha256 of bytes), `filename`, `doc_type`, `page_count`, `ingested_at`, `chunk_count` |
| `Chunk` | A retrievable unit | `chunk_id` (= sha256 of `document_id:index:text`), `document_id`, `chunk_index`, `filename`, `page_start`/`page_end`, `section`, `text`, `token_count`, `char_start`/`char_end` |
| `ScoredChunk` | A chunk + scores at a retrieval stage | `chunk`, `dense_score`, `sparse_score`, `fused_score`, `rerank_score`, `rank` |
| `Citation` | A verified reference in an answer | `document_id`, `filename`, `page`, `section`, `chunk_id`, `quote` (first 120 chars) |
| `TextBlock` | Loader output → chunker input | `text`, `page`, `section`, `is_heading` |
| `ChunkDraft` | Chunker output (pre-id) | `text`, `page_start`/`page_end`, `section`, `token_count`, `char_start`/`char_end` |
| `DocumentFilter` | Retrieval scoping | `document_ids: list[str] \| None` |
| `ManifestEntry` | Idempotency record | `document_id`, `filename`, `chunk_count`, `ingested_at` |
| `GenerationResult` | Raw LLM output | `text`, `model`, `prompt_tokens`, `completion_tokens` |
| `ContextBundle` | Assembled context | `text`, `included_chunks`, `truncated` |
| `IngestionWarning` | Non-fatal ingest issue | `document_id`, `filename`, `page`, `message` |

**The metadata rule:** `document_id`, `chunk_id`, `filename`, `page`, `section`,
and source `text` must survive unchanged from ingestion → retrieval
(`ScoredChunk.chunk`) → the final `Citation`. Every model above carries enough
to satisfy that at its layer.

### `requests.py` / `responses.py`
API-facing shapes. `QueryRequest` validates `question` (min length 1), `top_k`
(1–50, default 5), optional `rerank` override, optional `filters`.
`responses.py` defines `IngestResponse`, `QueryResponse`, `HealthResponse` +
`OllamaHealth`, `DocumentListResponse`, `DeleteDocumentResponse`.

### `app/api/schemas.py`
Thin re-exports of the above for OpenAPI grouping — one source of truth per
shape, no redefinition.

---

## 7. The ingestion pipeline — `app/ingestion/`

Flow: **`load_document` → `clean_text` / `strip_repeated_headers_footers` →
`chunk_text` → `build_document` / `build_chunks` → embed → dual-store upsert →
manifest write.** Orchestrated by `IngestionService.ingest_document`.

### 7.1 Loaders — `loaders.py`

`load_document(file_bytes, filename)` dispatches on extension and returns
`(blocks, page_count, warnings)`.

**PDF (`load_pdf`)** — via PyMuPDF:
- For each page, collect every span's font size; `median_size` = median span size.
- A text block is treated as a **heading** if its largest span is
  `≥ 1.15 × median_size` **and** the block text is `< 120` chars.
- The first heading on a page becomes `current_section`, emitted as its own
  `TextBlock(is_heading=True)`, and stays the active section for following
  blocks until the next heading (carries across pages).
- Pages that yield no extractable text are handed to the configured `OcrEngine`
  (`app/ingestion/ocr.py`); the default `NoOpOcrEngine` returns nothing, so they
  produce an `IngestionWarning` ("likely a scanned image") — **logged, not
  surfaced in the API response**. See §21 for the V2 OCR seam.
- `strip_repeated_headers_footers` runs across all page texts before cleaning.

**Markdown (`load_markdown`)** — a heading-stack line scanner (`^#{1,6}\s+`):
- Maintains a heading stack; `section` is the full breadcrumb, e.g.
  `"Widget Framework > Installation > Requirements"`.
- Paragraphs are flushed on each heading / at EOF.
- **No page numbers** — `page` is always `None` for Markdown blocks.

Anything else → `UnsupportedFileTypeError` (415).

### 7.2 Cleaning — `cleaning.py` (pure string functions, no I/O)

`clean_text`:
- NFKC unicode normalisation
- de-hyphenate words split across a line break (`exam-\nple` → `example`)
- strip trailing whitespace before newlines
- drop lines that are just a bare page number (`^\s*\d{1,4}\s*$`)
- collapse runs of spaces/tabs and 3+ newlines

`strip_repeated_headers_footers(pages, min_repeat_ratio=0.6)`:
- No-op for `< 3` pages.
- Counts the first-2 / last-2 lines of every page; any line appearing on
  `≥ 60%` of pages (min 2) is treated as a running header/footer and removed
  from every page.

### 7.3 Chunking — `chunking.py`

Token-accurate sliding window over the concatenated block text, measured with
`tiktoken` `cl100k_base` (`_ENCODING`). Helpers: `count_tokens`, `encode_tokens`,
`decode_tokens`.

`chunk_text(blocks, *, chunk_size, overlap, min_tokens)` → `list[ChunkDraft]`:
1. Encode every block; keep `token_owner[i]` = which block token `i` came from.
2. Windows: `[start, start+chunk_size)`, advancing by `step = chunk_size - overlap`
   (so 400/60 → step 340, 60 tokens of overlap re-included each time).
3. If the final window is `< min_tokens`, merge it into the previous window
   instead of emitting a fragment.
4. Per window: decode to text; find an approximate `char_start` in the full text
   (best-effort, for debugging/highlighting only — **not** used for citation
   correctness); `page_start`/`page_end` = min/max page of the blocks the window
   spans; `section` = first non-null section among them.

Defaults 400/60 balance citation granularity (point at a paragraph) against
recall, while keeping 5 chunks comfortably inside a 2048-token context.

### 7.4 Metadata / IDs — `metadata.py`

- `compute_document_id(file_bytes) = sha256(bytes).hexdigest()` → content-addressed.
- `compute_chunk_id(document_id, index, text) = sha256(f"{id}:{index}:{text}")` →
  deterministic; re-ingesting identical content produces identical chunk ids.
- `build_document(...)` stamps `ingested_at = datetime.now(UTC)`.
- `build_chunks(document, drafts)` assigns `chunk_index` and links each draft to
  its parent document.

### 7.5 Orchestration — `service.py`

**`Manifest`** — a JSON file (`data/indexes/manifest.json`) mapping
`document_id → ManifestEntry`. Loaded into memory on construction, rewritten
(pretty-printed) on every `put` / `remove`. It is the **source of truth for
"already ingested?"**.

**`raw_file_path(raw_dir, document_id, filename)`** → `data/raw/<document_id><ext>`.

**`IngestionService.ingest_document(file_bytes, filename, source_path="")`** →
`(document, chunks, skipped)`:
1. `load_document` → blocks + page_count.
2. `build_document` → compute `document_id`.
3. Persist raw bytes to `data/raw/<id><ext>` if not already there.
4. **If `manifest.has(document_id)` → return `(document, [], True)`** (skip;
   nothing re-embedded). This is the idempotency short-circuit.
5. `chunk_text` → drafts → `build_chunks`.
6. Embed in batches of `EMBEDDING_BATCH_SIZE`
   (`embedding_provider.embed_documents`).
7. `vector_store.upsert(chunks, vectors)` **and**
   `sparse_index.upsert(chunks)` + `sparse_index.save()`.
8. `manifest.put(ManifestEntry(...))`.

**`DocumentService`**:
- `list_documents()` → `manifest.list()`.
- `delete_document(document_id)` → raises `DocumentNotFoundError` if unknown;
  else deletes from Qdrant + BM25 (+ save), removes the manifest entry, unlinks
  the raw file. Returns count of vector points deleted.
- `raw_file(document_id)` → `(path, doc_type)`; raises `DocumentNotFoundError`
  if the entry or the on-disk file is missing.

**Idempotency summary:** identical bytes → same `document_id` → skipped.
*Changed* content → *new* `document_id`, ingested as a new document; the old one
is **not** auto-removed (call `DELETE /documents/{old_id}` first to replace).

---

## 8. Storage layer — `app/storage/`

### `vector_store.py` — `VectorStore` Protocol
`upsert(chunks, vectors)`, `search(query_vector, top_k, filters=None)`,
`delete_document(document_id) -> int`, `count() -> int`. Retrieval/ingestion
code depends only on this, never on Qdrant types.

### `qdrant_store.py` — `QdrantVectorStore`
- Embedded mode: `QdrantClient(path=...)` — writes straight to a local dir, no
  server, no Docker. **Only one process may hold a given path open at a time.**
- `_ensure_collection()` — creates the collection (size = embedding dim,
  `Distance.COSINE`) if absent.
- Point ids: `uuid5(_ID_NAMESPACE, chunk_id)` — deterministic, so re-upserting
  the same chunk overwrites rather than duplicates. Full `Chunk` is stored as
  the point payload (`model_dump(mode="json")`).
- `search` — optional `DocumentFilter.document_ids` becomes a Qdrant `should`
  filter over the `document_id` payload field; results become `ScoredChunk`
  with `dense_score = point.score` and `rank` = 1-based position.
- `delete_document` — deletes by `document_id` filter; returns
  `count_before - count_after`.
- `scroll_all()` — pages through every stored chunk. Used by
  `scripts/rebuild_index.py` to rebuild BM25 from Qdrant (the source of truth).

### `bm25_store.py` — `SparseIndex` Protocol + `BM25Store`
- Tokeniser: `[a-z0-9]+`, lowercased, tokens of length `> 1`.
- State: an in-memory `list[Chunk]` + a `BM25Okapi` built from their tokenised
  texts. `_rebuild()` recomputes the model from the chunk list.
- `upsert(chunks)` — merges by `chunk_id` (updates existing, appends new), then
  rebuilds.
- `search(query, top_k)` — `bm25.get_scores(tokens)`, argsort desc, top-k →
  `ScoredChunk` with `sparse_score` + `rank`.
- `delete_document(document_id)` — filters the chunk list, rebuilds.
- `save()` / `load()` — **pickle the chunk list** to `BM25_INDEX_PATH`
  (the BM25 model itself is rebuilt on load, not pickled).
- `rebuild_from(chunks)` — discard state, rebuild from a provided source of truth.
- **Limitation:** single pickle file, not safe for concurrent writers. Fine for
  a local single-process app; `rebuild_index.py` is the recovery path if the
  two indexes drift.

### The three persistence artefacts

| Artefact | Path | Written by |
|---|---|---|
| Dense index | `data/indexes/qdrant/` | `QdrantVectorStore` (SQLite-backed) |
| Sparse index | `data/indexes/bm25/index.pkl` | `BM25Store.save()` |
| Idempotency manifest | `data/indexes/manifest.json` | `Manifest._save()` |
| Original files | `data/raw/<document_id><ext>` | `IngestionService` / served by `GET /documents/{id}/file` |

All of `data/` except `eval_dataset.json` is gitignored.

---

## 9. Embeddings — `app/embeddings/`

`base.py` — `EmbeddingProvider` Protocol: attributes `dimension`, `model_name`;
methods `embed_documents(texts)`, `embed_query(text)`, `health_check()`.

| Provider | File | Behaviour |
|---|---|---|
| `SentenceTransformersEmbeddingProvider` | `sentence_transformers.py` | **Default.** Lazy-loads the HF model on first embed; verifies actual output dim == `EMBEDDING_DIM` (else `EmbeddingError`); `encode(..., normalize_embeddings=True)`. ~500 MB–1 GB RSS once loaded. |
| `OllamaEmbeddingProvider` | `ollama.py` | Routes through `POST /api/embed`. No torch. Connection errors → `OllamaUnavailableError`; non-200 → `EmbeddingError`. Requires a manual `ollama pull nomic-embed-text`. |
| `MockEmbeddingProvider` | `mock.py` | 32-d deterministic hash-based vectors. No deps. Used by the offline test suite and `EMBEDDING_PROVIDER=mock`. |

Selected in `build_embedding_provider` from `EMBEDDING_PROVIDER`. `EMBEDDING_DIM`
**must** match the chosen model's real output dimension (384 for `bge-small-en-v1.5`).

---

## 10. The retrieval pipeline — `app/retrieval/`

`RetrievalService.search(query, top_k, *, filters=None, rerank=None)`:

```
dense_results  = DenseRetriever.retrieve(query, RETRIEVAL_CANDIDATE_K, filters)   # 20
sparse_results = SparseRetriever.retrieve(query, RETRIEVAL_CANDIDATE_K)           # 20
fused          = reciprocal_rank_fusion([dense_results, sparse_results], k=RRF_K) # 60
use_rerank     = RERANK_ENABLED if rerank is None else rerank
return reranker.rerank(query, fused, top_k) if use_rerank else fused[:top_k]
```

### `dense.py` — `DenseRetriever`
Embeds the query (`embed_query`), calls `vector_store.search(vec, k, filters)`.
Document filtering is applied **only on the dense side** (Qdrant supports it;
BM25 does not).

### `sparse.py` — `SparseRetriever`
Thin wrapper over `sparse_index.search(query, k)`.

### `fusion.py` — Reciprocal Rank Fusion
```
score(chunk) = Σ over lists containing it of  1 / (RRF_K + rank_in_list)
```
- `RRF_K = 60` dampens the influence of top ranks — a rank-1 and rank-2 hit
  score `1/61` and `1/62`, close together, so agreement across both retrievers
  matters more than being #1 in one.
- A chunk in only one list still scores (lower) — dense-only / sparse-only hits
  are never dropped.
- Output: `ScoredChunk` list re-ranked 1..N, carrying through `dense_score` and
  `sparse_score` plus the new `fused_score`.

### `reranking.py` — optional cross-encoder
`Reranker` Protocol: `rerank(query, chunks, top_k)`.
- `NoOpReranker` — returns `chunks[:top_k]` unchanged (used when
  `RERANK_ENABLED=false`).
- `CrossEncoderReranker` — lazy-loads a `sentence_transformers.CrossEncoder`,
  scores `(query, chunk.text)` pairs, sorts desc, returns the top-k with
  `rerank_score` set and `rank` renumbered.

Selected by `build_reranker` from `RERANK_ENABLED`. The `/query` request can
override per-call via `rerank: true|false`.

---

## 11. The generation pipeline — `app/generation/`

`GenerationService.answer(question, retrieved_chunks)`:

```
context   = build_context(retrieved_chunks, context_budget_tokens)   # § 4 math ≈ 1395
prompt    = build_prompt(question, context)
result    = generation_provider.generate(prompt, system=SYSTEM_PROMPT)
citations = extract_citations(result.text, context.included_chunks)
return AnswerResult(answer, citations, model, context_truncated, chunks_used)
```

### `context.py` — token-budgeted context assembly
- `render_chunk(chunk)` → the exact text put in the prompt, prefixed with the
  **source tag**: `[filename p.N]`, `[filename p.N-M]`, or `[filename]` (no page
  for Markdown), then the chunk text, then a `---` separator.
- `build_context(chunks, budget)` — greedily add rendered chunks while
  `used + piece_tokens ≤ budget`; stop at the first that doesn't fit.
- **Never sends empty context:** if even the top chunk doesn't fit whole, it is
  truncated to the budget and included, with `truncated=True`.
- `truncated` is also `True` whenever fewer chunks were included than retrieved.

### `prompts.py` — the single source of truth for the citation format
- `SYSTEM_PROMPT` — "answer only using the provided context; cite every factual
  claim with the exact source tag shown before each excerpt; if the context
  doesn't contain the answer, say so."
- `CITATION_TAG_PATTERN = \[([^\[\]]+?)(?:\s+p\.(\d+)(?:-(\d+))?)?\]` — used by
  **both** `render_chunk` (implicitly, same format) and `extract_citations`, and
  mirrored in the frontend's `lib/citations.ts`, so the format can't drift.
- `build_prompt(question, context)` → `"Context:\n{...}\nQuestion: {...}\nAnswer:"`.

### Providers
| Provider | File | Behaviour |
|---|---|---|
| `OllamaGenerationProvider` | `ollama.py` | `is_model_available()` guard first (fail fast with `OllamaModelNotFoundError`), then `POST /api/generate` with `stream:false`, `think:<OLLAMA_THINK>`, `keep_alive:<OLLAMA_KEEP_ALIVE>`, `options:{num_ctx, num_predict}`. Maps `response`/`prompt_eval_count`/`eval_count` → `GenerationResult`. Connection → `OllamaUnavailableError`; non-200 → `OllamaGenerationError`. |
| `MockGenerationProvider` | `mock.py` | Echoes back the citation tags found in the prompt as "This is answered by [tag]." — enough to exercise citation extraction end to end with Ollama offline. |

`health_check()` = `GET /api/tags` returns 200 (never raises).
`is_model_available(model)` matches with or without a `:tag` suffix.

### `citations.py` — extraction **and verification**
For each `CITATION_TAG_PATTERN` match in the answer text:
1. Resolve `filename` (and `page`, if present) against
   `context.included_chunks` — the chunks **actually shown to the model**.
2. If `page` given, require `page_start ≤ page ≤ (page_end or page_start)`.
3. **No matching included chunk → the tag is dropped and logged** as
   "unresolvable citation tag". A hallucinated reference never becomes a
   `Citation`.
4. Otherwise emit `Citation(document_id, filename, page, section, chunk_id,
   quote=text[:120])`, de-duplicated on `(filename, page)`.

### `service.py`
`AnswerResult` bundles `answer`, `citations`, `model`, `context_truncated`,
`chunks_used`. Exists so the API route is a pure HTTP translation with no
orchestration logic of its own.

---

## 12. The API layer — `app/api/` + `app/main.py`

### `main.py` — app assembly
`create_app(container_factory=None)`:
- `lifespan`: configure logging; `mkdir -p` the four `data/` dirs; build the
  `ServiceContainer` (production factory, or the caller's) and stash it on
  `app.state.services`.
- Includes the three routers (`health`, `documents`, `query`).
- Registers the `RagError` → JSON exception handler.
- **Last:** if `frontend/dist/` exists, mounts it at `/` as
  `StaticFiles(html=True)`. Because it is mounted last, the API routes take
  precedence; everything else (`/`, `/assets/...`) serves the SPA.
- `app = create_app()` at module scope is what `uvicorn app.main:app` imports.

### `routes_health.py` — `GET /health`
Actively probes: `generation_provider.health_check()`, then (if reachable)
`is_model_available(...)`, then `vector_store.count()`. `status` is `"ok"` only
if all three pass, else `"degraded"`. Never 500s on a degraded backend — the
degraded state is the payload.

### `routes_documents.py`
| Route | Does |
|---|---|
| `POST /documents` | Multipart `file`. Extension-checks (`.pdf/.md/.markdown`) → `UnsupportedFileTypeError` (415). `await file.read()` → `ingestion_service.ingest_document` → `IngestResponse{document, chunks_created, skipped}`. |
| `GET /documents` | `document_service.list_documents()` → rebuilds `Document` views from `ManifestEntry` (note: `page_count` is `None` here — the manifest doesn't store it). |
| `DELETE /documents/{id}` | `document_service.delete_document` → `{document_id, deleted_chunks}`; 404 if unknown. Also unlinks the raw file. |
| `GET /documents/{id}/file` | `FileResponse` of the original bytes (`application/pdf` or `text/markdown`) — used by the frontend's source viewer. 404 if the doc or file is gone. |

### `routes_query.py` — `POST /query`
```
t0; chunks = retrieval_service.search(question, top_k, filters=..., rerank=...)
t1; result = generation_service.answer(question, chunks)
t2
→ QueryResponse{answer, citations, retrieved_chunks, model,
                timing_ms:{retrieval_ms:(t1-t0)*1000, generation_ms:(t2-t1)*1000}}
```

### Error envelope
Every `RagError` → `{"error": "<message>", "type": "<ExceptionClassName>"}` at
the mapped status. Pydantic validation failures (e.g. empty `question`) → 422
in FastAPI's default shape.

Interactive OpenAPI docs at `/docs` when the server is running.

---

## 13. End-to-end walkthroughs

### 13.1 Ingesting `paper.pdf`

```
POST /documents  (multipart: file=paper.pdf)
 └─ routes_documents.upload_document
     ├─ suffix ok? else 415
     ├─ bytes = await file.read()
     └─ IngestionService.ingest_document(bytes, "paper.pdf")
         ├─ load_document → load_pdf
         │    ├─ per page: extract spans, median font size, detect headings
         │    ├─ strip_repeated_headers_footers(all pages)
         │    └─ clean_text(each page) → [TextBlock(page, section, is_heading)]
         ├─ build_document → document_id = sha256(bytes)
         ├─ write data/raw/<document_id>.pdf   (if absent)
         ├─ manifest.has(document_id)?  ── yes ──▶ return (document, [], skipped=True)   ✋
         ├─ chunk_text(blocks, 400, 60, 40) → [ChunkDraft]
         ├─ build_chunks(document, drafts) → [Chunk]  (chunk_id per chunk)
         ├─ embed_documents(texts) in batches of 32 → vectors
         ├─ qdrant.upsert(chunks, vectors)
         ├─ bm25.upsert(chunks); bm25.save()
         └─ manifest.put(ManifestEntry(...))
 └─ IngestResponse{document, chunks_created=len(chunks), skipped=False}
```

### 13.2 Answering "How does reciprocal rank fusion work?"

```
POST /query  {"question": "...", "top_k": 5, "rerank": null}
 └─ routes_query.query
     ├─ RetrievalService.search(q, 5, filters=None, rerank=None)
     │    ├─ DenseRetriever: embed_query(q) → qdrant.search(vec, 20) → 20 ScoredChunk (dense_score)
     │    ├─ SparseRetriever: bm25.search(q, 20)                      → 20 ScoredChunk (sparse_score)
     │    ├─ reciprocal_rank_fusion([dense, sparse], k=60)           → merged, re-ranked
     │    └─ RERANK_ENABLED=false, rerank=None → return fused[:5]
     ├─ GenerationService.answer(q, chunks)
     │    ├─ build_context(chunks, ~1395) → ContextBundle
     │    │     "[paper.pdf p.2]\n<text>\n---\n[paper.pdf p.3]\n<text>\n---\n..."
     │    ├─ build_prompt(q, context)
     │    ├─ OllamaGenerationProvider.generate(prompt, system=SYSTEM_PROMPT)
     │    │     └─ POST /api/generate {model, prompt, system, stream:false,
     │    │                            think:false, keep_alive:0,
     │    │                            options:{num_ctx:2048, num_predict:256}}
     │    └─ extract_citations(answer_text, context.included_chunks)
     │          └─ keep only tags that resolve to an included chunk
     └─ QueryResponse{answer, citations, retrieved_chunks, model, timing_ms}
```

If Ollama is down: `OllamaUnavailableError` → HTTP 503
`{"error": "...", "type": "OllamaUnavailableError"}`.

---

## 14. The frontend — `frontend/`

A Vite + React 19 SPA. Tailwind v4, TanStack Query for server state, a
shadcn-style component set under `src/components/ui/`, `sonner` for toasts,
`react-pdf` + `react-markdown` for the source viewer.

### Build & serve model
- **Dev:** `npm run dev` on :5173. `vite.config.ts` proxies `/health`,
  `/documents`, `/query` to `http://localhost:8000`, so the frontend calls
  **relative** URLs and there is no CORS config anywhere.
- **Prod:** `npm run build` → `frontend/dist/`, which `app/main.py` mounts at
  `/`. Same origin as the API. `client.ts` deliberately uses relative paths for
  both cases.

### Layout
```
App.tsx
 └─ QueryClientProvider
     └─ AppShell (sidebar + main)
         ├─ sidebar: <UploadDropzone/> + <DocumentList/>
         └─ main:    <ChatPanel/>
     └─ <Toaster/>
```

### Data layer — `src/api/`
- `types.ts` — hand-mirrored copies of the Python request/response models
  ("keep in sync by hand, there is no schema generation").
- `client.ts` — the one HTTP module. `apiFetch` (JSON) / `postForm` (multipart)
  / `fetchText` (raw markdown) / `documentFileUrl(id)`. Non-OK → `ApiError`
  (via `lib/errors.ts`); network failure → `ApiError("Could not reach the
  backend", 0, "NetworkError")`.
- `queries.ts` — TanStack hooks: `useHealth` (poll every 15 s, no retry),
  `useDocuments`, `useUploadDocument` (invalidates `["documents"]` on success),
  `useDeleteDocument`, `useAskQuestion`.

### Chat flow — `src/components/chat/`
- `QueryForm` — textarea (Enter submits, Shift+Enter newline), `Top K` number
  input (1–50), `Rerank` toggle → `onSubmit(question, topK, rerank)`.
- `ChatPanel` — holds `result` and `activeCitation` state. On submit calls
  `useAskQuestion.mutate`; errors become a toast via `friendlyMessage`.
  Renders skeletons while pending, then:
  - `AnswerView` — runs the answer text through `lib/citations.ts::linkifyCitations`,
    which rewrites each resolvable `[filename p.N]` tag into a markdown link with
    a `citation:<index>` href; a custom `react-markdown` link renderer
    intercepts those and calls `onCitationClick` instead of navigating.
  - `CitationList` — the structured `citations[]`, each selectable.
  - `RetrievedChunksPanel` — the raw `retrieved_chunks` with their scores.
  - `TimingBadge` — `timing_ms` + the model name.
- `PdfViewerDialog` — opens on any selected citation. For PDFs: `react-pdf`
  `<Document>/<Page>` from `documentFileUrl(document_id)`, jumps to
  `citation.page`, with prev/next paging. For Markdown: `fetchText` the raw
  file and render with `react-markdown`. This is the "verify the citation"
  affordance.

### Documents — `src/components/documents/`
`UploadDropzone` (drag/drop → `useUploadDocument`) and `DocumentList`
(`useDocuments` → list with delete buttons).

---

## 15. CLI scripts — `scripts/`

All add the repo root to `sys.path` and build a real `ServiceContainer` via
`build_services(get_settings())`, so they exercise the exact production wiring.

| Script | Usage | Purpose |
|---|---|---|
| `check_ollama.py` | `python scripts/check_ollama.py` | Verify Ollama reachable + configured model pulled. Exit 0 / 1. |
| `ingest.py` | `python scripts/ingest.py --path <file-or-dir>` | Ingest one file, or recursively every `.pdf/.md/.markdown` under a dir. Prints `OK`/`SKIP` per file. |
| `query.py` | `python scripts/query.py "your question" [--top-k N]` | One-shot retrieve + answer + print citations. Doubles as an end-to-end smoke test. |
| `rebuild_index.py` | `python scripts/rebuild_index.py` | Rebuild BM25 from `qdrant.scroll_all()` — recovery path for index drift. Does not touch Qdrant. |
| `evaluate.py` | `python scripts/evaluate.py --dataset data/evaluation/eval_dataset.json [--top-k N] [--out-dir path]` | Run the benchmark, write JSON + Markdown reports. |

> Note: `CLAUDE.md` shows `python scripts/ingest.py <path-to-file>` — the script
> actually requires the `--path` flag (`--path <path-to-file>`). Prefix any of
> these with `.venv\Scripts\` on Windows as in `CLAUDE.md`.

---

## 16. Evaluation harness — `app/evaluation/`

Fully **offline and deterministic** — no LLM-judge.

### `dataset.py`
`EvalCase{question, expected_document?, expected_page?, expected_answer_keywords[]}`.
`load_dataset(path)` parses the JSON array. Sample: `data/evaluation/eval_dataset.json`
(3 cases over `sample.pdf` / `sample.md`).

### `metrics.py`
| Metric | Definition |
|---|---|
| `recall_at_k` | 1.0 if any top-k chunk is from `expected_document` (by id or filename), else 0.0 (1.0 if no expected doc). |
| `mrr` | `1 / rank` of the first chunk from `expected_document`, else 0.0. |
| `ndcg_at_k` | Graded-relevance nDCG. Available but **not used** by the default runner (sample labels are binary). |
| `lexical_overlap` | Fraction of `expected_answer_keywords` present (case-insensitive substring) in the answer. |
| `citation_presence` | True if some returned citation matches `expected_document` (and `expected_page` if given); if no expected doc, True iff any citation at all. |

### `benchmark.py`
`run_benchmark(cases, retrieval_service, generation_service, top_k=5)` — per case:
retrieve, generate, score the four metrics → `CaseResult`; then aggregate means
into `BenchmarkReport`.

### `reporting.py`
`write_report(report, out_dir)` → `report_<UTC timestamp>.json` +
`report_<UTC timestamp>.md` (summary means + per-case table). Reports are
gitignored.

Run against a fast mock stack with `GENERATION_PROVIDER=mock` /
`EMBEDDING_PROVIDER=mock` to test the harness without Ollama.

---

## 17. Testing — `tests/`

TDD is a project rule (`CLAUDE.md`): prefer real / in-memory adapters and the
mock providers over mocking internals.

| Suite | What it covers | Markers |
|---|---|---|
| `tests/unit/` | Pure logic — chunking, cleaning, fusion, citation extraction, context budgeting, metrics, errors, config, mock providers, reranking (NoOp) | none (fast) |
| `tests/integration/` | Real embeddings (`test_embeddings_real.py`), live Ollama (`test_ollama_live.py`), Qdrant round-trips, ingestion service, loaders, retrieval service, API-level (`test_api_documents.py`, `test_api_query.py`), benchmark, scripts | `slow`, `live_ollama` |
| `tests/fixtures/` | `sample.pdf`, `sample.md`, `generate_sample_pdf.py` (reportlab) | — |

Markers (`pyproject.toml`):
- `slow` — loads a real ML model (sentence-transformers / cross-encoder).
- `live_ollama` — needs a running Ollama with the model pulled.

Fast loop: `pytest -m "not slow and not live_ollama"`.

Mypy runs strict on `app/` only (`disallow_untyped_defs`), excludes
`scripts/` and `tests/`. Ruff selects `E,F,I,UP,B,SIM`; ignores `E501`
(formatter's job) and `B008` (FastAPI `Depends()` in defaults is the required
pattern).

---

## 18. Setup & running from scratch

### Backend

```powershell
# 1. Python 3.11 venv (pinned — see docs/TROUBLESHOOTING.md for the "why")
py -3.11 -m venv .venv
.venv\Scripts\pip install -e ".[dev]"

# 2. Config
copy .env.example .env        # defaults are sensible; edit if needed

# 3. Ollama (separate install) — pull the generation model (this app never auto-pulls)
ollama pull qwen3:1.7b
.venv\Scripts\python scripts\check_ollama.py    # verify

# 4. Ingest something
.venv\Scripts\python scripts\ingest.py --path tests\fixtures\sample.pdf

# 5. Ask (CLI)
.venv\Scripts\python scripts\query.py "How does reciprocal rank fusion work?"

# 6. Or run the API
.venv\Scripts\uvicorn app.main:app --reload      # http://localhost:8000  (/docs for OpenAPI)
```

First real query is slow (~20–30 s): `OLLAMA_KEEP_ALIVE=0` reloads the model
each call, and the sentence-transformers weights download once from HF. Raise
`OLLAMA_KEEP_ALIVE` if you have RAM to spare.

### Frontend

```powershell
cd frontend
npm install
npm run dev        # http://localhost:5173, proxies API to :8000
# or
npm run build      # -> frontend/dist, then the backend serves it at /
```

### First-run checklist / gotchas
- **Ollama not running** → `/health` reports `degraded`, `/query` → 503. Fix:
  start Ollama, confirm `OLLAMA_BASE_URL`.
- **Model not pulled** → 503 `OllamaModelNotFoundError`. Fix: `ollama pull qwen3:1.7b`.
- **Qdrant lock error** → another process holds `data/indexes/qdrant/`. Only one
  writer at a time — stop the other uvicorn/script.
- **`EMBEDDING_DIM` mismatch** → `EmbeddingError` on first embed. Set it to the
  model's real dimension.

---

## 19. Known limitations & deliberate tradeoffs

(From `docs/ARCHITECTURE.md`, consolidated.)

- **Tokeniser is approximate.** Chunk sizing and context budgeting use tiktoken
  `cl100k_base`, not qwen3's real tokeniser. The `CONTEXT_SAFETY_MARGIN=0.85`
  absorbs the drift.
- **BM25 persistence is a single pickle.** Not concurrency-safe. `rebuild_index.py`
  recovers it from Qdrant (the source of truth) if they diverge.
- **No OCR.** Scanned PDF pages with no extractable text are skipped with a
  logged `IngestionWarning` (not surfaced in the API response). Pre-OCR
  externally if you need them.
- **One-time model downloads** (sentence-transformers, cross-encoder) from
  Hugging Face — separate from the "never auto-pull Ollama models" rule.
- **`page_count` is not in `GET /documents`** — the manifest doesn't store it,
  so list views show `null`.
- **Changed documents aren't auto-replaced** — new bytes → new `document_id`;
  delete the old one first.
- **Embedded Qdrant only** — no server/Docker path wired up (a sketch is in
  `docs/TROUBLESHOOTING.md`).

Memory footprint (CPU-only, rough): sentence-transformers + torch ~0.5–1 GB;
cross-encoder +~80 MB (only if enabled); embedded Qdrant tens of MB; Ollama
`qwen3:1.7b` ~1.4 GB on disk, unloaded between calls at the default settings.

---

## 20. Extension points — "how do I add…"

| Goal | Where | How |
|---|---|---|
| A new document format | `app/ingestion/loaders.py` | Add a `load_<fmt>` returning `list[TextBlock]`; dispatch in `load_document`; extend `_SUPPORTED_SUFFIXES` in `routes_documents.py` and the CLI. See the `document-ingestion` skill. |
| A new embedding backend | `app/embeddings/` | Implement the `EmbeddingProvider` Protocol; add a branch in `build_embedding_provider`; add the enum value to `EMBEDDING_PROVIDER`'s `Literal`. |
| A different vector store | `app/storage/` | Implement `VectorStore`; swap in `build_vector_store`. Nothing in `retrieval/` or `ingestion/` changes. |
| A different LLM host | `app/generation/` | Implement `GenerationProvider`; branch in `build_generation_provider`. |
| Tune retrieval | env only | `RETRIEVAL_CANDIDATE_K`, `RRF_K`, `RERANK_ENABLED`, `CHUNK_SIZE_TOKENS`/`CHUNK_OVERLAP_TOKENS`. Re-ingest after chunk changes. See the `hybrid-retriveal` skill. |
| A new API endpoint | `app/api/` | New `APIRouter`; depend on `get_*_service` shims; `include_router` in `main.py`; raise `RagError` subclasses for failures. |
| A new eval metric | `app/evaluation/metrics.py` + `benchmark.py` | Add the pure function, wire it into `CaseResult` / `BenchmarkReport` / `reporting.py`. |

The `.claude/skills/` directory holds project-specific guidance skills
(`rag-architecture`, `document-ingestion`, `hybrid-retriveal`, `local-ollama`,
…) that go deeper on each subsystem's rules.
```

---

## 21. Document-analysis roadmap — backend plan

The system is evolving from "RAG Q&A" into a **document-analysis** system. The
roadmap ships in three tiers; the canonical, always-current version of this plan
(with the per-tier test plan) lives in **`CLAUDE.md` → "Document-Analysis
Roadmap"**. This section is the narrative companion.

### Guiding constraints

- Incremental, not big-bang. Every tier is additive; layer isolation
  (`ingestion` / `retrieval` / `generation` / `analysis` never import FastAPI or
  each other) is preserved.
- New capabilities enter as a **Protocol + `NoOp*` default + `build_*` factory +
  `ServiceContainer` field + `*_ENABLED` flag** (all default `false`). Flags off
  ⇒ behaviour identical to the previous tier.
- Trustworthiness, citations, and structure beat features when they conflict.
- No orchestration frameworks (LangChain/LlamaIndex). Local resource budget
  unchanged unless a flag is turned on.

### New package — `app/analysis/`

Per-document features that act on an *already-ingested* document rather than one
retrieval turn. Same import rules as `retrieval/` and `generation/`.

| Module | Tier | Role |
|---|---|---|
| `outline.py` | V1 | `build_outline(blocks) -> list[OutlineNode]` — nested TOC from heading blocks. Pure, unit-tested. |
| `extraction.py` | V2 seam | `StructuredExtractor` Protocol + `NoOpStructuredExtractor`. Pull named fields with citations. |
| `compare.py` | V2 seam | `DocumentComparer` Protocol + `NoOpDocumentComparer`. Side-by-side, per-document retrieval into one context. |
| `entities.py` | V3 (planned) | NER + relation extraction over chunks → `GraphStore`. |

### V1 — done (this pass + the one before it)

- **Section-aware ingestion.** `load_pdf` emits *every* detected heading per page
  (not just the first) and threads the running `section`; Markdown keeps the full
  `A > B > C` breadcrumb. This is what makes the outline and section-scoped
  citations possible.
- **Outline.** Extracted by `app/analysis/outline.py`, persisted by
  `IngestionService._write_outline` to `data/processed/<id>.outline.json`,
  rewritten on every ingest so a re-upload backfills documents indexed before the
  feature existed (no re-embed — the manifest short-circuit still fires).
  Served at `GET /documents/{id}/outline`.
- **Citations tied to spans.** `Citation.char_start/char_end` flow chunk → answer
  citation. Correctness still rests on `chunk_id` + `filename` + `page`; the
  offsets are for highlighting.
- **Answer provenance.** `QueryResponse.context` (`ContextInfo`: `chunks_used`,
  `chunk_ids`, `truncated`) reports exactly which retrieved chunks fit the token
  budget and reached the model. `chunk_ids ⊆ retrieved ids` is asserted in tests.
- **`page_count`** surfaced in `GET /documents` via `ManifestEntry.page_count`.

### V2 — architecture hooks in place, implementations pending

All NoOp today; endpoints are live and return truthful `implemented: false`
payloads so the frontend/contract can be built now.

| Capability | Seam | Flag | Endpoint |
|---|---|---|---|
| OCR for scanned pages | `OcrEngine` (`app/ingestion/ocr.py`); `load_pdf` renders empty pages → `ocr_page(png)` | `OCR_ENABLED` | — (ingest-time) |
| Table extraction | `TableExtractor` (`app/ingestion/tables.py`); `IngestionService._write_tables` writes the sidecar | `TABLE_EXTRACTION_ENABLED` | `GET /documents/{id}/tables` |
| Hybrid retrieval | already the default (`retrieval/service.py`) | — | `POST /query` |
| Reranking | `Reranker` / `CrossEncoderReranker` already implemented | `RERANK_ENABLED` | `POST /query` (`rerank` override) |
| Structured extraction | `StructuredExtractor` (`app/analysis/extraction.py`) | `STRUCTURED_EXTRACTION_ENABLED` | `POST /documents/{id}/extract` |
| Cross-document compare | `DocumentComparer` (`app/analysis/compare.py`) | `COMPARE_ENABLED` | `POST /compare` |

Recommended build order: **tables → structured extraction → compare → OCR →
rerank-by-default** (each reuses the previous; OCR is independent and carries the
heaviest dependency).

Router: `app/api/routes_analysis.py`. New request models `ExtractRequest`,
`CompareRequest`; new domain models `Table`, `ExtractionSchema/Field`,
`ExtractedValue`, `StructuredExtractionResult`, `DocumentComparison`.

### V3 — designed, not built

- **`GraphStore` Protocol** under `app/storage/` (local SQLite/NetworkX). Built by
  a post-ingest pass in `app/analysis/entities.py`, every edge keyed by
  `chunk_id` so relationships stay citable.
- **Multi-hop retrieval:** a `RetrievalStrategy` seam in `retrieval/service.py`
  (`single` | `multi_hop`), selected by `RETRIEVAL_STRATEGY`. Expand the query
  along graph edges, retrieve per hop, merge with RRF.
- **Evaluation hooks:** graph-grounded metrics (entity recall, hop precision) in
  `app/evaluation/`, a `--strategy` flag on `scripts/evaluate.py`. Still offline,
  still no LLM-judge.
- **Optional agent loop:** a thin hand-written planner over the existing services
  (retrieve → extract → compare → answer). No framework.

### What this pass changed

`app/analysis/{extraction,compare}.py`, `app/ingestion/{ocr,tables}.py` (new
seams); `IngestionService` writes the tables sidecar and threads the OCR engine;
`app/api/routes_analysis.py` + `/compare`, `/documents/{id}/extract`; config flags
`OCR_ENABLED` / `TABLE_EXTRACTION_ENABLED` / `STRUCTURED_EXTRACTION_ENABLED` /
`COMPARE_ENABLED` and `RAW_STORAGE_PATH` / `PROCESSED_STORAGE_PATH` in
`.env.example`; frontend `types.ts` mirror + a collapsible outline panel per
document + a "N sent to the model" line on the retrieved-chunks panel. Tests:
`tests/unit/test_analysis_seams.py`, `tests/integration/test_api_analysis.py`,
OCR-seam cases in `test_loaders.py`.
