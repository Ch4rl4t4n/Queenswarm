"""Lightweight recurring routine service for supervisor sessions."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import asc, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.supervisor.memory_evolution import run_memory_evolution_for_tenant
from app.application.services.supervisor.autonomy import (
    build_autonomous_routine_plan,
    compile_swarm_autonomy_snapshot,
)
from app.application.services.supervisor.shared_context import SharedContextService
from app.application.services.supervisor.skills import SkillLibrary
from app.core.config import settings
from app.core.metrics import observe_supervisor_routine_event
from app.infrastructure.persistence.models.memory_evolution import MemoryEvolutionProposal
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
from app.infrastructure.persistence.models.task import Task

RoutineScheduleKind = Literal["interval", "cron", "event"]


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
    if schedule_kind == "event":
        return now + timedelta(seconds=max(30, int(settings.routine_watch_interval_sec)))
    cron = (cron_expr or "").strip().lower()
    if cron in {"@daily", "daily", "0 0 * * *"}:
        next_day = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return next_day
    if cron in {"@weekly", "weekly", "0 0 * * 1"}:
        weekday = now.weekday()
        days_until_monday = 7 - weekday if weekday != 0 else 7
        next_week = (now + timedelta(days=days_until_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        return next_week
    if cron in {"@hourly", "hourly", "0 * * * *"}:
        return (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    return now + timedelta(hours=1)


def suggest_optimal_schedule(
    *,
    schedule_kind: RoutineScheduleKind,
    now: datetime,
    context_payload: dict[str, object] | None = None,
) -> tuple[int | None, str | None]:
    """Suggest smarter schedule defaults when user did not provide explicit cadence."""

    context = dict(context_payload or {})
    if schedule_kind == "event":
        return int(context.get("watch_interval_sec") or settings.routine_watch_interval_sec), None
    if schedule_kind == "cron":
        priority = str(context.get("priority") or "").strip().lower()
        if priority in {"high", "urgent"}:
            return None, "@hourly"
        cadence = str(context.get("cadence") or "").strip().lower()
        if cadence in {"weekly", "@weekly"}:
            return None, "@weekly"
        return None, "@daily"
    hour = now.hour
    if 8 <= hour <= 18:
        return 900, None
    return 1800, None


def _safe_float(value: object) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


async def _resolve_watch_metric(db: AsyncSession, metric: str) -> float | None:
    """Resolve watch metric values used by event-triggered routines."""

    key = metric.strip().lower()
    if key == "tasks_pending_count":
        rows = list((await db.scalars(select(Task))).all())
        return float(sum(1 for row in rows if getattr(row.status, "value", str(row.status)) == "pending"))
    if key == "sessions_needs_input_count":
        rows = list((await db.scalars(select(SupervisorSession))).all())
        return float(sum(1 for row in rows if str(row.status or "").lower() == "needs_input"))
    if key == "routines_failed_count":
        rows = list((await db.scalars(select(SupervisorRoutine))).all())
        return float(sum(1 for row in rows if str(row.status or "").lower() == "failed"))
    return None


def _condition_triggered(*, current: float | None, previous: float | None, condition: dict[str, object]) -> bool:
    """Evaluate routine condition expression with changed/threshold operators."""

    op = str(condition.get("op") or ">=").strip().lower()
    target = _safe_float(condition.get("value"))
    if current is None:
        return False
    if op in {"changed", "delta"}:
        if previous is None:
            return False
        return abs(current - previous) > 1e-9
    if target is None:
        return False
    if op == ">":
        return current > target
    if op == ">=":
        return current >= target
    if op == "<":
        return current < target
    if op == "<=":
        return current <= target
    if op in {"==", "="}:
        return abs(current - target) <= 1e-9
    return False


def _append_run_history(
    *,
    context_payload: dict[str, object],
    entry: dict[str, object],
) -> dict[str, object]:
    """Append history item and enforce bounded history window."""

    payload = dict(context_payload)
    history = [item for item in list(payload.get("run_history") or []) if isinstance(item, dict)]
    history.append(entry)
    if len(history) > settings.routine_history_max_entries:
        history = history[-settings.routine_history_max_entries :]
    payload["run_history"] = history
    return payload


def consolidate_routine_memory(*, context_payload: dict[str, object]) -> dict[str, object]:
    """Compact old run history into summary snapshots for long-running routines."""

    payload = dict(context_payload)
    history = [item for item in list(payload.get("run_history") or []) if isinstance(item, dict)]
    if len(history) <= settings.routine_history_max_entries:
        return payload
    keep_tail = max(12, settings.routine_history_max_entries // 4)
    archived = history[:-keep_tail]
    tail = history[-keep_tail:]
    success = sum(1 for item in archived if str(item.get("status") or "") == "triggered")
    skipped = sum(1 for item in archived if str(item.get("status") or "") == "skipped")
    failed = sum(1 for item in archived if str(item.get("status") or "") == "failed")
    consolidation = dict(payload.get("memory_consolidation") or {})
    consolidation["last_consolidated_at"] = datetime.now(tz=UTC).isoformat()
    consolidation["archived_runs"] = int(consolidation.get("archived_runs") or 0) + len(archived)
    consolidation["summary"] = (
        f"archived={len(archived)} triggered={success} skipped={skipped} failed={failed}"
    )
    payload["memory_consolidation"] = consolidation
    payload["run_history"] = tail
    return payload


async def should_trigger_event_routine(
    db: AsyncSession,
    *,
    routine: SupervisorRoutine,
) -> tuple[bool, dict[str, object]]:
    """Evaluate event/conditional watch rule and return updated payload state."""

    payload = dict(routine.context_payload or {})
    condition = dict(payload.get("condition") or {})
    metric = str(condition.get("metric") or payload.get("watch_metric") or "").strip()
    if not metric:
        return False, payload
    current = await _resolve_watch_metric(db, metric)
    state = dict(payload.get("condition_state") or {})
    previous = _safe_float(state.get("last_value"))
    triggered = _condition_triggered(current=current, previous=previous, condition=condition)
    state["last_checked_at"] = datetime.now(tz=UTC).isoformat()
    state["last_value"] = current
    state["last_triggered"] = bool(triggered)
    payload["condition_state"] = state
    return triggered, payload


def build_continuous_intelligence_report(*, routine: SupervisorRoutine) -> dict[str, object]:
    """Build compact long-run monitoring report for watch-mode routines."""

    payload = dict(routine.context_payload or {})
    history = [item for item in list(payload.get("run_history") or []) if isinstance(item, dict)]
    triggered = sum(1 for item in history if str(item.get("status") or "") == "triggered")
    skipped = sum(1 for item in history if str(item.get("status") or "") == "skipped")
    failed = sum(1 for item in history if str(item.get("status") or "") == "failed")
    consolidation = dict(payload.get("memory_consolidation") or {})
    return {
        "watch_mode": bool(payload.get("watch_mode") or routine.schedule_kind == "event"),
        "history_entries": len(history),
        "triggered": triggered,
        "skipped": skipped,
        "failed": failed,
        "memory_consolidation": consolidation,
    }


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
    tenant_id: uuid.UUID | None = None,
) -> SupervisorRoutine:
    """Create one routine row with computed next-run cursor."""

    now = datetime.now(tz=UTC)
    eff_interval = interval_seconds
    eff_cron = cron_expr
    if eff_interval is None and not eff_cron:
        suggested_interval, suggested_cron = suggest_optimal_schedule(
            schedule_kind=schedule_kind,
            now=now,
            context_payload=context_payload,
        )
        eff_interval = suggested_interval
        eff_cron = suggested_cron
    base_payload = dict(context_payload or {})
    if settings.supervisor_self_healing_enabled:
        base_payload.setdefault("self_healing_enabled", True)
    if settings.supervisor_skills_enabled:
        base_payload.setdefault("advanced_skills_enabled", True)
    if settings.autonomous_routines_enabled and settings.swarm_full_autonomy_enabled:
        base_payload.setdefault("autonomous_routine_enabled", True)
        base_payload.setdefault("autonomy_planning_horizon_hours", settings.autonomous_routine_planning_horizon_hours)
    if schedule_kind == "event":
        base_payload.setdefault("watch_mode", True)
        base_payload.setdefault("watch_interval_sec", int(eff_interval or settings.routine_watch_interval_sec))

    row = SupervisorRoutine(
        name=name.strip(),
        goal_template=goal_template.strip(),
        tenant_id=tenant_id,
        created_by_subject=created_by_subject,
        schedule_kind=schedule_kind,
        interval_seconds=eff_interval if schedule_kind in {"interval", "event"} else None,
        cron_expr=eff_cron.strip() if (eff_cron and schedule_kind == "cron") else None,
        runtime_mode=runtime_mode,
        roles=[item.strip() for item in roles if item.strip()],
        retrieval_contract=(retrieval_contract or "").strip() or None,
        skills=[item.strip().lower() for item in (skills or []) if item.strip()],
        context_payload=base_payload,
        is_active=True,
        status="scheduled",
        next_run_at=compute_next_run_at(
            now=now,
            schedule_kind=schedule_kind,
            interval_seconds=eff_interval,
            cron_expr=eff_cron,
        ),
    )
    db.add(row)
    await db.flush()
    observe_supervisor_routine_event(event="created")
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
    payload = dict(routine.context_payload or {})
    report = build_continuous_intelligence_report(routine=routine)
    payload["continuous_intelligence_report"] = report
    payload.setdefault("run_history", [])
    autonomy_snapshot_payload: dict[str, object] = {}
    if settings.swarm_full_autonomy_enabled and settings.autonomous_routines_enabled and routine.tenant_id is not None:
        autonomous_plan = build_autonomous_routine_plan(
            routine_name=str(routine.name),
            goal_template=str(routine.goal_template),
            schedule_kind=str(routine.schedule_kind),
            interval_seconds=routine.interval_seconds,
            context_payload=payload,
        )
        payload["autonomous_plan"] = autonomous_plan
        snapshot = await compile_swarm_autonomy_snapshot(db, tenant_id=routine.tenant_id)
        autonomy_snapshot_payload = {
            "autonomy_mode": snapshot.autonomy_mode,
            "pending_memory_approvals": snapshot.pending_memory_approvals,
            "pending_initiative_approvals": snapshot.pending_initiative_approvals,
            "average_strategy_score": snapshot.average_strategy_score,
            "status": snapshot.status,
        }
        payload["autonomy_snapshot"] = autonomy_snapshot_payload

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
        context_seed={
            "routine_id": str(routine.id),
            "routine_schedule_kind": str(routine.schedule_kind),
            "routine_watch_mode": bool(payload.get("watch_mode") or False),
            "continuous_intelligence_report": report,
            "autonomous_plan": dict(payload.get("autonomous_plan") or {}),
            "autonomy_snapshot": autonomy_snapshot_payload,
        },
        tenant_id=routine.tenant_id,
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
    payload = _append_run_history(
        context_payload=payload,
        entry={
            "ran_at": now.isoformat(),
            "status": "triggered",
            "session_id": str(created.id),
        },
    )
    routine.context_payload = consolidate_routine_memory(context_payload=payload)
    await db.flush()
    observe_supervisor_routine_event(event="triggered")
    return created.id


async def run_due_routines_tick(db: AsyncSession) -> dict[str, int]:
    """Execute due routines in-process by spawning supervisor sessions."""

    if not settings.routines_enabled:
        return {"queued": 0, "failed": 0, "skipped": 0}
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
    skipped = 0
    for row in due:
        try:
            routine_kind = str((row.context_payload or {}).get("routine_kind") or "").strip().lower()
            if routine_kind == "memory_dreaming":
                if row.tenant_id is None:
                    skipped += 1
                    continue
                from app.worker.celery_app import celery_app

                celery_app.send_task(
                    "app.worker.tasks.dreaming_tasks.run_memory_dreaming",
                    args=[str(row.tenant_id)],
                )
                now = datetime.now(tz=UTC)
                row.last_run_at = now
                row.next_run_at = compute_next_run_at(
                    now=now,
                    schedule_kind="interval",
                    interval_seconds=row.interval_seconds or (settings.dreaming_default_interval_hours * 3600),
                    cron_expr=None,
                )
                row.last_error = None
                row.status = "scheduled"
                payload = _append_run_history(
                    context_payload=dict(row.context_payload or {}),
                    entry={"ran_at": now.isoformat(), "status": "triggered", "kind": "memory_dreaming"},
                )
                row.context_payload = consolidate_routine_memory(context_payload=payload)
                queued += 1
                continue
            if str(row.schedule_kind or "") == "event":
                triggered, payload = await should_trigger_event_routine(db, routine=row)
                now = datetime.now(tz=UTC)
                if not triggered:
                    row.next_run_at = now + timedelta(seconds=max(30, int(row.interval_seconds or settings.routine_watch_interval_sec)))
                    payload = _append_run_history(
                        context_payload=payload,
                        entry={"ran_at": now.isoformat(), "status": "skipped"},
                    )
                    row.context_payload = consolidate_routine_memory(context_payload=payload)
                    skipped += 1
                    continue
                row.context_payload = payload
            await trigger_supervisor_routine_now(db, routine=row)
            queued += 1
        except Exception as exc:
            failed += 1
            row.status = "failed"
            row.last_error = str(exc)[:2000]
            now = datetime.now(tz=UTC)
            row.next_run_at = now + timedelta(minutes=5)
            payload = _append_run_history(
                context_payload=dict(row.context_payload or {}),
                entry={"ran_at": now.isoformat(), "status": "failed", "error": str(exc)[:300]},
            )
            row.context_payload = consolidate_routine_memory(context_payload=payload)
            observe_supervisor_routine_event(event="failed")
    if settings.memory_evolution_enabled and hasattr(db, "scalar"):
        tenant_ids = {
            row.tenant_id
            for row in due
            if getattr(row, "tenant_id", None) is not None
        }
        for tenant_id in tenant_ids:
            last_run_at = await db.scalar(
                select(func.max(MemoryEvolutionProposal.created_at)).where(
                    MemoryEvolutionProposal.tenant_id == tenant_id,
                ),
            )
            if isinstance(last_run_at, datetime):
                elapsed = datetime.now(tz=UTC) - last_run_at
                if elapsed.total_seconds() < float(settings.memory_evolution_interval_sec):
                    continue
            await run_memory_evolution_for_tenant(
                db,
                tenant_id=tenant_id,
                proposed_by_user_id=None,
                approval_threshold=settings.memory_evolution_manual_approval_threshold,
            )

    await db.flush()
    return {"queued": queued, "failed": failed, "skipped": skipped}


__all__ = [
    "build_continuous_intelligence_report",
    "consolidate_routine_memory",
    "compute_next_run_at",
    "create_supervisor_routine",
    "list_supervisor_routines",
    "should_trigger_event_routine",
    "suggest_optimal_schedule",
    "run_due_routines_tick",
    "trigger_supervisor_routine_now",
]
