from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional
from uuid import uuid4

from pydantic import BaseModel, Field

from models.question import Question, VotingResult


SessionStatus = Literal[
    "created",
    "browser_opened",
    "waiting_for_user_auth",
    "scraped",
    "answered",
    "filled",
    "closed",
    "error",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FormSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    url: str
    status: SessionStatus = "created"
    questions: list[Question] = Field(default_factory=list)
    answers: dict[str, VotingResult] = Field(default_factory=dict)
    audit_log: list[dict[str, Any]] = Field(default_factory=list)
    error: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def touch(self) -> None:
        self.updated_at = utc_now()

    def record(self, event: str, payload: dict[str, Any] | None = None) -> None:
        self.audit_log.append(
            {
                "event": event,
                "payload": payload or {},
                "timestamp": utc_now().isoformat(),
            }
        )
        self.touch()
