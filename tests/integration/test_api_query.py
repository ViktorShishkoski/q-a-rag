from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.dependencies import build_services
from app.main import create_app

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _test_settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        embedding_provider="mock",
        generation_provider="mock",
        rerank_enabled=False,
        qdrant_path=tmp_path / "qdrant",
        qdrant_collection="documents",
        bm25_index_path=tmp_path / "bm25" / "index.pkl",
        manifest_path=tmp_path / "manifest.json",
        raw_storage_path=tmp_path / "raw",
        processed_storage_path=tmp_path / "processed",
        embedding_dim=32,
    )


@pytest.fixture
def client(tmp_path: Path):
    settings = _test_settings(tmp_path)
    container = build_services(settings)
    app = create_app(container_factory=lambda: container)
    with TestClient(app) as c:
        with (FIXTURES / "sample.md").open("rb") as f:
            c.post("/documents", files={"file": ("sample.md", f, "text/markdown")})
        with (FIXTURES / "sample.pdf").open("rb") as f:
            c.post("/documents", files={"file": ("sample.pdf", f, "application/pdf")})
        yield c


def test_query_returns_answer_and_retrieved_chunks(client: TestClient):
    resp = client.post("/query", json={"question": "How does reciprocal rank fusion work?", "top_k": 3})
    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] != ""
    assert len(body["retrieved_chunks"]) > 0
    assert "retrieval_ms" in body["timing_ms"]
    assert "generation_ms" in body["timing_ms"]


def test_query_reports_context_provenance(client: TestClient):
    resp = client.post("/query", json={"question": "How does reciprocal rank fusion work?", "top_k": 3})
    body = resp.json()
    context = body["context"]
    assert context["chunks_used"] >= 1
    assert len(context["chunk_ids"]) == context["chunks_used"]
    retrieved_ids = {sc["chunk"]["chunk_id"] for sc in body["retrieved_chunks"]}
    # every chunk the model saw must be one that was actually retrieved
    assert set(context["chunk_ids"]).issubset(retrieved_ids)
    assert isinstance(context["truncated"], bool)


def test_query_respects_top_k(client: TestClient):
    resp = client.post("/query", json={"question": "widget configuration", "top_k": 1})
    assert resp.status_code == 200
    assert len(resp.json()["retrieved_chunks"]) <= 1


def test_query_missing_question_returns_422(client: TestClient):
    resp = client.post("/query", json={"top_k": 3})
    assert resp.status_code == 422


def test_query_empty_question_returns_422(client: TestClient):
    resp = client.post("/query", json={"question": ""})
    assert resp.status_code == 422
