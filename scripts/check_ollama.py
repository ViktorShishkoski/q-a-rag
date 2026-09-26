#!/usr/bin/env python
"""Check that Ollama is reachable and the configured generation model is
pulled. Exit code 0 = healthy, 1 = unhealthy. Prints a human-readable
summary either way."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import get_settings  # noqa: E402
from app.core.errors import RagError  # noqa: E402
from app.generation.ollama import OllamaGenerationProvider  # noqa: E402


def main() -> int:
    settings = get_settings()
    provider = OllamaGenerationProvider(
        settings.ollama_base_url,
        settings.ollama_generation_model,
        context_length=settings.ollama_context_length,
        num_predict=settings.ollama_num_predict,
        keep_alive=settings.ollama_keep_alive,
        think=settings.ollama_think,
        timeout_s=settings.ollama_timeout_s,
    )

    print(f"Checking Ollama at {settings.ollama_base_url} ...")
    if not provider.health_check():
        print("FAIL: Ollama is not reachable.")
        return 1
    print("OK: Ollama is reachable.")

    try:
        available = provider.is_model_available(settings.ollama_generation_model)
    except RagError as exc:
        print(f"FAIL: could not check model availability: {exc}")
        return 1

    if not available:
        print(
            f"FAIL: model '{settings.ollama_generation_model}' is not pulled. "
            f"Run: ollama pull {settings.ollama_generation_model}"
        )
        return 1

    print(f"OK: model '{settings.ollama_generation_model}' is available.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
