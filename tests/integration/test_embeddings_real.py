import pytest

from app.embeddings.sentence_transformers import SentenceTransformersEmbeddingProvider

pytestmark = pytest.mark.slow


def test_real_sentence_transformer_matches_configured_dimension():
    provider = SentenceTransformersEmbeddingProvider(
        model_name="BAAI/bge-small-en-v1.5", expected_dim=384, batch_size=8
    )
    vectors = provider.embed_documents(["hello world", "reciprocal rank fusion merges ranked lists"])
    assert len(vectors) == 2
    assert len(vectors[0]) == 384
    assert provider.dimension == 384
    assert provider.health_check() is True


def test_real_sentence_transformer_query_embedding_is_similar_for_related_text():
    provider = SentenceTransformersEmbeddingProvider(
        model_name="BAAI/bge-small-en-v1.5", expected_dim=384, batch_size=8
    )
    import math

    def cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        return dot / (na * nb)

    q = provider.embed_query("How does reciprocal rank fusion combine rankings?")
    relevant = provider.embed_documents(
        ["Reciprocal rank fusion merges dense and sparse ranked lists into one score."]
    )[0]
    unrelated = provider.embed_documents(["The weather today is sunny with a light breeze."])[0]

    assert cosine(q, relevant) > cosine(q, unrelated)
