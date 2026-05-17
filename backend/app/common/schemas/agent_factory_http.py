"""Lightweight API responses for universal agent runs."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class UniversalAgentRunQueued(BaseModel):
    """Metadata returned when the Celery worker has been handed a backlog id."""

    model_config = ConfigDict(extra="ignore")

    task_id: uuid.UUID
    status: str = Field(default="queued", max_length=32)


class UniversalAgentRunOverlay(BaseModel):
    """Optional prompt/tool overrides appended to Celery payloads without upserting config."""

    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    system_prompt: str | None = Field(default=None)
    user_prompt_template: str | None = Field(default=None, max_length=20_000)
    tools: list[Any] | None = None
    output_format: str | None = Field(default=None, max_length=50)
    output_destination: str | None = Field(default=None, max_length=200)
    output_config: dict[str, Any] | None = None


__all__ = ["UniversalAgentRunOverlay", "UniversalAgentRunQueued"]
