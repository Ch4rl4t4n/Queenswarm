"""HTTP contracts for UGC skill marketplace listings."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SkillMarketplaceConfigResponse(BaseModel):
    """Public UGC marketplace policy for submit + curator UI."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    platform_cut_bps: int = Field(ge=2000, le=3000)
    platform_cut_display: str
    price_tiers_cents: list[int] = Field(default_factory=list)


class SkillMarketplaceListingSubmitRequest(BaseModel):
    """Operator submits a verified recipe for curator review."""

    model_config = ConfigDict(extra="forbid")

    recipe_id: uuid.UUID
    price_eur_cents: int = Field(ge=900, le=9900)
    pitch: str | None = Field(default=None, max_length=2000)


class SkillMarketplaceListingRow(BaseModel):
    """One UGC listing row for tenant or curator dashboards."""

    model_config = ConfigDict(extra="forbid")

    id: uuid.UUID
    recipe_id: uuid.UUID
    recipe_name: str
    status: str
    price_eur_cents: int = Field(ge=0)
    platform_cut_bps: int = Field(ge=0)
    publisher_tenant_id: uuid.UUID
    pitch: str | None = None
    curator_note: str | None = None
    submitted_at: datetime
    reviewed_at: datetime | None = None


class SkillMarketplaceReviewRequest(BaseModel):
    """Curator approves or rejects a pending listing."""

    model_config = ConfigDict(extra="forbid")

    action: Literal["approve", "reject"]
    curator_note: str | None = Field(default=None, max_length=2000)


__all__ = [
    "SkillMarketplaceConfigResponse",
    "SkillMarketplaceListingRow",
    "SkillMarketplaceListingSubmitRequest",
    "SkillMarketplaceReviewRequest",
]
