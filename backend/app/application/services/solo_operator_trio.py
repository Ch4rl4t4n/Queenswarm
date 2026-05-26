"""Solo operator trio — lightweight preset group over existing routines (no new hive).

The trio is a **mini-swarm orchestration layer**: three named lanes that resolve to
existing ``SupervisorRoutine`` rows. It does not create sub-swarms, move bees, or
replace the full hive setup.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.supervisor.routine_service import trigger_supervisor_routine_now
from app.core.logging import get_logger
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession

logger = get_logger(__name__)

TrioLaneId = Literal["hive_learner", "scv_maintainer", "life_os"]

TRIO_LANE_META: dict[TrioLaneId, dict[str, str]] = {
    "hive_learner": {
        "label": "Hive Learner",
        "description": "Sentinel researcher+critic scan → verified HiveMind ingest.",
        "swarm_hint": "sentinel-radar",
    },
    "scv_maintainer": {
        "label": "SCV Maintainer",
        "description": "Queen Maintainer tech health → PR-only codebase proposals.",
        "swarm_hint": "queen-maintainer",
    },
    "life_os": {
        "label": "Life OS",
        "description": "Overnight dump / morning priorities briefing.",
        "swarm_hint": "life-os",
    },
}

# Name-pattern fallbacks when ``context_payload.solo_trio_lane`` is unset.
_LANE_NAME_PATTERNS: dict[TrioLaneId, tuple[str, ...]] = {
    "hive_learner": ("sentinel", "hivemind learning", "hive learner"),
    "scv_maintainer": ("queen maintainer", "maintainer", "scv"),
    "life_os": ("life os", "morning briefing", "morning executive", "overnight"),
}


@dataclass(slots=True)
class TrioLaneStatus:
    """Resolved lane binding and last-run telemetry."""

    lane_id: TrioLaneId
    label: str
    description: str
    swarm_hint: str
    routine_id: uuid.UUID | None
    routine_name: str | None
    routine_active: bool
    last_run_at: datetime | None
    last_session_id: uuid.UUID | None
    last_session_status: str | None
    binding: str  # context_payload | name_pattern | missing


def _lane_from_payload(context_payload: dict[str, Any] | None) -> str | None:
    if not isinstance(context_payload, dict):
        return None
    raw = context_payload.get("solo_trio_lane")
    if raw is None:
        return None
    lane = str(raw).strip().lower()
    if lane in TRIO_LANE_META:
        return lane
    return None


def _matches_name_pattern(*, name: str, lane_id: TrioLaneId) -> bool:
    lowered = name.strip().lower()
    return any(token in lowered for token in _LANE_NAME_PATTERNS[lane_id])


async def _latest_session_for_routine(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    routine_id: uuid.UUID,
) -> SupervisorSession | None:
    """Return the most recent supervisor session spawned from a routine."""

    stmt = (
        select(SupervisorSession)
        .where(
            SupervisorSession.tenant_id == tenant_id,
            SupervisorSession.context_summary["routine_id"].astext == str(routine_id),
        )
        .order_by(desc(SupervisorSession.created_at))
        .limit(1)
    )
    return await db.scalar(stmt)


def resolve_lane_routine(
    *,
    lane_id: TrioLaneId,
    routines: list[SupervisorRoutine],
) -> tuple[SupervisorRoutine | None, str]:
    """Pick the best routine for a trio lane from an in-memory routine list."""

    for row in routines:
        if not row.is_active:
            continue
        payload_lane = _lane_from_payload(dict(row.context_payload or {}))
        if payload_lane == lane_id:
            return row, "context_payload"

    for row in routines:
        if not row.is_active:
            continue
        if _matches_name_pattern(name=row.name, lane_id=lane_id):
            return row, "name_pattern"

    return None, "missing"


async def get_solo_trio_status(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, Any]:
    """Return trio lane bindings without mutating hive layout."""

    routines = list(
        (
            await db.scalars(
                select(SupervisorRoutine)
                .where(SupervisorRoutine.tenant_id == tenant_id)
                .order_by(SupervisorRoutine.name.asc()),
            )
        ).all(),
    )

    lanes: list[dict[str, Any]] = []
    bound_count = 0
    for lane_id in TRIO_LANE_META:
        meta = TRIO_LANE_META[lane_id]
        routine, binding = resolve_lane_routine(lane_id=lane_id, routines=routines)
        last_session: SupervisorSession | None = None
        if routine is not None:
            bound_count += 1
            last_session = await _latest_session_for_routine(
                db,
                tenant_id=tenant_id,
                routine_id=routine.id,
            )
        lanes.append(
            {
                "lane_id": lane_id,
                "label": meta["label"],
                "description": meta["description"],
                "swarm_hint": meta["swarm_hint"],
                "routine_id": str(routine.id) if routine is not None else None,
                "routine_name": routine.name if routine is not None else None,
                "routine_active": bool(routine.is_active) if routine is not None else False,
                "last_run_at": routine.last_run_at.isoformat() if routine and routine.last_run_at else None,
                "last_session_id": str(last_session.id) if last_session else None,
                "last_session_status": last_session.status if last_session else None,
                "binding": binding,
            },
        )

    return {
        "kind": "solo_operator_trio",
        "description": (
            "Preset group over existing supervisor routines — not a separate hive. "
            "Build swarms from Swarm Builder templates; routines auto-bind by name or solo_trio_lane tag."
        ),
        "lanes_bound": bound_count,
        "lanes_total": len(TRIO_LANE_META),
        "lanes": lanes,
    }


async def run_solo_trio_cycle(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    lane_ids: list[TrioLaneId] | None = None,
) -> dict[str, Any]:
    """Trigger bound routines sequentially; skip missing lanes with hints."""

    selected: tuple[TrioLaneId, ...] = tuple(lane_ids) if lane_ids else tuple(TRIO_LANE_META.keys())
    routines = list(
        (
            await db.scalars(
                select(SupervisorRoutine).where(
                    SupervisorRoutine.tenant_id == tenant_id,
                    SupervisorRoutine.is_active.is_(True),
                ),
            )
        ).all(),
    )

    triggered: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for lane_id in selected:
        meta = TRIO_LANE_META[lane_id]
        routine, binding = resolve_lane_routine(lane_id=lane_id, routines=routines)
        if routine is None:
            skipped.append(
                {
                    "lane_id": lane_id,
                    "label": meta["label"],
                    "reason": "no_routine",
                    "hint": f"Build '{meta['swarm_hint']}' swarm or tag a routine with solo_trio_lane={lane_id}",
                },
            )
            continue

        session_id = await trigger_supervisor_routine_now(db, routine=routine)
        triggered.append(
            {
                "lane_id": lane_id,
                "label": meta["label"],
                "routine_id": str(routine.id),
                "routine_name": routine.name,
                "binding": binding,
                "session_id": str(session_id),
            },
        )
        logger.info(
            "solo_trio.lane_triggered",
            agent_id=lane_id,
            swarm_id=str(routine.id),
            task_id=str(session_id),
        )

    return {
        "triggered": triggered,
        "skipped": skipped,
        "triggered_at": datetime.now(tz=UTC).isoformat(),
    }


async def tag_routine_for_trio_lane(
    db: AsyncSession,
    *,
    routine: SupervisorRoutine,
    lane_id: TrioLaneId,
) -> None:
    """Explicitly bind a routine to a trio lane via context_payload (optional operator action)."""

    payload = dict(routine.context_payload or {})
    payload["solo_trio_lane"] = lane_id
    routine.context_payload = payload
    await db.flush()


__all__ = [
    "TRIO_LANE_META",
    "TrioLaneId",
    "get_solo_trio_status",
    "resolve_lane_routine",
    "run_solo_trio_cycle",
    "tag_routine_for_trio_lane",
]
