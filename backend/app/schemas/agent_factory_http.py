"""Lightweight API responses for universal agent runs."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class UniversalAgentRunQueued(BaseModel):
    """Metadata returned when the Celery worker has been handed a backlog id."""

    model_config = ConfigDict(extra="ignore")

    task_id: uuid.UUID
    status: str = Field(default="queued", max_length=32)


__all__ = ["UniversalAgentRunQueued"]
