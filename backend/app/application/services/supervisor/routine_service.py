"""Lightweight recurring routine service for supervisor sessions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import asc, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.supervisor.shared_context import SharedContextService
from app.application.services.supervisor.skills import SkillLibrary
from app.core.config import settings
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine

RoutineScheduleKind = Literal["interval", "cron"]


def compute_next_run_at(
    *,
    now: datetime,
    schedule_kind: RoutineScheduleKind,
    interval_seconds: int | None,
    cron_expr: str | None,
) -> datetime:
    """Compute next routine execution timestamp with safe fallbacks."""

    if schedule_kind == "interval":
        delta = max(int(interval_seconds or 300), 60)
        return now + timedelta(seconds=delta)
    cron = (cron_expr or "").strip().lower()
    if cron in {"@daily", "daily", "0 0 * * *"}:
        next_day = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return next_day
    if cron in {"@hourly", "hourly", "0 * * * *"}:
        return (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return now + timedelta(hours=1)


async def create_supervisor_routine(
    db: AsyncSession,
    *,
    name: str,
    goal_template: str,
    created_by_subject: str | None,
    schedule_kind: RoutineScheduleKind,
    interval_seconds: int | None,
    cron_expr: str | None,
    runtime_mode: Literal["inprocess", "durable"],
    roles: list[str],
    retrieval_contract: str | None,
    skills: list[str] | None,
    context_payload: dict[str, object] | None = None,
) -> SupervisorRoutine:
    """Create one routine row with computed next-run cursor."""

    now = datetime.now(tz=UTC)
    row = SupervisorRoutine(
        name=name.strip(),
        goal_template=goal_template.strip(),
        created_by_subject=created_by_subject,
        schedule_kind=schedule_kind,
        interval_seconds=interval_seconds if schedule_kind == "interval" else None,
        cron_expr=cron_expr.strip() if (cron_expr and schedule_kind == "cron") else None,
        runtime_mode=runtime_mode,
        roles=[item.strip() for item in roles if item.strip()],
        retrieval_contract=(retrieval_contract or "").strip() or None,
        skills=[item.strip().lower() for item in (skills or []) if item.strip()],
        context_payload=dict(context_payload or {}),
        is_active=True,
        status="scheduled",
        next_run_at=compute_next_run_at(
            now=now,
            schedule_kind=schedule_kind,
            interval_seconds=interval_seconds,
            cron_expr=cron_expr,
        ),
    )
    db.add(row)
    await db.flush()
    return row


async def list_supervisor_routines(
    db: AsyncSession,
    *,
    limit: int,
    offset: int,
) -> list[SupervisorRoutine]:
    """Return routines ordered by next execution (then newest first)."""

    stmt = (
        select(SupervisorRoutine)
        .order_by(asc(SupervisorRoutine.next_run_at), desc(SupervisorRoutine.created_at))
        .limit(limit)
        .offset(offset)
    )
    return list((await db.scalars(stmt)).all())


async def trigger_supervisor_routine_now(db: AsyncSession, *, routine: SupervisorRoutine) -> uuid.UUID:
    """Spawn an immediate supervisor session for a routine and update run cursors."""

    from app.application.services.supervisor.session_service import create_supervisor_session

    shared_context = SharedContextService()
    skills = SkillLibrary()
    created = await create_supervisor_session(
        db,
        goal=routine.goal_template,
        created_by_subject=f"routine:{routine.id}",
        runtime_mode=routine.runtime_mode,
        roles=list(routine.roles or []),
        shared_context=shared_context,
        retrieval_contract=routine.retrieval_contract,
        skill_slugs=list(routine.skills or []),
        skill_library=skills,
    )
    now = datetime.now(tz=UTC)
    routine.last_run_at = now
    routine.next_run_at = compute_next_run_at(
        now=now,
        schedule_kind=routine.schedule_kind,  # type: ignore[arg-type]
        interval_seconds=routine.interval_seconds,
        cron_expr=routine.cron_expr,
    )
    routine.last_error = None
    routine.status = "scheduled"
    await db.flush()
    return created.id


async def run_due_routines_tick(db: AsyncSession) -> dict[str, int]:
    """Execute due routines in-process by spawning supervisor sessions."""

    if not settings.routines_enabled:
        return {"queued": 0, "failed": 0}
    now = datetime.now(tz=UTC)
    stmt = (
        select(SupervisorRoutine)
        .where(
            SupervisorRoutine.is_active.is_(True),
            SupervisorRoutine.next_run_at.is_not(None),
            SupervisorRoutine.next_run_at <= now,
        )
        .order_by(asc(SupervisorRoutine.next_run_at))
        .limit(32)
    )
    due = list((await db.scalars(stmt)).all())
    queued = 0
    failed = 0
    for row in due:
        try:
            await trigger_supervisor_routine_now(db, routine=row)
            queued += 1
        except Exception as exc:
            failed += 1
            row.status = "failed"
            row.last_error = str(exc)[:2000]
            row.next_run_at = now + timedelta(minutes=5)
    await db.flush()
    return {"queued": queued, "failed": failed}


__all__ = [
    "compute_next_run_at",
    "create_supervisor_routine",
    "list_supervisor_routines",
    "run_due_routines_tick",
    "trigger_supervisor_routine_now",
]
