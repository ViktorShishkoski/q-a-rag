"""Smoke tests for the CLI scripts, run as real subprocesses against a
tmp-path-isolated, mock-provider environment (no live Ollama required)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures"
PYTHON = REPO_ROOT / ".venv" / "Scripts" / "python.exe"


def _env(tmp_path: Path) -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "EMBEDDING_PROVIDER": "mock",
            "GENERATION_PROVIDER": "mock",
            "RERANK_ENABLED": "false",
            "EMBEDDING_DIM": "32",
            "QDRANT_PATH": str(tmp_path / "qdrant"),
            "BM25_INDEX_PATH": str(tmp_path / "bm25" / "index.pkl"),
            "MANIFEST_PATH": str(tmp_path / "manifest.json"),
            "RAW_STORAGE_PATH": str(tmp_path / "raw"),
            "PROCESSED_STORAGE_PATH": str(tmp_path / "processed"),
        }
    )
    return env


def _run(args: list[str], tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(PYTHON), *args],
        cwd=REPO_ROOT,
        env=_env(tmp_path),
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_ingest_script_ingests_fixture(tmp_path: Path):
    result = _run(["scripts/ingest.py", "--path", str(FIXTURES / "sample.md")], tmp_path)
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
    assert "sample.md" in result.stdout


def test_ingest_then_query_script(tmp_path: Path):
    ingest_result = _run(["scripts/ingest.py", "--path", str(FIXTURES / "sample.md")], tmp_path)
    assert ingest_result.returncode == 0, ingest_result.stderr

    query_result = _run(["scripts/query.py", "What file configures the framework?"], tmp_path)
    assert query_result.returncode == 0, query_result.stderr
    assert "Answer" in query_result.stdout


def test_evaluate_script_writes_report(tmp_path: Path):
    ingest_result = _run(
        [
            "scripts/ingest.py",
            "--path",
            str(FIXTURES),
        ],
        tmp_path,
    )
    assert ingest_result.returncode == 0, ingest_result.stderr

    out_dir = tmp_path / "eval_out"
    dataset = REPO_ROOT / "data" / "evaluation" / "eval_dataset.json"
    eval_result = _run(
        ["scripts/evaluate.py", "--dataset", str(dataset), "--out-dir", str(out_dir)], tmp_path
    )
    assert eval_result.returncode == 0, eval_result.stderr
    assert "Mean recall" in eval_result.stdout
    assert any(out_dir.glob("report_*.json"))
    assert any(out_dir.glob("report_*.md"))


def test_rebuild_index_script_after_ingest(tmp_path: Path):
    ingest_result = _run(["scripts/ingest.py", "--path", str(FIXTURES / "sample.md")], tmp_path)
    assert ingest_result.returncode == 0, ingest_result.stderr

    rebuild_result = _run(["scripts/rebuild_index.py"], tmp_path)
    assert rebuild_result.returncode == 0, rebuild_result.stderr
    assert "Rebuilt BM25 index" in rebuild_result.stdout


def test_rebuild_index_script_empty_manifest_is_noop(tmp_path: Path):
    result = _run(["scripts/rebuild_index.py"], tmp_path)
    assert result.returncode == 0, result.stderr
    assert "nothing to rebuild" in result.stdout
