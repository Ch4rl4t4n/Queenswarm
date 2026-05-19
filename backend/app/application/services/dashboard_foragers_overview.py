"""Foragers operator page — KPIs, configuration table, auto-spawn rules."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tenant_context import get_current_tenant_uuid
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.agent_config import AgentConfig
from app.infrastructure.persistence.models.agent_template import AgentTemplateORM
from app.infrastructure.persistence.models.forager import ForagerORM
from app.infrastructure.persistence.models.knowledge import KnowledgeItem
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine


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
        configurations.append(
            {
                "id": str(forager.id),
                "source_name": _display_source_name(forager),
                "source_type": _source_type_badge(forager.source_type),
                "schedule_label": _format_schedule(routine),
                "last_run_seconds_ago": _sync_seconds_ago(last_ref, now),
                "items_count": await _count_items_for_forager(session, forager),
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


__all__ = ["build_foragers_overview_payload"]
