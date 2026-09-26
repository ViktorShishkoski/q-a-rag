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


def test_health_endpoint_ok_with_mock_providers(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["ollama"]["reachable"] is True
    assert body["qdrant"] is True


def test_list_documents_empty_initially(client: TestClient):
    resp = client.get("/documents")
    assert resp.status_code == 200
    assert resp.json()["documents"] == []


def test_upload_markdown_document(client: TestClient):
    with (FIXTURES / "sample.md").open("rb") as f:
        resp = client.post("/documents", files={"file": ("sample.md", f, "text/markdown")})
    assert resp.status_code == 200
    body = resp.json()
    assert body["document"]["filename"] == "sample.md"
    assert body["document"]["doc_type"] == "markdown"
    assert body["chunks_created"] > 0
    assert body["skipped"] is False


def test_upload_pdf_document(client: TestClient):
    with (FIXTURES / "sample.pdf").open("rb") as f:
        resp = client.post("/documents", files={"file": ("sample.pdf", f, "application/pdf")})
    assert resp.status_code == 200
    body = resp.json()
    assert body["document"]["doc_type"] == "pdf"
    assert body["document"]["page_count"] == 3
    assert body["chunks_created"] > 0


def test_upload_unsupported_file_type_returns_415(client: TestClient):
    resp = client.post("/documents", files={"file": ("notes.txt", b"plain text", "text/plain")})
    assert resp.status_code == 415
    assert resp.json()["type"] == "UnsupportedFileTypeError"


def test_reuploading_same_file_is_skipped(client: TestClient):
    with (FIXTURES / "sample.md").open("rb") as f:
        first = client.post("/documents", files={"file": ("sample.md", f, "text/markdown")})
    with (FIXTURES / "sample.md").open("rb") as f:
        second = client.post("/documents", files={"file": ("sample.md", f, "text/markdown")})

    assert first.json()["skipped"] is False
    assert second.json()["skipped"] is True


def test_list_documents_after_upload(client: TestClient):
    with (FIXTURES / "sample.md").open("rb") as f:
        client.post("/documents", files={"file": ("sample.md", f, "text/markdown")})

    resp = client.get("/documents")
    documents = resp.json()["documents"]
    assert len(documents) == 1
    assert documents[0]["filename"] == "sample.md"


def test_delete_document_removes_it(client: TestClient):
    with (FIXTURES / "sample.md").open("rb") as f:
        upload = client.post("/documents", files={"file": ("sample.md", f, "text/markdown")})
    document_id = upload.json()["document"]["document_id"]

    resp = client.delete(f"/documents/{document_id}")
    assert resp.status_code == 200
    assert resp.json()["deleted_chunks"] > 0

    assert client.get("/documents").json()["documents"] == []


def test_delete_nonexistent_document_returns_404(client: TestClient):
    resp = client.delete("/documents/does-not-exist")
    assert resp.status_code == 404
    assert resp.json()["type"] == "DocumentNotFoundError"


def test_get_document_file_returns_raw_bytes(client: TestClient):
    with (FIXTURES / "sample.pdf").open("rb") as f:
        original_bytes = f.read()
    with (FIXTURES / "sample.pdf").open("rb") as f:
        upload = client.post("/documents", files={"file": ("sample.pdf", f, "application/pdf")})
    document_id = upload.json()["document"]["document_id"]

    resp = client.get(f"/documents/{document_id}/file")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content == original_bytes


def test_get_document_file_for_unknown_document_returns_404(client: TestClient):
    resp = client.get("/documents/does-not-exist/file")
    assert resp.status_code == 404
    assert resp.json()["type"] == "DocumentNotFoundError"


def test_get_document_file_after_delete_returns_404(client: TestClient):
    with (FIXTURES / "sample.md").open("rb") as f:
        upload = client.post("/documents", files={"file": ("sample.md", f, "text/markdown")})
    document_id = upload.json()["document"]["document_id"]

    client.delete(f"/documents/{document_id}")

    resp = client.get(f"/documents/{document_id}/file")
    assert resp.status_code == 404


def _upload(client: TestClient, name: str, media: str) -> str:
    with (FIXTURES / name).open("rb") as f:
        resp = client.post("/documents", files={"file": (name, f, media)})
    return resp.json()["document"]["document_id"]


def test_list_documents_includes_page_count_for_pdf(client: TestClient):
    _upload(client, "sample.pdf", "application/pdf")
    documents = client.get("/documents").json()["documents"]
    assert documents[0]["page_count"] == 3


def test_markdown_outline_reflects_heading_hierarchy(client: TestClient):
    document_id = _upload(client, "sample.md", "text/markdown")

    resp = client.get(f"/documents/{document_id}/outline")
    assert resp.status_code == 200
    body = resp.json()
    assert body["document_id"] == document_id

    outline = body["outline"]
    assert [n["title"] for n in outline] == ["Widget Framework"]
    root = outline[0]
    child_titles = [c["title"] for c in root["children"]]
    assert "Installation" in child_titles and "Configuration" in child_titles
    installation = next(c for c in root["children"] if c["title"] == "Installation")
    assert [c["title"] for c in installation["children"]] == ["Requirements"]
    assert installation["children"][0]["section_path"] == (
        "Widget Framework > Installation > Requirements"
    )


def test_pdf_outline_has_numbered_sections_with_pages(client: TestClient):
    document_id = _upload(client, "sample.pdf", "application/pdf")

    outline = client.get(f"/documents/{document_id}/outline").json()["outline"]
    titles = [n["title"] for n in outline]
    assert any("Introduction" in t for t in titles)
    assert any("Method" in t for t in titles)
    assert all(n["page"] is not None for n in outline)


def test_outline_for_unknown_document_returns_404(client: TestClient):
    resp = client.get("/documents/does-not-exist/outline")
    assert resp.status_code == 404
    assert resp.json()["type"] == "DocumentNotFoundError"


def test_outline_removed_after_delete(client: TestClient):
    document_id = _upload(client, "sample.md", "text/markdown")
    client.delete(f"/documents/{document_id}")
    assert client.get(f"/documents/{document_id}/outline").status_code == 404


def test_tables_endpoint_returns_empty_until_extractor_wired(client: TestClient):
    document_id = _upload(client, "sample.pdf", "application/pdf")
    resp = client.get(f"/documents/{document_id}/tables")
    assert resp.status_code == 200
    assert resp.json() == {"document_id": document_id, "tables": []}
