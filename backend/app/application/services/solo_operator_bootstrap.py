"""Bootstrap solo operator routines — trio lane tags + Bank PO weekly routine."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.queen_maintainer.service import ensure_queen_maintainer_routine
from app.application.services.sentinel_upgrade_backlog import ensure_sentinel_upgrade_routine
from app.application.services.solo_operator_trio import (
    TrioLaneId,
    _lane_from_payload,
    resolve_lane_routine,
    tag_routine_for_trio_lane,
)
from app.application.services.supervisor.routine_service import create_supervisor_routine
from app.core.logging import get_logger
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine

logger = get_logger(__name__)

LIFE_OS_ROUTINE_NAME = "Life OS morning briefing"
BANK_PO_ROUTINE_NAME = "Bank PO weekly brief"

LIFE_OS_GOAL = """\
Life OS morning briefing (verify-first).

Overnight digest + dnešné priority operátora:
1. Prečítaj posledné stalled project signály a overnight dump (ak existuje).
2. Zostav ≤300-word ranný brief: top 3 priority, blockery, 1 win.
3. Navrhni max 2 follow-up tasky do task queue (simulate-only).

Nikdy neposielaj citlivé bank dáta do LLM. Critic APPROVE pred operator_reply po slovensky.
""".strip()

BANK_PO_WEEKLY_GOAL = """\
Bank PO weekly brief (verify-first, no sensitive data).

Týždenný PO checkpoint zo anonymizovaných podkladov:
- PI/sprint status (5 bullets)
- Stakeholder risks + asks
- Backlog reorder návrh (top 5)
- Decisions needed from operator

