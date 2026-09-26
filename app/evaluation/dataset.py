from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class EvalCase(BaseModel):
    question: str
    expected_document: str | None = None
    expected_page: int | None = None
    expected_answer_keywords: list[str] = Field(default_factory=list)


def load_dataset(path: Path) -> list[EvalCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [EvalCase.model_validate(item) for item in raw]
