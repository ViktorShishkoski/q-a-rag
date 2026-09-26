#!/usr/bin/env python
"""Ingest a single file or every .pdf/.md file in a directory."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings  # noqa: E402
from app.core.dependencies import build_services  # noqa: E402
from app.core.errors import UnsupportedFileTypeError  # noqa: E402

_SUFFIXES = (".pdf", ".md", ".markdown")


def _iter_input_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path]
    return sorted(p for p in path.rglob("*") if p.suffix.lower() in _SUFFIXES)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", required=True, type=Path, help="File or directory to ingest")
    args = parser.parse_args()

    if not args.path.exists():
        print(f"FAIL: path does not exist: {args.path}")
        return 1

    settings = get_settings()
    services = build_services(settings)

    files = _iter_input_files(args.path)
    if not files:
        print(f"No .pdf/.md files found under {args.path}")
        return 0

    for file_path in files:
        try:
            file_bytes = file_path.read_bytes()
            document, chunks, skipped = services.ingestion_service.ingest_document(
                file_bytes, file_path.name, source_path=str(file_path)
            )
        except UnsupportedFileTypeError as exc:
            print(f"SKIP {file_path}: {exc}")
            continue

        if skipped:
            print(f"SKIP {file_path.name} (already ingested, document_id={document.document_id[:12]})")
        else:
            print(f"OK   {file_path.name}: {len(chunks)} chunks (document_id={document.document_id[:12]})")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
