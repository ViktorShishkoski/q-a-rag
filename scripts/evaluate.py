#!/usr/bin/env python
"""Run the evaluation benchmark against a dataset and write a report under
data/evaluation/."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings  # noqa: E402
from app.core.dependencies import build_services  # noqa: E402
from app.evaluation.benchmark import run_benchmark  # noqa: E402
from app.evaluation.dataset import load_dataset  # noqa: E402
from app.evaluation.reporting import write_report  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--out-dir", type=Path, default=Path("data/evaluation"))
    args = parser.parse_args()

    if not args.dataset.exists():
        print(f"FAIL: dataset not found: {args.dataset}")
        return 1

    settings = get_settings()
    services = build_services(settings)

    cases = load_dataset(args.dataset)
    print(f"Running {len(cases)} evaluation cases...")
    report = run_benchmark(cases, services.retrieval_service, services.generation_service, top_k=args.top_k)

    json_path, md_path = write_report(report, args.out_dir)

    print(f"\nMean recall@{args.top_k}: {report.mean_recall_at_k:.3f}")
    print(f"Mean MRR: {report.mean_mrr:.3f}")
    print(f"Mean lexical overlap: {report.mean_lexical_overlap:.3f}")
    print(f"Citation presence rate: {report.citation_presence_rate:.3f}")
    print(f"\nReport written to:\n  {json_path}\n  {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
