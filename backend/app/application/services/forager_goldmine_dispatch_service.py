"""DG7 — Goldmine alert inbox and one-click Mission Kanban dispatch with skill bundle."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.forager_harvest_report import _finding_title
from app.application.services.task_ledger import create_task_record
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.enums import TaskStatus, TaskType
from app.infrastructure.persistence.models.forager import ForagerORM
from app.infrastructure.persistence.models.knowledge import KnowledgeItem
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine

_logger = get_logger(__name__)

PromoteMode = Literal["digest", "alert"]

_DEFAULT_SKILL_BUNDLE: list[str] = [
    "competitor-scrape-analyze",
    "context",
    "execution-studio",
]

_SOURCE_SKILL_BUNDLES: dict[str, list[str]] = {
    "youtube": ["competitor-scrape-analyze", "context", "research"],
    "twitter": ["competitor-scrape-analyze", "context", "marketing-campaign-playbook"],
    "x": ["competitor-scrape-analyze", "context", "marketing-campaign-playbook"],
    "rss": ["competitor-scrape-analyze", "context", "research"],
    "free_api": ["competitor-scrape-analyze", "context"],
}


class ForagerGoldminePreviewItem(BaseModel):
    """One harvested signal preview for a goldmine alert row."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    scraped_at: datetime | None = None
    source_url: str | None = None


class ForagerGoldmineAlertRow(BaseModel):
    """Actionable delta alert — new HiveMind rows since the last scheduled run."""

    model_config = ConfigDict(extra="forbid")

    forager_id: str
    forager_name: str
    source_type: str
    new_item_count: int
    since_iso: str
    headline: str
    skill_bundle: list[str] = Field(default_factory=list)
    preview_items: list[ForagerGoldminePreviewItem] = Field(default_factory=list)


