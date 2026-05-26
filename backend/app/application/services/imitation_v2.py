"""Imitation v2 — auto-suggest top neighbor workflow after verified outcomes (P8)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.recipe_chroma_bridge import search_recipes_semantic
from app.core.config import settings
from app.infrastructure.persistence.models.reward import ImitationEvent

MIN_VERIFIED_FOR_SUGGESTION = 3


class ImitationSuggestionOut(BaseModel):
    """One imitation v2 suggestion."""

    model_config = ConfigDict(extra="ignore")

    recipe_id: str | None
    name: str
    similarity: float
    verified_count: int
    detail: str


class ImitationV2SnapshotOut(BaseModel):
    """Imitation engine v2 suggestions snapshot."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    verified_outcomes: int
    ready: bool
    suggestions: list[ImitationSuggestionOut] = Field(default_factory=list)


async def _count_recent_verified_outcomes(session: AsyncSession, *, tenant_id: uuid.UUID | None) -> int:
    """Count verified publish/trade activity events as proxy for imitation readiness."""

    from app.infrastructure.persistence.models.tenant import Tenant

    if tenant_id is None:
        return 0
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        return 0
    from app.application.services.execution_studio_activity import list_execution_activity

    rows = list_execution_activity(tenant, limit=120)
    count = 0
    for row in rows:
        event_type = str(row.get("event_type") or "")
        payload = dict(row.get("payload") or {})
        if event_type.startswith("publish_") and payload.get("ok") is not False:
            count += 1
        if event_type.startswith("trade_") or "paper_fill" in event_type:
            count += 1
    return count


async def compose_imitation_v2_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    task_query: str = "verified workflow trading marketing publish",
    limit: int = 5,
) -> ImitationV2SnapshotOut:
    """Suggest top neighbor recipes when tenant has enough verified outcomes."""

    if not settings.imitation_v2_enabled:
        return ImitationV2SnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            verified_outcomes=0,
            ready=False,
        )

    verified = await _count_recent_verified_outcomes(session, tenant_id=tenant_id)
    ready = verified >= MIN_VERIFIED_FOR_SUGGESTION
    suggestions: list[ImitationSuggestionOut] = []

    if ready:
        hits = await search_recipes_semantic(session, query=task_query, limit=max(3, min(limit, 8)))
        top_imitation_stmt = (
            select(ImitationEvent.recipe_id, func.count())
            .group_by(ImitationEvent.recipe_id)
            .order_by(func.count().desc())
            .limit(3)
        )
        top_rows = list((await session.execute(top_imitation_stmt)).all())
        top_recipe_ids = {str(rid) for rid, _ in top_rows if rid is not None}

        for hit in hits:
            rid = str(hit.postgres_recipe_id) if hit.postgres_recipe_id else None
            name = hit.postgres_row.name if hit.postgres_row else hit.document_preview[:80]
            is_top = rid in top_recipe_ids if rid else False
            suggestions.append(
                ImitationSuggestionOut(
                    recipe_id=rid,
                    name=str(name)[:120],
                    similarity=round(float(hit.similarity), 3),
                    verified_count=verified,
                    detail="Top performer neighbor — simulate before apply."
                    if is_top
                    else f"Match {hit.similarity:.0%} — review before copying.",
                ),
            )

    return ImitationV2SnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        verified_outcomes=verified,
        ready=ready,
        suggestions=suggestions[:limit],
    )


__all__ = ["ImitationV2SnapshotOut", "compose_imitation_v2_snapshot"]
