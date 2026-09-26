"""Exception hierarchy for the RAG backend.

Every exception here maps to an HTTP status code via ERROR_STATUS_MAP, wired to
FastAPI exception handlers in app.main. Application code should raise these
(or subclasses) instead of bare Exception/ValueError so API responses stay
consistent regardless of which layer failed.
"""

from __future__ import annotations


class RagError(Exception):
    """Base class for all application-raised errors."""


class OllamaUnavailableError(RagError):
    """Ollama could not be reached (connection refused, timeout, DNS failure)."""


class OllamaModelNotFoundError(RagError):
    """The configured Ollama model is not present in `ollama list` / /api/tags."""


class OllamaGenerationError(RagError):
    """Ollama reached but returned an error response for /api/generate or /api/embed."""


class DocumentNotFoundError(RagError):
    """Requested document_id does not exist in the store."""


class UnsupportedFileTypeError(RagError):
    """Uploaded file is neither PDF nor Markdown."""


class ConfigurationError(RagError):
    """Invalid or inconsistent configuration detected at startup or wiring time."""


class EmbeddingError(RagError):
    """Embedding provider failed to produce vectors."""


ERROR_STATUS_MAP: dict[type[RagError], int] = {
    OllamaUnavailableError: 503,
    OllamaModelNotFoundError: 503,
    OllamaGenerationError: 502,
    DocumentNotFoundError: 404,
    UnsupportedFileTypeError: 415,
    ConfigurationError: 500,
    EmbeddingError: 500,
    RagError: 500,
}


def status_code_for(exc: RagError) -> int:
    for exc_type, status in ERROR_STATUS_MAP.items():
        if isinstance(exc, exc_type):
            return status
    return 500
