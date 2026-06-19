"""OP3 — Purge zombie four-lane sessions and revoke orphan Celery sub-agent tasks."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.services.four_lane_llm_service import is_four_lane_session
from app.application.services.supervisor_session_discipline import revoke_durable_celery_tasks_for_session
from app.application.services.supervisor.session_service import apply_session_control
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession

logger = structlog.get_logger(__name__)

_STALE_RUNNING = timedelta(hours=6)
_TERMINAL = frozenset({"stopped", "failed", "cancelled", "completed"})


async def cleanup_zombie_supervisor_sessions(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    stale_after_hours: float = 6.0,
) -> dict[str, Any]:
    """Stop stale running four-lane rows and revoke orphan Celery tasks (OP3)."""

    stale_cutoff = datetime.now(tz=UTC) - timedelta(hours=max(1.0, stale_after_hours))
    rows = list(
        (
            await db.scalars(
                select(SupervisorSession)
                .where(SupervisorSession.tenant_id == tenant_id)
                .options(selectinload(SupervisorSession.sub_agents))
                .order_by(SupervisorSession.created_at.desc())
                .limit(200),
            )
        ).all(),
    )

    stopped = 0
    revoked = 0
    skipped = 0
    session_ids: list[str] = []

    for row in rows:
        ctx = dict(row.context_summary or {})
        if not is_four_lane_session(ctx):
            skipped += 1
            continue

        status = str(row.status or "").strip().lower()
        updated = row.updated_at or row.created_at
        is_stale_running = status == "running" and updated is not None and updated < stale_cutoff
        discipline_halt = bool(ctx.get("discipline_halt_at") or ctx.get("critic_failure") or ctx.get("llm_failure"))

        if status in _TERMINAL and status != "completed":
            revoked += await revoke_durable_celery_tasks_for_session(db, session_row=row)
            skipped += 1
            continue

        if is_stale_running or (status == "running" and discipline_halt):
            revoked += await revoke_durable_celery_tasks_for_session(db, session_row=row)
            await apply_session_control(db, session_row=row, action="stop")
            summary = dict(row.context_summary or {})
            summary["zombie_cleanup"] = True
            summary["zombie_cleanup_at"] = datetime.now(tz=UTC).isoformat()
            row.context_summary = summary
            stopped += 1
            session_ids.append(str(row.id))
            logger.info(
                "zombie_session_cleanup.stopped",
                agent_id="zombie_session_cleanup",
                swarm_id=str(tenant_id),
                task_id=str(row.id),
                prior_status=status,
            )

    await db.flush()
    return {
        "ok": True,
        "tenant_id": str(tenant_id),
        "stopped_count": stopped,
        "celery_revoked": revoked,
        "skipped_non_lane": skipped,
        "session_ids": session_ids,
    }


__all__ = ["cleanup_zombie_supervisor_sessions"]
