"""Recipe Library rows surfaced to dashboards (no raw workflow JSON blobs)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RecipeCatalogItem(BaseModel):
    """Lightweight leaderboard representation for imitation + ops."""

    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None = None
    topic_tags: list[str] = Field(default_factory=list)
    success_count: int = 0
    fail_count: int = 0
    avg_pollen_earned: float = 0.0
    embedding_id: str | None = None
    verified_at: datetime | None = None
    last_used_at: datetime | None = None
    is_deprecated: bool = False


__all__ = ["RecipeCatalogItem"]
