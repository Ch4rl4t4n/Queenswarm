"""Cross-swarm knowledge transfer — recipe suggestions across domains (P8)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.recipe_chroma_bridge import search_recipes_semantic
from app.core.config import settings

DOMAIN_QUERIES: dict[str, str] = {
    "trading": "polymarket paper trading risk verified workflow",
    "marketing": "social publish content flywheel marketing ops",
    "life_os": "morning briefing stalled projects overnight dump",
    "exec": "executive assistant inbox triage calendar",
}


class CrossSwarmRecipeSuggestionOut(BaseModel):
    """One cross-domain recipe suggestion."""

    model_config = ConfigDict(extra="ignore")

    recipe_id: str | None
    name: str
    source_domain: str
    target_domain: str
    similarity: float
    rationale: str


class CrossSwarmKnowledgeSnapshotOut(BaseModel):
    """Snapshot for cross-swarm transfer panel."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    source_domain: str
    suggestions: list[CrossSwarmRecipeSuggestionOut] = Field(default_factory=list)


async def compose_cross_swarm_knowledge_snapshot(
    session: AsyncSession,
    *,
    source_domain: str = "trading",
    target_domain: str = "marketing",
    limit: int = 5,
) -> CrossSwarmKnowledgeSnapshotOut:
    """Suggest verified recipes from source domain applicable to target domain."""

    if not settings.cross_swarm_knowledge_enabled:
        return CrossSwarmKnowledgeSnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            source_domain=source_domain,
        )

    query = f"{DOMAIN_QUERIES.get(source_domain, source_domain)} apply to {target_domain}"
    hits = await search_recipes_semantic(session, query=query, limit=max(3, min(limit, 10)))

    suggestions: list[CrossSwarmRecipeSuggestionOut] = []
    for hit in hits:
        name = hit.postgres_row.name if hit.postgres_row else (hit.document_preview[:80] or "Recipe")
        rid = str(hit.postgres_recipe_id) if hit.postgres_recipe_id else None
        suggestions.append(
            CrossSwarmRecipeSuggestionOut(
                recipe_id=rid,
                name=str(name)[:120],
                source_domain=source_domain,
                target_domain=target_domain,
                similarity=round(float(hit.similarity), 3),
                rationale=f"Cosine {hit.similarity:.0%} — transfer {source_domain} learnings to {target_domain}.",
            ),
        )

    return CrossSwarmKnowledgeSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        source_domain=source_domain,
        suggestions=suggestions[:limit],
    )


__all__ = ["CrossSwarmKnowledgeSnapshotOut", "compose_cross_swarm_knowledge_snapshot"]
