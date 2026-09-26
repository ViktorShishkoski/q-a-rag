#!/usr/bin/env python
"""Rebuild the BM25 index from whatever chunks currently exist in Qdrant.

Recovery path for drift between the vector store and the sparse index (e.g.
after an interrupted ingestion). Does not touch Qdrant itself - Qdrant is
the source of truth this rebuilds BM25 from.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings  # noqa: E402
from app.core.dependencies import build_services  # noqa: E402
from app.storage.qdrant_store import QdrantVectorStore  # noqa: E402


def main() -> int:
    settings = get_settings()
    services = build_services(settings)

    manifest_entries = services.manifest.list()
    if not manifest_entries:
        print("Manifest is empty - nothing to rebuild. Run scripts/ingest.py first.")
        return 0

    if not isinstance(services.vector_store, QdrantVectorStore):
        print("FAIL: rebuild_index.py requires the Qdrant vector store implementation.")
        return 1

    chunks = services.vector_store.scroll_all()
    services.sparse_index.rebuild_from(chunks)
    services.sparse_index.save()

    print(f"Rebuilt BM25 index from {len(chunks)} chunks across {len(manifest_entries)} documents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