Pravidlo: žiadne PII, interné bank čísla, nepublic roadmapy. Critic verify → SK summary.
""".strip()

SENTINEL_SCAN_NAME = "Sentinel daily scan"
SENTINEL_SCAN_GOAL = """\
Sentinel HiveMind learning scan: surface 3 verified AI/agent signals
from free sources (RSS, Grokipedia, Wikipedia).
Researcher drafts [INSIGHT] pages; critic verifies before hivemind-candidate ingest.
""".strip()


async def _load_tenant_routines(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> list[SupervisorRoutine]:
    return list(
        (
            await db.scalars(
                select(SupervisorRoutine)
                .where(SupervisorRoutine.tenant_id == tenant_id)
                .order_by(SupervisorRoutine.name.asc()),
            )
        ).all(),
    )


async def _ensure_tagged_lane(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    lane_id: TrioLaneId,
    routines: list[SupervisorRoutine],
    created_by_subject: str | None,
) -> dict[str, Any]:
    """Ensure a trio lane has a bound routine; tag or create as needed."""

    routine, binding = resolve_lane_routine(lane_id=lane_id, routines=routines)
    action = "exists"

    if routine is None and lane_id == "hive_learner":
        await ensure_sentinel_upgrade_routine(
            db,
            tenant_id=tenant_id,
            created_by_subject=created_by_subject,
        )
        routines = await _load_tenant_routines(db, tenant_id=tenant_id)
        routine, binding = resolve_lane_routine(lane_id=lane_id, routines=routines)
        if routine is None:
            routine = await create_supervisor_routine(
                db,
                name=SENTINEL_SCAN_NAME,
                goal_template=SENTINEL_SCAN_GOAL,
                created_by_subject=created_by_subject,
                schedule_kind="cron",
                interval_seconds=None,
                cron_expr="0 6 * * *",
                runtime_mode="durable",
                roles=["researcher", "critic"],
                retrieval_contract="default_v2",
                skills=["context", "execution-studio"],
                context_payload={"simulate_first": True, "solo_trio_lane": "hive_learner"},
                tenant_id=tenant_id,
            )
            action = "created"
            binding = "context_payload"

    if routine is None and lane_id == "life_os":
        routine = await create_supervisor_routine(
            db,
            name=LIFE_OS_ROUTINE_NAME,
            goal_template=LIFE_OS_GOAL,
            created_by_subject=created_by_subject,
            schedule_kind="cron",
            interval_seconds=None,
            cron_expr="0 5 * * *",
            runtime_mode="durable",
            roles=["researcher", "critic"],
            retrieval_contract="default_v2",
            skills=["context", "execution-studio"],
            context_payload={"simulate_first": True, "solo_trio_lane": "life_os"},
            tenant_id=tenant_id,
        )
        action = "created"
        binding = "context_payload"

    if routine is None:
        return {
            "lane_id": lane_id,
            "status": "missing",
            "routine_id": None,
            "binding": binding,
        }

    if _lane_from_payload(dict(routine.context_payload or {})) != lane_id:
        await tag_routine_for_trio_lane(db, routine=routine, lane_id=lane_id)
        if action == "exists":
            action = "tagged"

    return {
        "lane_id": lane_id,
        "status": action,
        "routine_id": str(routine.id),
        "routine_name": routine.name,
        "binding": binding,
    }


async def _ensure_bank_po_weekly_routine(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    created_by_subject: str | None,
) -> dict[str, Any]:
    existing = await db.scalar(
        select(SupervisorRoutine)
        .where(
            SupervisorRoutine.tenant_id == tenant_id,
            SupervisorRoutine.name == BANK_PO_ROUTINE_NAME,
        )
        .limit(1),
    )
    if existing is not None:
        return {
            "status": "exists",
            "routine_id": str(existing.id),
            "routine_name": existing.name,
        }

    row = await create_supervisor_routine(
        db,
        name=BANK_PO_ROUTINE_NAME,
        goal_template=BANK_PO_WEEKLY_GOAL,
        created_by_subject=created_by_subject,
        schedule_kind="cron",
        interval_seconds=None,
        cron_expr="0 7 * * 1",
        runtime_mode="durable",
        roles=["researcher", "critic"],
        retrieval_contract="default_v2",
        skills=["context", "execution-studio"],
        context_payload={"simulate_first": True, "lane": "bank_po"},
        tenant_id=tenant_id,
    )
    return {
        "status": "created",
        "routine_id": str(row.id),
        "routine_name": row.name,
    }


async def ensure_solo_operator_lane_bootstrap(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    created_by_subject: str | None,
) -> dict[str, Any]:
    """Idempotently ensure Queen Maintainer + trio lanes + Bank PO weekly routine."""

    maintainer = await ensure_queen_maintainer_routine(
        db,
        tenant_id=tenant_id,
        created_by_subject=created_by_subject,
        enabled=True,
    )
    if _lane_from_payload(dict(maintainer.context_payload or {})) != "scv_maintainer":
        await tag_routine_for_trio_lane(db, routine=maintainer, lane_id="scv_maintainer")

    routines = await _load_tenant_routines(db, tenant_id=tenant_id)
    lane_results: list[dict[str, Any]] = []
    for lane_id in ("hive_learner", "scv_maintainer", "life_os"):
        if lane_id == "scv_maintainer":
            lane_results.append(
                {
                    "lane_id": lane_id,
                    "status": "exists",
                    "routine_id": str(maintainer.id),
                    "routine_name": maintainer.name,
                    "binding": "context_payload",
                },
            )
            continue
        lane_results.append(
            await _ensure_tagged_lane(
                db,
                tenant_id=tenant_id,
                lane_id=lane_id,  # type: ignore[arg-type]
                routines=routines,
                created_by_subject=created_by_subject,
            ),
        )
        routines = await _load_tenant_routines(db, tenant_id=tenant_id)

    bank_po = await _ensure_bank_po_weekly_routine(
        db,
        tenant_id=tenant_id,
        created_by_subject=created_by_subject,
    )

    bound = sum(1 for row in lane_results if row.get("routine_id"))
    logger.info(
        "solo_operator_bootstrap.complete",
        agent_id="solo_bootstrap",
        swarm_id=str(tenant_id),
        task_id="",
        lanes_bound=bound,
    )

    return {
        "tenant_id": str(tenant_id),
        "lanes_bound": bound,
        "lanes_total": 3,
        "trio_lanes": lane_results,
        "bank_po_weekly": bank_po,
        "queen_maintainer_id": str(maintainer.id),
    }


__all__ = ["ensure_solo_operator_lane_bootstrap"]
