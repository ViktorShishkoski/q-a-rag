from pathlib import Path

from app.core.config import Settings


def test_ollama_defaults_match_spec(monkeypatch):
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    assert settings.ollama_base_url == "http://localhost:11434"
    assert settings.ollama_generation_model == "qwen3:1.7b"
    assert settings.ollama_context_length == 2048
    assert settings.ollama_num_predict == 256
    assert settings.ollama_num_parallel == 1
    assert settings.ollama_keep_alive == 300
    assert settings.ollama_think is False


def test_embedding_defaults(monkeypatch):
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.embedding_provider == "sentence_transformers"
    assert settings.embedding_model == "BAAI/bge-small-en-v1.5"
    assert settings.embedding_dim == 384


def test_rerank_disabled_by_default():
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.rerank_enabled is False


def test_storage_paths_are_path_objects():
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert isinstance(settings.qdrant_path, Path)
    assert isinstance(settings.bm25_index_path, Path)


def test_env_var_override(monkeypatch):
    monkeypatch.setenv("OLLAMA_GENERATION_MODEL", "custom-model")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.ollama_generation_model == "custom-model"
