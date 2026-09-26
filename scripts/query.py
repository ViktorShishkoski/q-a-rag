#!/usr/bin/env python
"""One-shot query against the ingested corpus. Prints the answer and
citations to stdout - doubles as a manual end-to-end smoke test."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings  # noqa: E402
from app.core.dependencies import build_services  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question", type=str, help="Question to ask")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()

    settings = get_settings()
    services = build_services(settings)

    chunks = services.retrieval_service.search(args.question, args.top_k)
    result = services.generation_service.answer(args.question, chunks)

    print(f"Question: {args.question}\n")
    print(f"Answer ({result.model}):\n{result.answer}\n")

    if result.citations:
        print("Citations:")
        for c in result.citations:
            page = f" p.{c.page}" if c.page is not None else ""
            print(f"  - {c.filename}{page}: {c.quote!r}")
    else:
        print("Citations: (none)")

    if result.context_truncated:
        print("\nNote: context was truncated to fit the token budget.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
