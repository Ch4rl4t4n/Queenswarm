"""Ambient Forager — passive ingest relevance brief (compose-only)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.forager_intelligence_v2 import compose_forager_v2_snapshot
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant


class AmbientForagerItemOut(BaseModel):
    """One morning relevance item from passive scan."""

    model_config = ConfigDict(extra="ignore")

    id: str
    source: str
    title: str
    detail: str
    priority: str = "medium"


class AmbientForagerSnapshotOut(BaseModel):
    """Morning relevance brief from forager + dump-sleep signals."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    item_count: int = 0
    items: list[AmbientForagerItemOut] = Field(default_factory=list)
    connector_gaps: list[str] = Field(default_factory=list)


async def compose_ambient_forager_snapshot(
    session: AsyncSession,
    *,
    tenant: Tenant | None,
    dashboard_user_id: uuid.UUID,
    limit: int = 5,
) -> AmbientForagerSnapshotOut:
    """Combine forager v2 proposals + dump-sleep overnight signals into relevance brief."""

    if not settings.operator_control_plane_enabled:
        return AmbientForagerSnapshotOut(enabled=False, generated_at=datetime.now(tz=UTC))

    items: list[AmbientForagerItemOut] = []
    connector_gaps: list[str] = []

    if settings.forager_intelligence_v2_enabled:
        v2 = await compose_forager_v2_snapshot(session, tenant=tenant, dashboard_user_id=dashboard_user_id)
        connector_gaps = list(v2.connector_gaps or [])
        for idx, row in enumerate(v2.proposals[:limit]):
            items.append(
                AmbientForagerItemOut(
                    id=f"forager-{idx}",
                    source="forager_v2",
                    title=row.target[:120] or row.kind,
                    detail=row.rationale[:300],
                    priority=row.priority,
                ),
            )

    if tenant is not None and settings.dump_sleep_enabled:
        root = dict(tenant.operator_settings or {})
        dump = root.get("dump_sleep") or {}
        if isinstance(dump, dict):
            batches = dump.get("recent_batches")
            if isinstance(batches, list):
                for idx, batch in enumerate(batches[:3]):
                    if not isinstance(batch, dict):
                        continue
                    items.append(
                        AmbientForagerItemOut(
                            id=f"dump-{idx}",
                            source="dump_sleep",
                            title=str(batch.get("label") or "Overnight dump batch")[:120],
                            detail=str(batch.get("summary") or "Pending Dreaming ingest.")[:300],
                            priority="high",
                        ),
                    )

    cap = max(1, min(limit, 8))
    return AmbientForagerSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        item_count=len(items),
        items=items[:cap],
        connector_gaps=connector_gaps[:5],
    )


__all__ = [
    "AmbientForagerItemOut",
    "AmbientForagerSnapshotOut",
    "compose_ambient_forager_snapshot",
]
