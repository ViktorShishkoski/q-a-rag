from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.evaluation.benchmark import BenchmarkReport


def write_report(report: BenchmarkReport, out_dir: Path) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    json_path = out_dir / f"report_{timestamp}.json"
    json_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

    md_path = out_dir / f"report_{timestamp}.md"
    lines = [
        f"# Evaluation report ({timestamp})",
        "",
        "## Summary",
        "",
        f"- Mean recall@k: {report.mean_recall_at_k:.3f}",
        f"- Mean MRR: {report.mean_mrr:.3f}",
        f"- Mean lexical overlap: {report.mean_lexical_overlap:.3f}",
        f"- Citation presence rate: {report.citation_presence_rate:.3f}",
        "",
        "## Per-case results",
        "",
        "| Question | Recall@k | MRR | Lexical overlap | Citation present |",
        "|---|---|---|---|---|",
    ]
    for r in report.case_results:
        question = r.question.replace("|", "\\|")
        lines.append(
            f"| {question} | {r.recall_at_k:.2f} | {r.mrr:.2f} | {r.lexical_overlap:.2f} | {r.citation_present} |"
        )
    md_path.write_text("\n".join(lines), encoding="utf-8")

    return json_path, md_path
