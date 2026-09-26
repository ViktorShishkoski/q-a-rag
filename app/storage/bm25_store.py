"""BM25 sparse index. Persisted as a pickle of the chunk list under
BM25_INDEX_PATH; the BM25Okapi model itself is cheap to rebuild in memory on
load(), so it is not pickled. Not safe for concurrent writers - acceptable for
a local, single-process app; see docs/ARCHITECTURE.md for the limitation."""

from __future__ import annotations

import pickle
import re
from pathlib import Path
from typing import Protocol, runtime_checkable

from rank_bm25 import BM25Okapi

from app.models.domain import Chunk, ScoredChunk

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    return [tok for tok in _TOKEN_RE.findall(text.lower()) if len(tok) > 1]


@runtime_checkable
class SparseIndex(Protocol):
    def upsert(self, chunks: list[Chunk]) -> None: ...
    def search(self, query: str, top_k: int) -> list[ScoredChunk]: ...
    def delete_document(self, document_id: str) -> int: ...
    def save(self) -> None: ...
    def load(self) -> None: ...


class BM25Store:
    def __init__(self, index_path: Path) -> None:
        self._index_path = index_path
        self._chunks: list[Chunk] = []
        self._bm25: BM25Okapi | None = None
        if self._index_path.exists():
            self.load()

    def _rebuild(self) -> None:
        if not self._chunks:
            self._bm25 = None
            return
        corpus = [_tokenize(c.text) for c in self._chunks]
        self._bm25 = BM25Okapi(corpus)

    def upsert(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
        existing_ids = {c.chunk_id for c in self._chunks}
        new_by_id = {c.chunk_id: c for c in chunks}

        merged = [new_by_id.get(c.chunk_id, c) for c in self._chunks]
        for chunk_id, chunk in new_by_id.items():
            if chunk_id not in existing_ids:
                merged.append(chunk)
        self._chunks = merged
        self._rebuild()

    def search(self, query: str, top_k: int) -> list[ScoredChunk]:
        if self._bm25 is None or not self._chunks:
            return []
        scores = self._bm25.get_scores(_tokenize(query))
        ranked = sorted(range(len(self._chunks)), key=lambda i: scores[i], reverse=True)[:top_k]
        return [
            ScoredChunk(chunk=self._chunks[i], sparse_score=float(scores[i]), rank=rank)
            for rank, i in enumerate(ranked, start=1)
        ]

    def delete_document(self, document_id: str) -> int:
        before = len(self._chunks)
        self._chunks = [c for c in self._chunks if c.document_id != document_id]
        self._rebuild()
        return before - len(self._chunks)

    def save(self) -> None:
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        with self._index_path.open("wb") as f:
            pickle.dump(self._chunks, f)

    def load(self) -> None:
        with self._index_path.open("rb") as f:
            self._chunks = pickle.load(f)
        self._rebuild()

    def rebuild_from(self, chunks: list[Chunk]) -> None:
        """Discard current state and rebuild the index from a source of truth
        (used by scripts/rebuild_index.py to recover from drift)."""
        self._chunks = list(chunks)
        self._rebuild()
