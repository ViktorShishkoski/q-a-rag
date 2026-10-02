# Development guide

Build, test and contribution reference for this repo: commands, code rules, known
gotchas and the roadmap.

## Build, Run, and Dev Commands

### Backend (Python — run from repo root)
- Start the API dev server (auto-reload):
  `.venv\Scripts\uvicorn app.main:app --reload`  → http://localhost:8000 (`/docs` for OpenAPI)
- Check Ollama connection and model:
  `.venv\Scripts\python scripts/check_ollama.py`
- Ingest a file **or a directory** (recursive `.pdf/.md/.markdown`):
  `.venv\Scripts\python scripts/ingest.py --path <file-or-dir>`
- Query via CLI (optional `--top-k N`, default 5):
  `.venv\Scripts\python scripts/query.py "your question"`
- Rebuild the BM25 index from Qdrant:
  `.venv\Scripts\python scripts/rebuild_index.py`
- Evaluate against a dataset (optional `--top-k`, `--out-dir`):
  `.venv\Scripts\python scripts/evaluate.py --dataset data/evaluation/eval_dataset.json`

Entry points: `app/main.py::create_app` (imported as `app.main:app`). Every
`scripts/*.py` builds the real `ServiceContainer` via `build_services(get_settings())`,
so scripts exercise production wiring.

### Frontend (Node — run from `frontend/`)
- Dev server: `npm run dev`  → http://localhost:5173, proxies `/health`, `/documents`, `/query` to `:8000`
- Production build: `npm run build`  → `frontend/dist/`, which `app/main.py` mounts at `/`
- Lint: `npm run lint`  (oxlint)

## Test Commands
- All tests: `.venv\Scripts\pytest`
- Unit only: `.venv\Scripts\pytest tests/unit`
- Integration only: `.venv\Scripts\pytest tests/integration`
- Fast loop (skip real ML model loads + live Ollama): `.venv\Scripts\pytest -m "not slow and not live_ollama"`
- A specific file: `.venv\Scripts\pytest tests/unit/test_chunking.py`

Markers (`pyproject.toml`): `slow` = loads a real sentence-transformers / cross-encoder
model; `live_ollama` = needs a running Ollama with the model pulled. A new test that
loads a model or calls Ollama must carry the matching marker or it breaks the fast loop.

## Linter and Formatter Commands
- Ruff check: `.venv\Scripts\ruff check`
- Ruff auto-fix: `.venv\Scripts\ruff check --fix`
- Ruff format: `.venv\Scripts\ruff format`
- Mypy (type check): `.venv\Scripts\mypy app`

Mypy strict (`disallow_untyped_defs`) covers `app/` **only** — `scripts/` and `tests/`
are excluded. Ruff rule set is `E,F,I,UP,B,SIM`; `E501` (formatter's job) and `B008`
(FastAPI `Depends(...)` in defaults) are ignored — do not re-flag them.

## Codebase Guidelines and Style Rules
- **Type annotations**: all of `app/` must be fully annotated (strict mypy, enforced in `pyproject.toml`).
- **Dependency injection**: providers are built by the `build_*` factories in
  `app/core/dependencies.py` and bundled in `ServiceContainer`. API routes depend on the
  `get_*_service` shims, never on `ServiceContainer` directly, so a test can override one
  provider at a time (or pass `container_factory` to `create_app`). A provider that loads
  an ML model must load it lazily on first use, not at import/construction.
- **Layer isolation**: `app/ingestion`, `app/retrieval`, and `app/generation` must not
  import FastAPI and must not import each other. They communicate only through the Protocol
  interfaces and the service classes — this is what lets `scripts/` and any non-HTTP caller
  reuse them.
- **No orchestration frameworks**: do not add LangChain / LlamaIndex etc.
- **Error handling**: raise subclasses of `RagError` (`app/core/errors.py`); the registered
  handler converts them to `{"error", "type"}` JSON at the mapped status. Add new statuses in
  `ERROR_STATUS_MAP`.
- **Idempotency**: `document_id = sha256(file_bytes)`, tracked in `data/indexes/manifest.json`.
  Do not re-embed a document whose hash is already registered. Changed bytes get a *new*
  `document_id` and the old version is **not** auto-removed — `DELETE /documents/{id}` first
  to replace. Re-ingest after changing any `CHUNK_*` setting; existing chunks are not migrated.
- **Citation format**: `CITATION_TAG_PATTERN` in `app/generation/prompts.py` is the single
  source of truth for `[filename p.N]`. It is mirrored by hand in
  `frontend/src/lib/citations.ts` — change both together.
- **API shapes**: request/response models live in `app/models/` and are re-exported from
  `app/api/schemas.py` (one definition per shape). `frontend/src/api/types.ts` is a
  hand-kept mirror — update it when a shape changes.
- **Adding a document format**: implement `load_<fmt>` in `app/ingestion/loaders.py`,
  dispatch it in `load_document`, and extend **both** `_SUPPORTED_SUFFIXES`
  (`app/api/routes_documents.py`) and `_SUFFIXES` (`scripts/ingest.py`).
- **Adding an embeddings / vector-store / reranker / LLM backend**: implement its Protocol,
  add a branch in the matching `build_*` factory in `app/core/dependencies.py`, and extend
  the relevant `Literal` / env enum.
- **Testing (TDD)**: write the test first; prefer real / in-memory adapters and the `mock`
  providers over mocking internals.

## Known Gotchas
- **Embedded Qdrant is single-writer.** Stop the uvicorn server before running `ingest.py`
  or `rebuild_index.py` — they open the same `data/indexes/qdrant/` directory. "Storage
  folder ... already accessed by another instance" means two writers.
- **Ollama models are never auto-pulled.** `ollama pull qwen3:1.7b` by hand;
  `scripts/check_ollama.py` verifies reachability + model.
- **`EMBEDDING_DIM` must equal the model's real output dimension** (384 for
  `bge-small-en-v1.5`) or the first embed call raises `EmbeddingError`.
