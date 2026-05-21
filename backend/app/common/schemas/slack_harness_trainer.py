"""HTTP contracts for Slack harness trainer."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class SlackTrainerFeedbackRequest(BaseModel):
    """Dashboard or API feedback append (JWT authenticated)."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    feedback: str = Field(..., min_length=4, max_length=4000)
    source: str = Field(default="dashboard", max_length=64)


class SlackTrainerFeedbackResponse(BaseModel):
    """Confirmation after behavioral memory append."""

    model_config = ConfigDict(extra="ignore")

    tenant_id: uuid.UUID
    kind: str
    version: int
    char_count: int
    appended_chars: int
    source: str
    author: str | None = None
    slack_notified: bool = False


__all__ = ["SlackTrainerFeedbackRequest", "SlackTrainerFeedbackResponse"]
