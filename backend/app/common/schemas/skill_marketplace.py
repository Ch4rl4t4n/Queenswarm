"""Verified pollen leaderboard HTTP contracts."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field


class VerifiedPollenLeaderboardRow(BaseModel):
    """One ranked bee on the verified pollen board."""

    model_config = ConfigDict(extra="forbid")

    rank: int = Field(ge=1)
    agent_id: uuid.UUID
    agent_name: str
    agent_role: str
    swarm_id: uuid.UUID | None = None
    verified_pollen: float = Field(ge=0.0)
    total_pollen: float = Field(ge=0.0)


class SkillUnlockStatusResponse(BaseModel):
    """Tenant unlock state for skills marketplace."""

    model_config = ConfigDict(extra="forbid")

    checkout_available: bool
    unlocked_recipe_ids: list[str] = Field(default_factory=list)
    premium_price_eur_cents_default: int


__all__ = [
    "SkillUnlockStatusResponse",
    "VerifiedPollenLeaderboardRow",
]