- **BM25 and Qdrant can drift.** BM25 is a single pickle rebuilt in memory; Qdrant is the
  source of truth. `scripts/rebuild_index.py` rebuilds BM25 from Qdrant.
- **Tokenisation is approximate.** Chunk sizing and context budgeting use tiktoken
  `cl100k_base` as a stand-in for qwen3's tokeniser; `CONTEXT_SAFETY_MARGIN` absorbs the
  drift — do not swap tokenisers to "fix" it.
- **Python 3.11 only** (`py -3.11 -m venv .venv`) — pinned for wheel availability (torch,
  qdrant-client, sentence-transformers).
- **First real query is slow (~20–30 s)** — the LLM loads into memory (kept for
  `OLLAMA_KEEP_ALIVE=300` s afterwards) and sentence-transformers weights download once
  from Hugging Face. Not a bug.
- **`IngestionWarning`s are logged only** (e.g. scanned page / no OCR) — they are not
  returned by `POST /documents`.

## Document-Analysis Roadmap (V1 / V2 / V3)

The product goal is a **document-analysis system**, not a chat app: reliable ingestion,
preserved structure, cited answers, table/structured extraction, cross-document compare,
and a path to graph/agent features. Priority order when trading off: **trustworthiness &
citations & structure > features**.

New package: **`app/analysis/`** — features that operate on an already-ingested document
rather than a single retrieval turn. Same layer rules as `retrieval/` / `generation/`:
no FastAPI import, called through service/Protocol classes. Members: `outline.py` (V1),
`extraction.py` (V2 seam), `compare.py` (V2 seam).

### V1 — trustworthy one-document Q&A + structure — **done**

| Area | Where | State |
|---|---|---|
| Section-aware ingestion | `ingestion/loaders.py` | PDF emits **every** heading per page + tracks the running section; Markdown carries the `>`-joined breadcrumb. |
| Outline extraction | `app/analysis/outline.py` (`build_outline`, `flatten_outline`) → `OutlineNode` | Pure function over heading blocks; Markdown depth from breadcrumb, PDF depth from numeric prefix (`2.1` → level 2). |
| Outline persistence | `IngestionService._write_outline` → `data/processed/<id>.outline.json` | Rewritten every ingest so a plain re-upload backfills old docs (no re-embed). |
| Outline API | `GET /documents/{id}/outline` → `OutlineResponse` | `[]` when no headings; 404 unknown id. |
| Citations tied to spans | `Citation.char_start/char_end`, carried chunk→citation | Best-effort offsets into cleaned text; correctness still = `chunk_id`+`filename`+`page`. |
| Source-context provenance | `ContextInfo` on `QueryResponse` (`chunks_used`, `chunk_ids`, `truncated`) | Lets a caller show exactly which retrieved chunks reached the model. |
| `page_count` in list view | `ManifestEntry.page_count` → `GET /documents` | Older manifest entries: `null`. |

