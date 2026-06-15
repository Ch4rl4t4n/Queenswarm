"""LR3 — Worker crash auto-resume for stale durable sub-agent steps."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.operator_mission_feed import push_mission_feed_event
from app.application.services.supervisor.checkpoint_resume import resume_session_from_last_checkpoint
from app.application.services.supervisor.runtime import append_event
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.supervisor_session import SubAgentSession, SupervisorSession

_logger = get_logger(__name__)

_OPEN_SUPERVISOR_STATUSES: frozenset[str] = frozenset({"running", "pending", "needs_input"})
_MAX_BATCH = 25


class WorkerCrashResumeResult(BaseModel):
    """Outcome counters for one LR3 sweep tick."""

    model_config = ConfigDict(extra="ignore")

    scanned: int = 0
    resumed: int = 0
    skipped_cooldown: int = 0
    skipped_resume_error: int = 0
    notified: int = 0


def derive_worker_crash_stale_cutoff(
    *,
    now: datetime | None = None,
    timeout_sec: int | None = None,
) -> datetime:
    """Return UTC cutoff — sub-agents running before this are considered worker-crash stale."""

    anchor = now or datetime.now(tz=UTC)
    window = int(timeout_sec or settings.worker_crash_stale_timeout_sec)
    return anchor - timedelta(seconds=max(30, window))


def _should_skip_cooldown(summary: dict[str, Any], *, cooldown_sec: int) -> bool:
    last_at = summary.get("last_worker_crash_resume_at")
    if not last_at:
        return False
    try:
        parsed = datetime.fromisoformat(str(last_at).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)
    except ValueError:
        return False
    return (datetime.now(tz=UTC) - parsed).total_seconds() < max(60, cooldown_sec)


async def sweep_stale_durable_sub_agents_for_auto_resume(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None = None,
) -> WorkerCrashResumeResult:
    """Mark crash-stale running sub-agents failed, checkpoint-resume, and notify mission feed."""

    if not settings.worker_crash_auto_resume_enabled:
        return WorkerCrashResumeResult()

    cutoff = derive_worker_crash_stale_cutoff()
    cooldown_sec = int(settings.worker_crash_resume_cooldown_sec)
    result = WorkerCrashResumeResult()

    stmt = (
        select(SubAgentSession, SupervisorSession)
        .join(SupervisorSession, SubAgentSession.supervisor_session_id == SupervisorSession.id)
        .where(
            SubAgentSession.status == "running",
            SubAgentSession.started_at.is_not(None),
            SubAgentSession.started_at < cutoff,
            SupervisorSession.runtime_mode == "durable",
            SupervisorSession.status.in_(tuple(_OPEN_SUPERVISOR_STATUSES)),
        )
        .order_by(SubAgentSession.started_at.asc())
        .limit(_MAX_BATCH)
    )
    if tenant_id is not None:
        stmt = stmt.where(SupervisorSession.tenant_id == tenant_id)

    rows = list((await session.execute(stmt)).all())
    result.scanned = len(rows)

    for sub, sup in rows:
        summary = dict(sup.context_summary or {})
        if _should_skip_cooldown(summary, cooldown_sec=cooldown_sec):
            result.skipped_cooldown += 1
            continue

        sub.status = "failed"
        sub.error_text = (
            "Worker lease expired (likely Celery worker crash). "
            "Auto-resuming from last verified checkpoint."
        )
        sub.completed_at = None

        await append_event(
            session,
            supervisor_session=sup,
            sub_agent=sub,
            event_type="worker_crash_detected",
            message=f"{sub.role} step stale — marking failed and auto-resuming.",
            payload={
                "sub_agent_session_id": str(sub.id),
                "started_at": sub.started_at.isoformat() if sub.started_at else None,
                "stale_cutoff": cutoff.isoformat(),
            },
            level="warning",
        )

        try:
            updated, snapshot, requeued = await resume_session_from_last_checkpoint(
                session,
                session_row=sup,
            )
        except ValueError as exc:
            result.skipped_resume_error += 1
            _logger.warning(
                "worker_crash_auto_resume.resume_failed",
                agent_id="worker_crash_auto_resume",
                swarm_id=str(sup.tenant_id or ""),
                task_id=str(sup.id),
                sub_agent_id=str(sub.id),
                error=str(exc),
            )
            continue

        if requeued <= 0:
            result.skipped_resume_error += 1
            continue

        now = datetime.now(tz=UTC)
        goal = str(summary.get("raw_goal") or sup.goal or "Supervisor session").strip()
        resume_summary = dict(updated.context_summary or {})
        resume_summary["last_worker_crash_resume_at"] = now.isoformat()
        resume_summary["last_worker_crash_resume_sub_agent_id"] = str(sub.id)
        resume_summary["last_worker_crash_resume_role"] = str(sub.role or "")
        resume_summary["last_worker_crash_resume_requeued"] = requeued
        updated.context_summary = resume_summary

        if updated.tenant_id is not None:
            role_hint = snapshot.next_resumable_role or str(sub.role or "agent")
            await push_mission_feed_event(
                tenant_id=updated.tenant_id,
                kind="worker_crash_resume",
                title="Session auto-resumed",
                body=f"{goal[:200]} — worker crash detected; resumed from checkpoint ({role_hint}).",
                href=f"/agents?session={updated.id}",
                entity_id=str(updated.id),
            )
            result.notified += 1

        result.resumed += 1
        _logger.info(
            "worker_crash_auto_resume.resumed",
            agent_id="worker_crash_auto_resume",
            swarm_id=str(sup.tenant_id or ""),
            task_id=str(sup.id),
            sub_agent_id=str(sub.id),
            requeued_sub_agents=requeued,
            next_resumable_role=snapshot.next_resumable_role,
        )

    if result.resumed:
        await session.flush()

    return result


__all__ = [
    "WorkerCrashResumeResult",
    "derive_worker_crash_stale_cutoff",
    "sweep_stale_durable_sub_agents_for_auto_resume",
]
