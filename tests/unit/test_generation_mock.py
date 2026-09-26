from app.generation.mock import MockGenerationProvider


def test_mock_generation_health_check_and_model_available():
    provider = MockGenerationProvider()
    assert provider.health_check() is True
    assert provider.is_model_available("anything") is True


def test_mock_generation_echoes_citation_tags_present_in_prompt():
    provider = MockGenerationProvider()
    prompt = "Context:\n[paper.pdf p.4]\nSome text\n---\n\nQuestion: What is X?\nAnswer:"
    result = provider.generate(prompt)
    assert "[paper.pdf p.4]" in result.text
    assert result.model == "mock-generation"


def test_mock_generation_no_context_gives_no_answer_text():
    provider = MockGenerationProvider()
    result = provider.generate("Context:\n\nQuestion: What is X?\nAnswer:")
    assert "does not contain the answer" in result.text
