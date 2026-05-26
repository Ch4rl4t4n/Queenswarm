"""Recipe Marketplace beta snapshot — UGC listings overview (P9 #83)."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.skill_marketplace_ugc import build_marketplace_config
from app.core.config import settings
from app.infrastructure.persistence.models.skill_marketplace_listing import (
    LISTING_APPROVED,
    LISTING_PENDING,
    SkillMarketplaceListing,
)


class RecipeMarketplaceBetaSnapshotOut(BaseModel):
    """Marketplace beta panel snapshot."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    config: dict[str, object] = Field(default_factory=dict)
    approved_count: int = 0
    pending_count: int = 0
    total_listings: int = 0


async def compose_recipe_marketplace_beta_snapshot(session: AsyncSession) -> RecipeMarketplaceBetaSnapshotOut:
    """Aggregate UGC marketplace stats for recipes hub."""

    if not settings.recipe_marketplace_beta_enabled:
        return RecipeMarketplaceBetaSnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
        )

    approved = int(
        await session.scalar(
            select(func.count())
            .select_from(SkillMarketplaceListing)
            .where(SkillMarketplaceListing.status == LISTING_APPROVED),
        )
        or 0,
    )
    pending = int(
        await session.scalar(
            select(func.count())
            .select_from(SkillMarketplaceListing)
            .where(SkillMarketplaceListing.status == LISTING_PENDING),
        )
        or 0,
    )
    total = int(await session.scalar(select(func.count()).select_from(SkillMarketplaceListing)) or 0)

    return RecipeMarketplaceBetaSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        config=build_marketplace_config(),
        approved_count=approved,
        pending_count=pending,
        total_listings=total,
    )


__all__ = ["RecipeMarketplaceBetaSnapshotOut", "compose_recipe_marketplace_beta_snapshot"]
