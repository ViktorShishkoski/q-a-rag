import threading
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.dependencies import build_services
from app.main import create_app


def _settings(tmp_path: Path, warmup: bool) -> Settings:
    return Settings(
        _env_file=None,  # type: ignore[call-arg]
        embedding_provider="mock",
        generation_provider="mock",
        rerank_enabled=False,
        qdrant_path=tmp_path / "qdrant",
        bm25_index_path=tmp_path / "bm25" / "index.pkl",
        manifest_path=tmp_path / "manifest.json",
        raw_storage_path=tmp_path / "raw",
        processed_storage_path=tmp_path / "processed",
        embedding_dim=32,
        warmup_on_startup=warmup,
    )


class _SpyGeneration:
    def __init__(self, inner: object) -> None:
        self._inner = inner
        self.called = threading.Event()

    def __getattr__(self, name: str) -> object:
        return getattr(self._inner, name)

    def generate(self, prompt: str, **kwargs: object) -> object:
        self.called.set()
        return self._inner.generate(prompt, **kwargs)  # type: ignore[attr-defined]


class _SpyEmbeddings:
    """Wraps the real mock provider and signals when a query is embedded."""

    def __init__(self, inner: object) -> None:
        self._inner = inner
        self.called = threading.Event()

    def __getattr__(self, name: str) -> object:
        return getattr(self._inner, name)

    def embed_query(self, text: str) -> list[float]:
        self.called.set()
        return self._inner.embed_query(text)  # type: ignore[attr-defined]


def _client_with_spies(
    tmp_path: Path, warmup: bool
) -> tuple[TestClient, _SpyEmbeddings, _SpyGeneration]:
    container = build_services(_settings(tmp_path, warmup))
    embed_spy = _SpyEmbeddings(container.embedding_provider)
    gen_spy = _SpyGeneration(container.generation_provider)
    container.embedding_provider = embed_spy  # type: ignore[assignment]
    container.generation_provider = gen_spy  # type: ignore[assignment]
    return TestClient(create_app(container_factory=lambda: container)), embed_spy, gen_spy


def test_startup_warms_models_in_background(tmp_path: Path):
    client, embed_spy, gen_spy = _client_with_spies(tmp_path, warmup=True)
    with client:
        assert embed_spy.called.wait(timeout=5)
        assert gen_spy.called.wait(timeout=5)


def test_startup_warmup_can_be_disabled(tmp_path: Path):
    client, embed_spy, gen_spy = _client_with_spies(tmp_path, warmup=False)
    with client:
        assert not embed_spy.called.wait(timeout=0.5)
        assert not gen_spy.called.is_set()
