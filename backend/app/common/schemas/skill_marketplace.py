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


class SkillCheckoutRequest(BaseModel):
    """Start Stripe checkout for a premium skill export."""

    model_config = ConfigDict(extra="forbid")

    recipe_id: uuid.UUID


class SkillCheckoutResponse(BaseModel):
    """Checkout session metadata returned to the dashboard."""

    model_config = ConfigDict(extra="forbid")

    status: str
    recipe_id: str
    slug: str
    purchase_id: str | None = None
    checkout_url: str | None = None
    amount_eur_cents: str | None = None
    message: str | None = None


class SkillUnlockStatusResponse(BaseModel):
    """Tenant unlock state for skills marketplace."""

    model_config = ConfigDict(extra="forbid")

    stripe_checkout_ready: bool
    unlocked_recipe_ids: list[str] = Field(default_factory=list)
    premium_price_eur_cents_default: int


class SkillConfirmCheckoutRequest(BaseModel):
    """Finalize unlock after Stripe success redirect."""

    model_config = ConfigDict(extra="forbid")

    checkout_session_id: str = Field(min_length=8, max_length=255)


class SkillConfirmCheckoutResponse(BaseModel):
    """Result of client-side checkout confirmation."""

    model_config = ConfigDict(extra="forbid")

    status: str
    checkout_session_id: str | None = None
    recipe_id: str | None = None
    purchase_id: str | None = None
    payment_status: str | None = None
    message: str | None = None


__all__ = [
    "SkillCheckoutRequest",
    "SkillCheckoutResponse",
    "SkillConfirmCheckoutRequest",
    "SkillConfirmCheckoutResponse",
    "SkillUnlockStatusResponse",
    "VerifiedPollenLeaderboardRow",
]
