from __future__ import annotations

import re
from typing import Any
from uuid import uuid5, NAMESPACE_URL

from pydantic import BaseModel, Field, computed_field


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value).strip()


def stable_id(*parts: str | None) -> str:
    basis = "::".join(normalize_text(part) for part in parts if part)
    return str(uuid5(NAMESPACE_URL, basis or "unknown-field"))


class Question(BaseModel):
    id: str
    question: str
    options: list[str] = Field(default_factory=list)
    type: str = "radio"

    @computed_field
    @property
    def prompt(self) -> str:
        return self.question


class AnswerCandidate(BaseModel):
    question_id: str
    model: str
    option: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""
    raw_response: str = ""


class VotingResult(BaseModel):
    question_id: str
    selected_option: str
    confidence: float
    candidates: list[AnswerCandidate]
    scores: dict[str, float] = Field(default_factory=dict)