Tests: `tests/unit/test_outline.py`, `tests/integration/test_api_documents.py`
(outline + provenance), `tests/integration/test_api_query.py::test_query_reports_context_provenance`.

### V2 — richer extraction & retrieval — **seams in place, providers are NoOp**

Every hook is a Protocol + `NoOp*` default + `build_*` factory + `ServiceContainer` field
+ config flag (all default `false`). With the flags off the app is byte-for-byte V1.

| Capability | Protocol / file | Default | Enable flag | To implement |
|---|---|---|---|---|
| OCR scanned pages | `OcrEngine` — `app/ingestion/ocr.py` | `NoOpOcrEngine` (returns `None`) | `OCR_ENABLED` | Implement `ocr_page(png)`; branch in `build_ocr_engine`; lazy model load. `load_pdf` already renders empty pages and calls it. |
| Table extraction | `TableExtractor` — `app/ingestion/tables.py` | `NoOpTableExtractor` (`[]`) | `TABLE_EXTRACTION_ENABLED` | Implement `extract(...)` (PyMuPDF `find_tables`, Camelot, or layout model); `IngestionService._write_tables` already writes the sidecar `GET /documents/{id}/tables` reads. |
| Hybrid retrieval | — | **already the default** (`retrieval/service.py`: dense + sparse + RRF) | — | V2 work here is tuning `RETRIEVAL_CANDIDATE_K` / `RRF_K`, not new code. |
| Reranking | `Reranker` — `retrieval/reranking.py` | `NoOpReranker` | `RERANK_ENABLED` (already wired) | `CrossEncoderReranker` already exists; V2 = enable by default after eval. |
| Structured extraction | `StructuredExtractor` — `app/analysis/extraction.py` | `NoOpStructuredExtractor` (`implemented=False`) | `STRUCTURED_EXTRACTION_ENABLED` | Retrieve per field (scoped by `DocumentFilter`), prompt for JSON, verify citations like `generation/citations.py`. Endpoint `POST /documents/{id}/extract` is live. |
| Cross-document compare | `DocumentComparer` — `app/analysis/compare.py` | `NoOpDocumentComparer` (`implemented=False`) | `COMPARE_ENABLED` | Retrieve from each doc, one shared context, structured diff + citations. Endpoint `POST /compare` is live. |

New models: `Table`, `ExtractionField/Schema`, `ExtractedValue`, `StructuredExtractionResult`,
`DocumentComparison` (`app/models/domain.py`). New router: `app/api/routes_analysis.py`.
Tests: `tests/unit/test_analysis_seams.py`, `tests/integration/test_api_analysis.py`,
`test_loaders.py` (OCR path with a fake engine).

**V2 build order:** table extraction → structured extraction (reuses tables + retrieval) →
compare (reuses structured extraction shape) → OCR (independent, heaviest dep) → rerank-by-default.

### V3 — advanced intelligence — **design only, no code yet**

- **Entity + relationship store.** New `GraphStore` Protocol under `app/storage/`
  (e.g. SQLite/NetworkX locally). Populated in a post-ingest pass in `app/analysis/`
  (`entities.py`): NER + relation extraction over chunks, keyed by `chunk_id` so every
  edge keeps a citation.
- **Multi-hop retrieval.** A `RetrievalStrategy` seam in `retrieval/service.py`
  (`single` vs `multi_hop`): expand the query along graph edges, retrieve per hop,
  merge. Config `RETRIEVAL_STRATEGY`.
- **Evaluation hooks.** Extend `app/evaluation/` with graph-grounded metrics
  (entity recall, hop precision) and a `--strategy` flag on `scripts/evaluate.py`.
  Still offline, still no LLM-judge.
- **Agent loop (optional).** A thin planner over the existing services
  (retrieve → extract → compare → answer). No orchestration framework.

### Per-tier test plan

- **V1:** unit for pure logic (`outline`), integration for every new endpoint + the
  provenance contract. Mock providers, tmp-path dirs, no live Ollama.
- **V2:** each Protocol gets a NoOp contract test (inert + truthful `implemented=False`);
  each endpoint gets a happy-path + 404/422 test; a fake implementation proves the seam
  (see `test_loaders.py` OCR). A real ML backend added later carries the `slow` marker.
- **V3:** graph build tested on a fixture corpus with hand-labelled entities; multi-hop
  tested for hop-count bounds and citation preservation.
