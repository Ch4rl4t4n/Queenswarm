"""Foragers operator page — KPIs, configuration table, auto-spawn rules."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.services.social_intel_runner import _source_keys_for_forager
from app.core.tenant_context import get_current_tenant_uuid
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.agent_config import AgentConfig
from app.infrastructure.persistence.models.agent_template import AgentTemplateORM
from app.infrastructure.persistence.models.forager import ForagerORM
from app.infrastructure.persistence.models.intel_source_cursor import IntelSourceCursorORM
from app.infrastructure.persistence.models.knowledge import KnowledgeItem
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession


def _sync_seconds_ago(ref: datetime | None, now: datetime) -> int | None:
    """Return elapsed seconds since *ref*, or ``None`` when unknown."""

    if ref is None:
        return None
    stamp = ref if ref.tzinfo is not None else ref.replace(tzinfo=UTC)
    return max(0, int((now - stamp).total_seconds()))


def _source_type_badge(source_type: str) -> str:
    """Map persisted source type to UI badge label."""

    if source_type == "free_api":
        return "api"
    return source_type


def _display_source_name(forager: ForagerORM) -> str:
    """Human-readable source label for the configurations table."""

    badge = _source_type_badge(forager.source_type)
    if badge == "youtube":
        return f"YouTube · {forager.name}"
    if badge == "rss":
        return f"RSS · {forager.name}"
    if badge == "api":
        return f"API · {forager.name}"
    return forager.name


def _format_schedule(routine: SupervisorRoutine | None) -> str:
    """Render schedule cadence for operator table."""

    if routine is None or not routine.is_active:
        return "on demand"
    if routine.schedule_kind == "cron" and routine.cron_expr:
        return routine.cron_expr
    interval = routine.interval_seconds
    if isinstance(interval, int) and interval > 0:
        if interval < 3600:
            minutes = max(1, interval // 60)
            return f"every {minutes}m"
        if interval < 86_400:
            hours = max(1, interval // 3600)
            return f"every {hours}h"
        days = max(1, interval // 86_400)
        return f"every {days}d"
    return routine.schedule_kind


def _forager_status(forager: ForagerORM, routine: SupervisorRoutine | None) -> str:
    """Derive row status: ok, warn, paused, or error."""

    if not forager.is_active:
        return "paused"
    if routine is not None and routine.last_error:
        return "error"
    if routine is not None and routine.last_run_at is not None and routine.interval_seconds:
        stale_after = max(routine.interval_seconds * 2, 3600)
        age = _sync_seconds_ago(routine.last_run_at, datetime.now(tz=UTC))
        if age is not None and age > stale_after:
            return "warn"
    return "ok"


def _trend_pct(current: int, previous: int) -> int | None:
    """Percent change vs prior window; ``None`` when baseline is zero."""

    if previous <= 0:
        return None
    return int(round(((current - previous) / previous) * 100))


def _session_sub_agent_progress_pct(session: SupervisorSession) -> int:
    """Derive live evaluator progress from sub-agent completion ratio."""

    subs = list(getattr(session, "sub_agents", None) or [])
    if not subs:
        return 15
    done = sum(1 for row in subs if str(row.status or "").strip().lower() == "completed")
    total = len(subs)
    if done >= total:
        return 99
    return max(5, min(98, int(round(100.0 * done / total))))


def _status_fallback_progress(
    *,
    status: str,
    routine: SupervisorRoutine | None,
    now: datetime,
) -> int:
    """Map idle row status to operator-visible completion when no live run exists."""

    if status == "paused":
        return 0
    if status == "error":
        return 0
    if status == "ok":
        return 100
    if status == "warn" and routine is not None and routine.last_run_at is not None:
        stale_after = max(int(routine.interval_seconds or 0) * 2, 3600)
        age = _sync_seconds_ago(routine.last_run_at, now)
        if age is not None and stale_after > 0:
            overdue = min(1.0, age / stale_after)
            return max(15, int(round(100 * (1.0 - overdue * 0.75))))
    return 40


async def _running_routine_progress_map(
    session: AsyncSession,
    routine_ids: list[uuid.UUID],
) -> dict[str, int]:
    """Return live progress pct keyed by routine id string for active supervisor sessions."""

    detail = await _running_routine_detail_map(session, routine_ids)
    return {key: int(row.get("pct") or 0) for key, row in detail.items()}


async def _running_routine_detail_map(
    session: AsyncSession,
    routine_ids: list[uuid.UUID],
) -> dict[str, dict[str, Any]]:
    """Return live progress + session id keyed by routine id string."""

    if not routine_ids:
        return {}
    id_strs = [str(rid) for rid in routine_ids]
    stmt = (
        select(SupervisorSession)
        .options(selectinload(SupervisorSession.sub_agents))
        .where(
            SupervisorSession.status.in_(("running", "pending", "needs_input")),
            SupervisorSession.context_summary["routine_id"].astext.in_(id_strs),
        )
        .order_by(SupervisorSession.created_at.desc())
    )
    rows = list((await session.execute(stmt)).scalars().all())
    detail: dict[str, dict[str, Any]] = {}
    for row in rows:
        routine_key = str((row.context_summary or {}).get("routine_id") or "")
        if not routine_key or routine_key in detail:
            continue
        detail[routine_key] = {
            "pct": _session_sub_agent_progress_pct(row),
            "session_id": str(row.id),
        }
    return detail


async def _cursor_backfill_progress_map(
    session: AsyncSession,
    foragers: list[ForagerORM],
) -> dict[str, int]:
    """Return source backfill completion pct for social intel foragers."""

    social_ids = [
        row.id
        for row in foragers
        if row.source_type in {"youtube", "twitter", "x"}
    ]
    if not social_ids:
        return {}

    cursor_rows = list(
        (
            await session.execute(
                select(IntelSourceCursorORM).where(IntelSourceCursorORM.forager_id.in_(social_ids)),
            )
        ).scalars().all(),
    )
    by_forager: dict[str, list[IntelSourceCursorORM]] = {}
    for cursor in cursor_rows:
        by_forager.setdefault(str(cursor.forager_id), []).append(cursor)

    out: dict[str, int] = {}
    for forager in foragers:
        if forager.source_type not in {"youtube", "twitter", "x"}:
            continue
        keys = _source_keys_for_forager(forager)
        if not keys:
            continue
        cursors = by_forager.get(str(forager.id), [])
        if not cursors:
            out[str(forager.id)] = 0
            continue
        complete = sum(1 for row in cursors if bool(row.backfill_complete))
        out[str(forager.id)] = max(0, min(100, int(round(100.0 * complete / len(keys)))))
    return out


def resolve_forager_run_progress_pct(
    *,
    forager: ForagerORM,
    routine: SupervisorRoutine | None,
    status: str,
    now: datetime,
    running_progress: int | None,
    cursor_progress: int | None,
) -> int:
    """Combine live session, source backfill, and schedule health into one pct."""

    return resolve_forager_progress_meta(
        forager=forager,
        routine=routine,
        status=status,
        now=now,
        running_progress=running_progress,
        running_session_id=None,
        cursor_progress=cursor_progress,
    )["pct"]


def resolve_forager_progress_meta(
    *,
    forager: ForagerORM,
    routine: SupervisorRoutine | None,
    status: str,
    now: datetime,
    running_progress: int | None,
    running_session_id: str | None,
    cursor_progress: int | None,
) -> dict[str, Any]:
    """Return pct plus operator-facing progress kind, detail, and optional deep link."""

    forager_id = str(forager.id)
    knowledge_href = f"/knowledge?forager={forager_id}&q={forager.name}#explorer"

    if running_progress is not None:
        href = f"/agents?session={running_session_id}" if running_session_id else None
        return {
            "pct": running_progress,
            "kind": "live_run",
            "detail": "Supervisor evaluator session is running.",
            "href": href,
        }
    if cursor_progress is not None:
        pct = cursor_progress
        if status == "ok" and cursor_progress >= 100:
            pct = 100
        elif status == "error":
            pct = min(cursor_progress, 25)
        detail = (
            "Source backfill complete — all monitored channels indexed."
            if pct >= 100
            else f"Source backfill {pct}% — historical channels still indexing."
        )
        return {
            "pct": pct,
            "kind": "backfill",
            "detail": detail,
            "href": knowledge_href,
        }
    if status == "paused":
        return {"pct": 0, "kind": "paused", "detail": "Forager paused — enable to resume schedule.", "href": None}
    if status == "error":
        return {
            "pct": 0,
            "kind": "error",
            "detail": "Last routine run failed — open Edit or trigger Run to retry.",
            "href": None,
        }
    if status == "ok":
        return {
            "pct": 100,
            "kind": "idle_ok",
            "detail": "Last scheduled run completed — harvest in HiveMind.",
            "href": knowledge_href,
        }
    if status == "warn" and routine is not None and routine.last_run_at is not None:
        pct = _status_fallback_progress(status=status, routine=routine, now=now)
        return {
            "pct": pct,
            "kind": "schedule_stale",
            "detail": "Run is overdue vs schedule — check cron or trigger Run now.",
            "href": None,
        }
    return {"pct": 40, "kind": "unknown", "detail": "Progress estimate unavailable.", "href": None}


async def _count_knowledge(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    since: datetime,
    until: datetime | None = None,
    source_prefix: str | None = None,
    embedded_only: bool = False,
) -> int:
    """Count knowledge rows in a time window with optional filters."""

    clauses = [KnowledgeItem.scraped_at >= since]
    if until is not None:
        clauses.append(KnowledgeItem.scraped_at < until)
    if tenant_id is not None:
        clauses.append(KnowledgeItem.tenant_id == tenant_id)
    if source_prefix:
        clauses.append(KnowledgeItem.source_type.like(f"{source_prefix}%"))
    if embedded_only:
        clauses.append(KnowledgeItem.embedding_id.isnot(None))
    return int(await session.scalar(select(func.count()).select_from(KnowledgeItem).where(*clauses)) or 0)


async def _count_items_for_forager(session: AsyncSession, forager: ForagerORM) -> int:
    """Count HiveMind rows tagged with this forager id."""

    tag = f"forager:{forager.id}"
    return int(
        await session.scalar(
            select(func.count())
            .select_from(KnowledgeItem)
            .where(
                KnowledgeItem.tenant_id == forager.tenant_id,
                KnowledgeItem.topic_tags.contains([tag]),
            ),
        )
        or 0,
    )


async def build_foragers_overview_payload(session: AsyncSession) -> dict[str, Any]:
    """Aggregate forager KPIs, configuration rows, and auto-spawn rules."""

    now = datetime.now(tz=UTC)
    since_24h = now - timedelta(hours=24)
    since_48h = now - timedelta(hours=48)
    since_7d = now - timedelta(days=7)
    tenant_id = get_current_tenant_uuid()

    forager_stmt = select(ForagerORM).order_by(ForagerORM.updated_at.desc(), ForagerORM.name.asc())
    if tenant_id is not None:
        forager_stmt = forager_stmt.where(ForagerORM.tenant_id == tenant_id)
    foragers = list((await session.execute(forager_stmt)).scalars().all())

    routine_ids = [row.supervisor_routine_id for row in foragers if row.supervisor_routine_id is not None]
    routines_map: dict[uuid.UUID, SupervisorRoutine] = {}
    if routine_ids:
        routine_rows = (
            await session.execute(select(SupervisorRoutine).where(SupervisorRoutine.id.in_(routine_ids)))
        ).scalars().all()
        routines_map = {row.id: row for row in routine_rows}

    running_detail = await _running_routine_detail_map(session, routine_ids)
    running_progress = {key: int(row.get("pct") or 0) for key, row in running_detail.items()}
    cursor_progress = await _cursor_backfill_progress_map(session, foragers)

    template_ids = {row.agent_template_id for row in foragers if row.agent_template_id is not None}
    templates_map: dict[uuid.UUID, AgentTemplateORM] = {}
    if template_ids:
        template_rows = (
            await session.execute(select(AgentTemplateORM).where(AgentTemplateORM.id.in_(template_ids)))
        ).scalars().all()
        templates_map = {row.id: row for row in template_rows}

    items_24h = await _count_knowledge(
        session,
        tenant_id=tenant_id,
        since=since_24h,
        source_prefix="forager:",
    )
    items_prev_24h = await _count_knowledge(
        session,
        tenant_id=tenant_id,
        since=since_48h,
        until=since_24h,
        source_prefix="forager:",
    )
    chunks_7d = await _count_knowledge(
        session,
        tenant_id=tenant_id,
        since=since_7d,
        embedded_only=True,
    )

    spawned_from_config = (
        await session.scalar(
            select(func.count())
            .select_from(Agent)
            .where(Agent.config["origin"].astext == "forager_spawn"),
        )
        or 0
    )
    spawned_from_output = (
        await session.scalar(
            select(func.count())
            .select_from(AgentConfig)
            .where(AgentConfig.output_config["forager_id"].astext.isnot(None)),
        )
        or 0
    )
    spawned_count = int(max(spawned_from_config, spawned_from_output))

    configurations: list[dict[str, Any]] = []
    error_n = 0
    for forager in foragers:
        routine = routines_map.get(forager.supervisor_routine_id) if forager.supervisor_routine_id else None
        status = _forager_status(forager, routine)
        if status == "error":
            error_n += 1
        last_ref = routine.last_run_at if routine is not None and routine.last_run_at is not None else forager.updated_at
        routine_key = str(forager.supervisor_routine_id) if forager.supervisor_routine_id else ""
        live = running_detail.get(routine_key)
        progress_meta = resolve_forager_progress_meta(
            forager=forager,
            routine=routine,
            status=status,
            now=now,
            running_progress=int(live["pct"]) if live is not None else None,
            running_session_id=str(live.get("session_id") or "") or None if live is not None else None,
            cursor_progress=cursor_progress.get(str(forager.id)),
        )
        configurations.append(
            {
                "id": str(forager.id),
                "source_name": _display_source_name(forager),
                "source_type": _source_type_badge(forager.source_type),
                "schedule_label": _format_schedule(routine),
                "last_run_seconds_ago": _sync_seconds_ago(last_ref, now),
                "items_count": await _count_items_for_forager(session, forager),
                "run_progress_pct": progress_meta["pct"],
                "progress_kind": progress_meta["kind"],
                "progress_detail": progress_meta["detail"],
                "progress_href": progress_meta.get("href"),
                "status": status,
                "is_active": bool(forager.is_active),
            },
        )

    active_n = sum(1 for row in foragers if row.is_active)
    paused_n = sum(1 for row in foragers if not row.is_active)

    spawn_rules: list[dict[str, Any]] = []
    for forager in foragers:
        filter_cfg = dict(forager.filter_config or {})
        explicit_rules = list(filter_cfg.get("auto_spawn_rules") or [])
        if explicit_rules:
            for index, rule in enumerate(explicit_rules):
                if not isinstance(rule, dict):
                    continue
                spawn_rules.append(
                    {
                        "id": str(rule.get("id") or f"{forager.id}:{index}"),
                        "forager_id": str(forager.id),
                        "when_label": str(rule.get("when_label") or rule.get("when") or forager.name),
                        "spawn_label": str(rule.get("spawn_label") or rule.get("spawn") or "Spawn agent"),
                        "cooldown": str(rule.get("cooldown") or "1h"),
                        "enabled": bool(rule.get("enabled", True)),
                    },
                )
            continue
        if forager.agent_template_id is None:
            continue
        template = templates_map.get(forager.agent_template_id)
        template_name = template.name if template is not None else "Agent template"
        spawn_rules.append(
            {
                "id": f"{forager.id}:default",
                "forager_id": str(forager.id),
                "when_label": f"{forager.name} finds matching items",
                "spawn_label": f"{template_name} → swarm",
                "cooldown": "1h",
                "enabled": bool(forager.is_active),
            },
        )

    trend = _trend_pct(items_24h, items_prev_24h)

    return {
        "generated_at": now.isoformat(),
        "kpis": {
            "foragers_total": len(foragers),
            "foragers_active": active_n,
            "foragers_paused": paused_n,
            "foragers_error": error_n,
            "items_ingested_24h": items_24h,
            "items_trend_pct": trend,
            "hivemind_chunks_7d": chunks_7d,
            "auto_spawned_bees": spawned_count,
        },
        "configurations": configurations,
        "spawn_rules": spawn_rules,
    }


__all__ = [
    "build_foragers_overview_payload",
    "resolve_forager_progress_meta",
    "resolve_forager_run_progress_pct",
]
