from app.core.errors import (
    ConfigurationError,
    DocumentNotFoundError,
    OllamaModelNotFoundError,
    OllamaUnavailableError,
    RagError,
    UnsupportedFileTypeError,
    status_code_for,
)


def test_ollama_unavailable_maps_to_503():
    assert status_code_for(OllamaUnavailableError("x")) == 503


def test_ollama_model_not_found_maps_to_503():
    assert status_code_for(OllamaModelNotFoundError("x")) == 503


def test_document_not_found_maps_to_404():
    assert status_code_for(DocumentNotFoundError("x")) == 404


def test_unsupported_file_type_maps_to_415():
    assert status_code_for(UnsupportedFileTypeError("x")) == 415


def test_configuration_error_maps_to_500():
    assert status_code_for(ConfigurationError("x")) == 500


def test_generic_rag_error_maps_to_500():
    assert status_code_for(RagError("x")) == 500
