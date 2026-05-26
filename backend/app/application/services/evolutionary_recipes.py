"""Evolutionary Recipes — verified variants compete on pollen fitness (compose-only)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.imitation_v2 import compose_imitation_v2_snapshot
from app.core.config import settings


class EvolutionaryRecipeVariantOut(BaseModel):
    """One recipe variant ranked by imitation fitness."""

    model_config = ConfigDict(extra="ignore")

    recipe_id: str | None
    name: str
    similarity: float
    verified_count: int
    detail: str
    fitness_rank: int


class EvolutionaryRecipesSnapshotOut(BaseModel):
    """Evolutionary recipe competition snapshot for Operator Cockpit."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    verified_outcomes: int = 0
    ready: bool = False
    variants: list[EvolutionaryRecipeVariantOut] = Field(default_factory=list)
    summary: str = ""


async def compose_evolutionary_recipes_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> EvolutionaryRecipesSnapshotOut:
    """Wrap imitation v2 suggestions as evolutionary recipe variants."""

    now = datetime.now(tz=UTC)
    if not settings.operator_control_plane_enabled or not settings.imitation_v2_enabled:
        return EvolutionaryRecipesSnapshotOut(enabled=False, generated_at=now)

    base = await compose_imitation_v2_snapshot(session, tenant_id=tenant_id, limit=6)
    variants = [
        EvolutionaryRecipeVariantOut(
            recipe_id=s.recipe_id,
            name=s.name,
            similarity=s.similarity,
            verified_count=s.verified_count,
            detail=s.detail,
            fitness_rank=idx + 1,
        )
        for idx, s in enumerate(base.suggestions)
    ]
    if not base.ready:
        summary = f"Need {3 - base.verified_outcomes} more verified outcomes before variants compete."
    elif variants:
        summary = f"{len(variants)} variant(s) ranked by pollen fitness — simulate winner first."
    else:
        summary = "No recipe variants yet — complete verified workflows to evolve."

    return EvolutionaryRecipesSnapshotOut(
        enabled=True,
        generated_at=now,
        verified_outcomes=base.verified_outcomes,
        ready=base.ready,
        variants=variants,
        summary=summary,
    )


__all__ = [
    "EvolutionaryRecipeVariantOut",
    "EvolutionaryRecipesSnapshotOut",
    "compose_evolutionary_recipes_snapshot",
]
