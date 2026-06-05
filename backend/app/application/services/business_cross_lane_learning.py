"""BA7 — Cross-lane learning: verified recipe winners → CBO apply-to-lane suggestions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.cross_swarm_knowledge import compose_cross_swarm_knowledge_snapshot
from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger(__name__)

BusinessLane = Literal["revenue", "marketing", "factory", "ops", "trading", "mission"]

LANE_TRANSFER_PAIRS: tuple[tuple[str, str, BusinessLane], ...] = (
    ("trading", "marketing", "marketing"),
    ("marketing", "factory", "factory"),
    ("factory", "revenue", "revenue"),
    ("life_os", "marketing", "marketing"),
)


class CrossLaneSuggestionOut(BaseModel):
    """One recipe transfer suggestion for a business lane."""

    model_config = ConfigDict(extra="ignore")

    id: str
    recipe_id: str | None
    recipe_name: str
    source_domain: str
    target_domain: str
    target_lane: BusinessLane
    similarity: float
    rationale: str
    href: str | None = None


class BusinessCrossLaneLearningOut(BaseModel):
    """BA7 rollup for CBO."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    suggestions: list[CrossLaneSuggestionOut] = Field(default_factory=list)


async def compose_business_cross_lane_learning(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    limit: int = 5,
) -> BusinessCrossLaneLearningOut:
    """Compose cross-lane recipe suggestions (no LLM — semantic recipe search only)."""

    _ = tenant_id
    if not settings.cross_swarm_knowledge_enabled or not settings.business_cross_lane_learning_enabled:
        return BusinessCrossLaneLearningOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
        )

    suggestions: list[CrossLaneSuggestionOut] = []
    for source, target, lane in LANE_TRANSFER_PAIRS:
        snap = await compose_cross_swarm_knowledge_snapshot(
            session,
            source_domain=source,
            target_domain=target,
            limit=2,
        )
        for idx, row in enumerate(snap.suggestions):
            if row.similarity < 0.35:
                continue
            rid = row.recipe_id or f"{source}_{target}_{idx}"
            suggestions.append(
                CrossLaneSuggestionOut(
                    id=f"cross_lane_{rid}",
                    recipe_id=row.recipe_id,
                    recipe_name=row.name,
                    source_domain=row.source_domain,
                    target_domain=row.target_domain,
                    target_lane=lane,
                    similarity=row.similarity,
                    rationale=row.rationale,
                    href=f"/recipes?highlight={row.recipe_id}" if row.recipe_id else "/recipes",
                ),
            )

    suggestions.sort(key=lambda row: row.similarity, reverse=True)
    return BusinessCrossLaneLearningOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        suggestions=suggestions[: max(1, min(limit, 8))],
    )


__all__ = [
    "BusinessCrossLaneLearningOut",
    "CrossLaneSuggestionOut",
    "compose_business_cross_lane_learning",
]
