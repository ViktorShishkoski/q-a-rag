# Evaluation

## Dataset format

A JSON array of cases (see `data/evaluation/eval_dataset.json`):

```json
[
  {
    "question": "What method combines dense retrieval with a sparse BM25 index?",
    "expected_document": "sample.pdf",
    "expected_page": 2,
    "expected_answer_keywords": ["reciprocal", "rank", "fusion"]
  }
]
```

- `expected_document`: filename or document_id the answer should be grounded
  in (optional - omit or `null` to skip retrieval-grounding checks for that case).
- `expected_page`: optional page number check (PDF only).
- `expected_answer_keywords`: words/phrases expected to appear in the answer
  (case-insensitive substring match).

## Metrics (`app/evaluation/metrics.py`)

- **recall@k** - 1.0 if a chunk from `expected_document` appears in the top-k
  retrieved chunks, else 0.0.
- **MRR** - reciprocal of the rank of the first chunk from `expected_document`.
- **nDCG@k** - available for graded relevance judgements (`ndcg_at_k`), not
  used by the default benchmark runner since the sample dataset only has
  binary expected-document labels.
- **lexical overlap** - fraction of `expected_answer_keywords` present in the
  generated answer text.
- **citation presence** - whether at least one returned citation matches
  `expected_document`/`expected_page`.

No external LLM-judge is used - these are all cheap, deterministic, offline
metrics by design.

## Running

```bash
python scripts/evaluate.py --dataset data/evaluation/eval_dataset.json
```

Add `--top-k N` (default 5) or `--out-dir path` to change retrieval depth or
report location. Requires documents to already be ingested (`scripts/ingest.py`
first) and a working generation provider (real Ollama, or set
`GENERATION_PROVIDER=mock` for a fast dry run of the harness itself).

## Reports

Written to `data/evaluation/report_<UTC timestamp>.json` and `.md`: a summary
of mean metrics plus a per-case table. Neither file is committed to git
(`data/evaluation/*` is gitignored except the sample dataset itself).
