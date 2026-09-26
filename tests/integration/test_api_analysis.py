"""V2 analysis endpoints: live, validated, and truthfully reporting that the
real providers are not wired yet (NoOp -> implemented: false)."""

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
        yield c


def _upload(client: TestClient, name: str, media: str) -> str:
    with (FIXTURES / name).open("rb") as f:
        resp = client.post("/documents", files={"file": (name, f, media)})
    return resp.json()["document"]["document_id"]


def test_extract_returns_not_implemented_payload(client: TestClient):
    document_id = _upload(client, "sample.md", "text/markdown")
    resp = client.post(
        f"/documents/{document_id}/extract",
        json={"schema": {"fields": [{"name": "title", "description": "the document title"}]}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["document_id"] == document_id
    assert body["implemented"] is False
    assert body["values"] == []


def test_extract_unknown_document_returns_404(client: TestClient):
    resp = client.post(
        "/documents/does-not-exist/extract",
        json={"schema": {"fields": []}},
    )
    assert resp.status_code == 404
    assert resp.json()["type"] == "DocumentNotFoundError"


def test_compare_returns_not_implemented_payload(client: TestClient):
    a = _upload(client, "sample.md", "text/markdown")
    b = _upload(client, "sample.pdf", "application/pdf")
    resp = client.post(
        "/compare", json={"document_ids": [a, b], "question": "which mentions widgets?"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["document_ids"] == [a, b]
    assert body["implemented"] is False
    assert body["summary"] == ""


def test_compare_requires_at_least_two_ids(client: TestClient):
    a = _upload(client, "sample.md", "text/markdown")
    resp = client.post("/compare", json={"document_ids": [a]})
    assert resp.status_code == 422


def test_compare_unknown_document_returns_404(client: TestClient):
    a = _upload(client, "sample.md", "text/markdown")
    resp = client.post("/compare", json={"document_ids": [a, "nope"]})
    assert resp.status_code == 404


def test_tables_sidecar_written_empty_on_ingest(client: TestClient):
    document_id = _upload(client, "sample.pdf", "application/pdf")
    resp = client.get(f"/documents/{document_id}/tables")
    assert resp.status_code == 200
    assert resp.json() == {"document_id": document_id, "tables": []}