class ForagerGoldmineAlertsOut(BaseModel):
    """Operator inbox payload for DG7 goldmine dispatch."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    alerts: list[ForagerGoldmineAlertRow] = Field(default_factory=list)
    operator_hint: str = "Dispatch attaches a skill bundle and parks triage on Mission Kanban."


def derive_forager_skill_bundle(source_type: str) -> list[str]:
    """Map forager source type to a reusable harness skill bundle."""

    key = str(source_type or "").strip().lower()
    bundle = list(_SOURCE_SKILL_BUNDLES.get(key, _DEFAULT_SKILL_BUNDLE))
    return bundle[:12]


def _forager_tag(forager_id: uuid.UUID) -> str:
    return f"forager:{forager_id}"


async def _load_forager_knowledge_rows(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    forager_id: uuid.UUID,
    since: datetime | None = None,
    item_ids: list[uuid.UUID] | None = None,
    limit: int = 12,
) -> list[KnowledgeItem]:
    """Load knowledge rows for one forager, optionally filtered by time or explicit ids."""

    tag = _forager_tag(forager_id)
    clauses = [
        KnowledgeItem.tenant_id == tenant_id,
        KnowledgeItem.topic_tags.contains([tag]),
    ]
    if item_ids:
        clauses.append(KnowledgeItem.id.in_(item_ids))
    if since is not None and not item_ids:
        clauses.append(KnowledgeItem.scraped_at >= since)

    stmt = (
        select(KnowledgeItem)
        .where(*clauses)
        .order_by(desc(KnowledgeItem.scraped_at))
        .limit(max(1, min(limit, 50)))
    )
    return list((await session.execute(stmt)).scalars().all())


async def _count_new_forager_items(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    forager_id: uuid.UUID,
    since: datetime,
) -> int:
    """Count HiveMind rows tagged to a forager ingested after *since*."""

    tag = _forager_tag(forager_id)
    stmt = (
        select(func.count())
        .select_from(KnowledgeItem)
        .where(
            KnowledgeItem.tenant_id == tenant_id,
            KnowledgeItem.topic_tags.contains([tag]),
            KnowledgeItem.scraped_at >= since,
        )
    )
    return int((await session.scalar(stmt)) or 0)


async def _resolve_alert_since(
    session: AsyncSession,
    *,
    forager: ForagerORM,
) -> datetime:
    """Anchor delta window to last routine run, else rolling 24h."""

    routine_id = forager.supervisor_routine_id
    if routine_id is not None:
        routine = await session.scalar(
            select(SupervisorRoutine).where(SupervisorRoutine.id == routine_id),
        )
        if routine is not None and routine.last_run_at is not None:
            ref = routine.last_run_at
            return ref if ref.tzinfo is not None else ref.replace(tzinfo=UTC)
    return datetime.now(tz=UTC) - timedelta(hours=24)


def _preview_from_rows(rows: list[KnowledgeItem]) -> list[ForagerGoldminePreviewItem]:
    """Serialize knowledge rows for alert previews."""

    previews: list[ForagerGoldminePreviewItem] = []
    for row in rows[:5]:
        previews.append(
            ForagerGoldminePreviewItem(
                id=str(row.id),
                title=_finding_title(str(row.content_text or ""), row.source_url),
                scraped_at=row.scraped_at,
                source_url=row.source_url,
            ),
        )
    return previews


def _build_alert_task_text(
    *,
    forager: ForagerORM,
    mode: PromoteMode,
    new_count: int,
    since_iso: str,
    rows: list[KnowledgeItem],
    skill_bundle: list[str],
) -> str:
    """Compose triage prompt for digest or delta alert dispatch."""

    header = (
        f"Goldmine alert: {forager.name} ({forager.source_type}) — "
        f"{new_count} new signal{'s' if new_count != 1 else ''} since {since_iso}."
    )
    if mode == "digest":
        header = (
            f"Review forager harvest: {forager.name} ({forager.source_type}). "
            f"Sample items loaded: {len(rows)}. Simulate-first — verify intel before downstream spawn."
        )

    parts: list[str] = [header, "", "Skill bundle:", ", ".join(skill_bundle), ""]
    if rows:
        parts.append("Signals:")
        for index, row in enumerate(rows[:8], start=1):
            title = _finding_title(str(row.content_text or ""), row.source_url)
            snippet = str(row.content_text or "").strip().replace("\n", " ")
            if len(snippet) > 280:
                snippet = f"{snippet[:277]}…"
            line = f"{index}. {title}"
            if row.source_url:
                line += f" ({row.source_url})"
            parts.append(line)
            if snippet:
                parts.append(f"   {snippet}")
        parts.append("")
    else:
        parts.append("No ingested items yet — run the forager or check source config.")
    parts.append("Simulate-first before spawn or publish.")
    return "\n".join(parts)


async def compose_forager_goldmine_alerts(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    limit: int = 20,
) -> ForagerGoldmineAlertsOut:
    """List foragers with new HiveMind rows since their last scheduled run."""

    if not settings.forager_goldmine_dispatch_enabled:
        return ForagerGoldmineAlertsOut(enabled=False)

    cap = max(1, min(limit, 40))
    foragers = list(
        (
            await session.execute(
                select(ForagerORM)
                .where(
                    ForagerORM.tenant_id == tenant_id,
                    ForagerORM.is_active.is_(True),
                )
                .order_by(ForagerORM.updated_at.desc()),
            )
        ).scalars().all(),
    )

    alerts: list[ForagerGoldmineAlertRow] = []
    for forager in foragers:
        since = await _resolve_alert_since(session, forager=forager)
        new_count = await _count_new_forager_items(
            session,
            tenant_id=tenant_id,
            forager_id=forager.id,
            since=since,
        )
        if new_count <= 0:
            continue
        preview_rows = await _load_forager_knowledge_rows(
            session,
            tenant_id=tenant_id,
            forager_id=forager.id,
            since=since,
            limit=5,
        )
        skill_bundle = derive_forager_skill_bundle(forager.source_type)
        since_iso = since.isoformat()
        alerts.append(
            ForagerGoldmineAlertRow(
                forager_id=str(forager.id),
                forager_name=forager.name,
                source_type=str(forager.source_type or ""),
                new_item_count=new_count,
                since_iso=since_iso,
                headline=f"{new_count} new signal{'s' if new_count != 1 else ''} since last run",
                skill_bundle=skill_bundle,
                preview_items=_preview_from_rows(preview_rows),
            ),
        )
        if len(alerts) >= cap:
            break

    _logger.info(
        "forager.goldmine_alerts",
        agent_id="forager_hub",
        swarm_id=str(tenant_id),
        alert_count=len(alerts),
    )
    return ForagerGoldmineAlertsOut(enabled=True, alerts=alerts)


async def promote_forager_goldmine_dispatch(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    forager_id: uuid.UUID,
    title: str | None = None,
    mode: PromoteMode = "digest",
    knowledge_item_ids: list[uuid.UUID] | None = None,
    include_skill_bundle: bool = True,
) -> dict[str, Any]:
    """Create a Mission Kanban triage task from digest or delta alert with skill bundle."""

    forager = await session.scalar(
        select(ForagerORM).where(
            ForagerORM.id == forager_id,
            ForagerORM.tenant_id == tenant_id,
        ),
    )
    if forager is None:
        return {"ok": False, "error": "forager_not_found"}

    since = await _resolve_alert_since(session, forager=forager)
    since_iso = since.isoformat()
    item_ids = list(knowledge_item_ids or [])
    rows: list[KnowledgeItem]
    if item_ids:
        rows = await _load_forager_knowledge_rows(
            session,
            tenant_id=tenant_id,
            forager_id=forager_id,
            item_ids=item_ids,
            limit=len(item_ids),
        )
        new_count = len(rows)
    elif mode == "alert":
        rows = await _load_forager_knowledge_rows(
            session,
            tenant_id=tenant_id,
            forager_id=forager_id,
            since=since,
            limit=12,
        )
        new_count = await _count_new_forager_items(
            session,
            tenant_id=tenant_id,
            forager_id=forager_id,
            since=since,
        )
    else:
        rows = await _load_forager_knowledge_rows(
            session,
            tenant_id=tenant_id,
            forager_id=forager_id,
            limit=3,
        )
        new_count = len(rows)

    skill_bundle = derive_forager_skill_bundle(forager.source_type) if include_skill_bundle else []
    if mode == "alert" and new_count > 0:
        default_title = f"Goldmine alert · {forager.name} · {new_count} new"
    else:
        default_title = f"Forager digest · {forager.name}"
    task_title = (title or default_title).strip()[:500]
    task_text = _build_alert_task_text(
        forager=forager,
        mode=mode,
        new_count=new_count,
        since_iso=since_iso,
        rows=rows,
        skill_bundle=skill_bundle,
    )
    excerpt = "\n\n---\n\n".join(
        str(row.content_text or "").strip()[:600]
        for row in rows[:3]
        if str(row.content_text or "").strip()
    ).strip()[:1800]

    payload: dict[str, Any] = {
        "mission_kanban": True,
        "triage": True,
        "source": "forager_goldmine" if mode == "alert" else "forager_digest",
        "forager_id": str(forager.id),
        "forager_name": forager.name,
        "source_type": forager.source_type,
        "task_text": task_text,
        "excerpt": excerpt,
        "simulate_first": True,
        "goldmine_mode": mode,
        "new_item_count": new_count,
        "since_iso": since_iso,
    }
    if skill_bundle:
        payload["skills"] = skill_bundle
        payload["skill_bundle"] = skill_bundle
    if item_ids:
        payload["knowledge_item_ids"] = [str(item_id) for item_id in item_ids]

    row = await create_task_record(
        session,
        title=task_title,
        task_type_value=TaskType.REPORT,
        priority=5,
        payload=payload,
        swarm_id=None,
        workflow_id=None,
        parent_task_id=None,
        status=TaskStatus.TRIAGE,
    )
    row.tenant_id = tenant_id
    await session.flush()

    _logger.info(
        "forager.goldmine_dispatch",
        agent_id="forager_hub",
        swarm_id=str(tenant_id),
        task_id=str(row.id),
        forager_id=str(forager.id),
        mode=mode,
        new_item_count=new_count,
        skill_count=len(skill_bundle),
    )
    return {
        "ok": True,
        "task_id": str(row.id),
        "forager_id": str(forager.id),
        "title": task_title,
        "mode": mode,
        "new_item_count": new_count,
        "skill_slugs": skill_bundle,
    }


def derive_spawn_rule_match_hint(filter_config: dict[str, Any] | None) -> str | None:
    """Return operator hint when auto-spawn rules may match new harvest."""

    cfg = dict(filter_config or {})
    rules = list(cfg.get("auto_spawn_rules") or [])
    enabled: list[str] = []
    for entry in rules:
        if not isinstance(entry, dict) or not entry.get("enabled", True):
            continue
        label = str(entry.get("when_label") or entry.get("when") or "spawn rule").strip()
        if label:
            enabled.append(label[:80])
    if not enabled:
        return None
    joined = ", ".join(enabled[:2])
    if len(enabled) > 2:
        joined += f" (+{len(enabled) - 2} more)"
    return f"Spawn rules: {joined}"


async def compose_goldmine_alert_inbox_items(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    limit: int = 12,
) -> list[dict[str, Any]]:
    """DG3 — Map goldmine delta alerts to approval inbox rows."""

    if not settings.forager_goldmine_dispatch_enabled:
        return []

    payload = await compose_forager_goldmine_alerts(session, tenant_id=tenant_id, limit=limit)
    if not payload.enabled or not payload.alerts:
        return []

    forager_ids = [uuid.UUID(alert.forager_id) for alert in payload.alerts]
    forager_rows = list(
        (
            await session.execute(
                select(ForagerORM).where(
                    ForagerORM.tenant_id == tenant_id,
                    ForagerORM.id.in_(forager_ids),
                ),
            )
        ).scalars().all(),
    )
    forager_map = {str(row.id): row for row in forager_rows}

    rows: list[dict[str, Any]] = []
    for alert in payload.alerts:
        forager = forager_map.get(alert.forager_id)
        rule_hint = derive_spawn_rule_match_hint(
            dict(forager.filter_config or {}) if forager is not None else None,
        )
        preview = alert.preview_items[0].title if alert.preview_items else ""
        detail_parts = [alert.headline]
        if preview:
            detail_parts.append(preview)
        if rule_hint:
            detail_parts.append(rule_hint)
        rows.append(
            {
                "forager_id": alert.forager_id,
                "forager_name": alert.forager_name,
                "source_type": alert.source_type,
                "new_item_count": alert.new_item_count,
                "detail": " · ".join(detail_parts)[:320],
                "skill_bundle": alert.skill_bundle,
            },
        )
    return rows


__all__ = [
    "compose_forager_goldmine_alerts",
    "compose_goldmine_alert_inbox_items",
    "derive_forager_skill_bundle",
    "derive_spawn_rule_match_hint",
    "ForagerGoldmineAlertRow",
    "ForagerGoldmineAlertsOut",
    "ForagerGoldminePreviewItem",
    "promote_forager_goldmine_dispatch",
]
