import math

from app.embeddings.base import EmbeddingProvider
from app.embeddings.mock import MockEmbeddingProvider


def test_mock_provider_satisfies_protocol():
    assert isinstance(MockEmbeddingProvider(), EmbeddingProvider)


def test_mock_embed_is_deterministic():
    provider = MockEmbeddingProvider()
    a = provider.embed_query("what is reciprocal rank fusion?")
    b = provider.embed_query("what is reciprocal rank fusion?")
    assert a == b


def test_mock_embed_differs_for_different_text():
    provider = MockEmbeddingProvider()
    a = provider.embed_query("apples")
    b = provider.embed_query("orbital mechanics")
    assert a != b


def test_mock_embed_documents_batch_matches_dimension():
    provider = MockEmbeddingProvider()
    vectors = provider.embed_documents(["one", "two", "three"])
    assert len(vectors) == 3
    for v in vectors:
        assert len(v) == provider.dimension


def test_mock_embed_vectors_are_normalized():
    provider = MockEmbeddingProvider()
    vec = provider.embed_query("normalize me")
    norm = math.sqrt(sum(x * x for x in vec))
    assert abs(norm - 1.0) < 1e-6


def test_mock_health_check_always_true():
    assert MockEmbeddingProvider().health_check() is True
