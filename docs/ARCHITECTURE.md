# Architecture

## Layers and data flow

```
PDF / Markdown file
    -> app/ingestion/loaders.py            (extract text, page/heading structure)
    -> app/ingestion/cleaning.py           (de-hyphenate, strip headers/footers, NFKC)
    -> app/ingestion/chunking.py           (token-accurate sliding window, tiktoken cl100k_base)
    -> app/ingestion/metadata.py           (content-hash IDs -> Document, Chunk)
    -> app/ingestion/service.py            (orchestrates the above, idempotent via manifest)
        -> app/embeddings/*                (EmbeddingProvider.embed_documents)
        -> app/storage/qdrant_store.py     (dense index, embedded local-persistent Qdrant)
        -> app/storage/bm25_store.py       (sparse index, pickled rank_bm25.BM25Okapi)

Query
    -> app/retrieval/dense.py + sparse.py  (top-N from each index)
    -> app/retrieval/fusion.py             (Reciprocal Rank Fusion)
    -> app/retrieval/reranking.py          (optional cross-encoder, RERANK_ENABLED)
    -> app/retrieval/service.py            (orchestrates the above)
    -> app/generation/context.py           (token-budgeted context assembly)
    -> app/generation/prompts.py           (system prompt + citation-tag format)
    -> app/generation/ollama.py            (or mock.py) (LLM call)
    -> app/generation/citations.py         (extract + verify citation tags)
    -> app/generation/service.py           (orchestrates the above)
    -> app/api/routes_query.py             (thin HTTP translation only)
```

Ingestion, retrieval, generation, and the API are independent packages that only
talk to each other through the Protocol interfaces below and through the
service classes (`IngestionService`, `RetrievalService`, `GenerationService`,
`DocumentService`). Nothing in `retrieval/` or `generation/` imports FastAPI;
nothing in `ingestion/` knows what an LLM is. This is what lets a future UI
process (or any other caller) reuse the exact same services the API uses.

## Swappable interfaces (Protocols)

| Interface | File | Implementations |
|---|---|---|
| `EmbeddingProvider` | `app/embeddings/base.py` | `sentence_transformers.py`, `ollama.py`, `mock.py` |
| `VectorStore` | `app/storage/vector_store.py` | `qdrant_store.py::QdrantVectorStore` |
| `SparseIndex` | `app/storage/bm25_store.py` | `BM25Store` |
| `Reranker` | `app/retrieval/reranking.py` | `CrossEncoderReranker`, `NoOpReranker` |
| `GenerationProvider` | `app/generation/base.py` | `ollama.py::OllamaGenerationProvider`, `mock.py::MockGenerationProvider` |
| `OcrEngine` (V2 seam) | `app/ingestion/ocr.py` | `NoOpOcrEngine` |
| `TableExtractor` (V2 seam) | `app/ingestion/tables.py` | `NoOpTableExtractor` |
| `StructuredExtractor` (V2 seam) | `app/analysis/extraction.py` | `NoOpStructuredExtractor` |
| `DocumentComparer` (V2 seam) | `app/analysis/compare.py` | `NoOpDocumentComparer` |

Every concrete implementation is selected by `app/core/dependencies.py` from
`Settings` (env vars) - swapping a provider is a config change, never a code
change in `ingestion/`, `retrieval/`, or `generation/`.

## Known limitations (deliberate, documented tradeoffs)

- **Tokenizer approximation**: chunk sizing and context-token-budgeting use
  `tiktoken`'s `cl100k_base` encoding as an offline, dependency-light stand-in
  for qwen3's actual tokenizer (not available without an extra download). A
  15% safety margin (`CONTEXT_SAFETY_MARGIN`) is applied when budgeting
  context against `OLLAMA_CONTEXT_LENGTH` to absorb the mismatch.
- **BM25 persistence**: `BM25Store` pickles the chunk list to a single file and
  rebuilds the `BM25Okapi` model in memory on load. Not safe for concurrent
  writers - fine for a local, single-process app. `scripts/rebuild_index.py`
  can always rebuild BM25 from Qdrant (the source of truth) if the two drift.
- **No OCR by default**: scanned PDF pages that PyMuPDF can't extract text from
  are skipped with a logged warning. `app/ingestion/ocr.py` defines the
  `OcrEngine` seam (`load_pdf(..., ocr_engine=...)`) so a real backend can be
  dropped in behind `OCR_ENABLED`; the default `NoOpOcrEngine` keeps today's
  behaviour. See the V2 roadmap in `CLAUDE.md`.
- **One-time model downloads**: `sentence-transformers` (default embeddings)
  and the optional cross-encoder reranker download their weights from
  Hugging Face on first use, cached locally after. This is separate from
  "never auto-pull Ollama models" - see `docs/OLLAMA.md`.

## Memory footprint (rough, CPU-only)

| Component | Approx. RSS | Notes |
|---|---|---|
| sentence-transformers (`bge-small-en-v1.5`) + torch | ~500MB-1GB | Loaded lazily on first embed call |
| Cross-encoder reranker (`ms-marco-MiniLM-L-6-v2`) | +~80MB | Only loaded if `RERANK_ENABLED=true`, lazily |
| Qdrant embedded mode | tens of MB | Grows with corpus size, local disk-backed |
| Ollama (`qwen3:1.7b`, Q4_K_M) | ~1.4GB on disk | Separate process; `OLLAMA_KEEP_ALIVE=0` unloads it after each request |

`EMBEDDING_PROVIDER=ollama` avoids the torch/sentence-transformers memory
cost entirely, at the price of a manual `ollama pull nomic-embed-text` step
and no per-call batching efficiency win from local batched encoding.
