"""HTTP contracts for bee gamification badges."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class BeeBadgeItem(BaseModel):
    """One earned badge on a bee profile."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    description: str
    tier: str
    emoji: str


class BeeBadgeProfile(BaseModel):
    """Agent row with earned verified-workflow badges."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str
    agent_name: str
    agent_role: str
    swarm_id: str | None = None
    verified_pollen: float = Field(ge=0.0)
    total_pollen: float = Field(ge=0.0)
    performance_pct: int = Field(ge=0, le=100)
    verified_task_count: int = Field(ge=0)
    badges: list[BeeBadgeItem] = Field(default_factory=list)
    badge_count: int = Field(ge=0)


class BeeBadgeCatalogItem(BaseModel):
    """Static badge definition for tooltips."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    description: str
    tier: str
    emoji: str


__all__ = ["BeeBadgeCatalogItem", "BeeBadgeItem", "BeeBadgeProfile"]
