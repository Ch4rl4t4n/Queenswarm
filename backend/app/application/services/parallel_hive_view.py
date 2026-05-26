"""Parallel Hive View — multi-bee mission control snapshot (compose-only)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession

SessionStatus = Literal["running", "needs_input", "completed", "failed", "pending"]


class ParallelBeeLaneOut(BaseModel):
    """One bee lane in a parallel session view."""

    model_config = ConfigDict(extra="ignore")

    lane_id: str
    label: str
    status: SessionStatus
    detail: str = ""


class ParallelHiveSessionOut(BaseModel):
    """One supervisor session with inferred bee lanes."""

    model_config = ConfigDict(extra="ignore")

    session_id: str
    goal: str
    status: SessionStatus
    lanes: list[ParallelBeeLaneOut] = Field(default_factory=list)
    merge_ready: bool = False


class ParallelHiveViewSnapshotOut(BaseModel):
    """Mission control snapshot for cockpit."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    active_count: int = 0
    sessions: list[ParallelHiveSessionOut] = Field(default_factory=list)


def _normalize_status(raw: str) -> SessionStatus:
    normalized = raw.strip().lower()
    if normalized in {"running", "needs_input", "completed", "failed", "pending"}:
        return normalized  # type: ignore[return-value]
    return "pending"


def _lanes_from_context(ctx: dict) -> list[ParallelBeeLaneOut]:
    """Infer bee lanes from supervisor context_summary."""

    lanes: list[ParallelBeeLaneOut] = []
    bees = ctx.get("active_bees") or ctx.get("sub_agents") or ctx.get("lanes")
    if isinstance(bees, list):
        for idx, bee in enumerate(bees[:6]):
            if isinstance(bee, dict):
                lanes.append(
                    ParallelBeeLaneOut(
                        lane_id=str(bee.get("id") or f"bee-{idx}"),
                        label=str(bee.get("role") or bee.get("label") or f"Bee {idx + 1}")[:80],
                        status=_normalize_status(str(bee.get("status") or "running")),
                        detail=str(bee.get("detail") or "")[:200],
                    ),
                )
    if not lanes:
        for role in ("researcher", "coder", "critic"):
            lanes.append(
                ParallelBeeLaneOut(
                    lane_id=role,
                    label=role.title(),
                    status="running",
                    detail="Inferred maintainer swarm lane.",
                ),
            )
    return lanes


async def compose_parallel_hive_view_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    limit: int = 6,
) -> ParallelHiveViewSnapshotOut:
    """List recent supervisor sessions with parallel bee lane breakdown."""

    if not settings.operator_control_plane_enabled:
        return ParallelHiveViewSnapshotOut(enabled=False, generated_at=datetime.now(tz=UTC))

    cap = max(1, min(limit, 12))
    rows = list(
        (
            await session.scalars(
                select(SupervisorSession)
                .where(SupervisorSession.tenant_id == tenant_id)
                .order_by(desc(SupervisorSession.created_at))
                .limit(cap),
            )
        ).all(),
    )

    sessions: list[ParallelHiveSessionOut] = []
    active = 0
    for row in rows:
        status = _normalize_status(str(row.status or "pending"))
        if status in {"running", "needs_input"}:
            active += 1
        ctx = dict(row.context_summary or {}) if isinstance(row.context_summary, dict) else {}
        lanes = _lanes_from_context(ctx)
        merge_ready = status == "completed" or bool(ctx.get("merge_ready"))
        sessions.append(
            ParallelHiveSessionOut(
                session_id=str(row.id),
                goal=str(row.goal or "")[:200],
                status=status,
                lanes=lanes,
                merge_ready=merge_ready,
            ),
        )

    return ParallelHiveViewSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        active_count=active,
        sessions=sessions,
    )


__all__ = [
    "ParallelBeeLaneOut",
    "ParallelHiveSessionOut",
    "ParallelHiveViewSnapshotOut",
    "compose_parallel_hive_view_snapshot",
]
