# Ollama integration

## Env vars and defaults

```
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_GENERATION_MODEL=qwen3:1.7b
OLLAMA_CONTEXT_LENGTH=2048
OLLAMA_NUM_PREDICT=256
OLLAMA_NUM_PARALLEL=1
OLLAMA_KEEP_ALIVE=300
OLLAMA_THINK=false
OLLAMA_TIMEOUT_S=60
```

## What the adapter (`app/generation/ollama.py`) actually does

- `health_check()` - `GET /api/tags`, returns `False` on any connection error
  or non-200 status rather than raising.
- `is_model_available(model)` - `GET /api/tags`, checks the model name (with
  or without a `:tag` suffix) against the returned list.
- `generate(prompt, system=...)` - checks `is_model_available` first (fails
  fast with `OllamaModelNotFoundError` rather than letting a vague error
  come back from `/api/generate`), then `POST /api/generate` with:
  ```json
  {
    "model": "qwen3:1.7b",
    "prompt": "...",
    "system": "...",
    "stream": false,
    "think": false,
    "keep_alive": 300,
    "options": { "num_ctx": 2048, "num_predict": 256 }
  }
  ```
  Response fields `response`, `prompt_eval_count`, `eval_count` map to
  `GenerationResult.text/prompt_tokens/completion_tokens`.
- Connection failures raise `OllamaUnavailableError`; a non-200 response from
  `/api/generate` raises `OllamaGenerationError`. All with request timeouts
  (`OLLAMA_TIMEOUT_S`).

### `OLLAMA_NUM_PARALLEL` is not a per-request field

This one is easy to get wrong: Ollama only honors `num_parallel` as an **OS
environment variable set before `ollama serve` starts** - there is no
`/api/generate` request field that controls it. The adapter reads
`OLLAMA_NUM_PARALLEL` from `Settings` purely for documentation/consistency
(e.g. so `.env.example` has one place listing every Ollama-related knob) and
does **not** send it in the request body, because doing so would silently do
nothing and misrepresent what the adapter actually controls. If you want to
change it, set it as a real environment variable for the Ollama process
itself, e.g. (PowerShell) `$env:OLLAMA_NUM_PARALLEL=1; ollama serve`.

### `think: false`

qwen3 is a hybrid-reasoning model that supports a `think` toggle in Ollama's
API. Disabled by default (`OLLAMA_THINK=false`) to save tokens/latency on a
low-resource setup; verified against a live `qwen3:1.7b` instance during
development (`tests/integration/test_ollama_live.py`).

### `keep_alive: 300`

Keeps the model in memory for 5 minutes after the last request (the default),
so only the first query after a pause pays the full model-load cost (~20-30s
on typical consumer hardware for a 1.7B Q4 model). Set `OLLAMA_KEEP_ALIVE=0`
to unload after every call on a memory-constrained machine, or `-1` to keep
it loaded indefinitely.

## Embedding provider tradeoff

| | `EMBEDDING_PROVIDER=sentence_transformers` (default) | `EMBEDDING_PROVIDER=ollama` |
|---|---|---|
| Extra dependency | torch + sentence-transformers (~500MB-1GB RSS once loaded) | None beyond Ollama itself |
| Setup step | None - HF weights auto-download on first use (small, ~130MB for `bge-small-en-v1.5`), cached locally | Manual: `ollama pull nomic-embed-text` (never done automatically by this app) |
| Retrieval quality | Strong on technical/academic text (this project's target corpus) | Good, but not benchmarked against bge-small for this project |
| Batching | Local batched `encode()` calls, fast | One `/api/embed` HTTP round-trip per batch |

Default is `sentence_transformers` because retrieval quality on technical
docs/research papers matters more here than the extra ~500MB, and it needs no
manual Ollama model pull. Switch by setting `EMBEDDING_PROVIDER=ollama` and
`EMBEDDING_OLLAMA_MODEL` (default `nomic-embed-text`) after pulling that model
yourself. `EMBEDDING_DIM` must match the actual output dimension of whichever
provider/model you choose (384 for `bge-small-en-v1.5`; check
`nomic-embed-text`'s dimension if you switch providers).

## Mock provider for offline tests

`app/generation/mock.py::MockGenerationProvider` and
`app/embeddings/mock.py::MockEmbeddingProvider` let the full test suite (and
`GENERATION_PROVIDER=mock`/`EMBEDDING_PROVIDER=mock` in `.env`) run with
Ollama completely offline. The mock generation provider echoes back the
citation tags present in its prompt so citation-extraction logic is
exercised without a live model.
