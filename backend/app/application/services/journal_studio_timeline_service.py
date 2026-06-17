"""Track O TJ1 — Journal Studio timeline and workspace snapshot."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.journal_studio_settings_service import (
    JournalStudioRoutineKpiOut,
    compose_journal_studio_routine_kpi,
    get_journal_studio_settings,
)
from app.application.services.trading_cockpit import ensure_primary_trading_project
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.external_project import ExternalProjectRunAudit
from app.infrastructure.persistence.models.paper_trading import PaperTradingFill
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

TimelineEntryKind = Literal["paper_fill", "live_run", "manual_entry", "review_session"]


class JournalTimelineEntryOut(BaseModel):
    """One row on the trading journal timeline."""

    model_config = ConfigDict(extra="ignore")

    id: str
    kind: TimelineEntryKind
    title: str
    detail: str
    occurred_at: datetime
    venue: str | None = None
    symbol: str | None = None
    side: str | None = None
    notional_usd: float | None = None
    pnl_usd: float | None = None
    tags: list[str] = Field(default_factory=list)
    href: str | None = None


class JournalTimelineOut(BaseModel):
    """Timeline snapshot for trading journal module."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    window_days: int = 90
    entry_count: int = 0
    paper_fill_count: int = 0
    live_run_count: int = 0
    manual_entry_count: int = 0
    review_session_count: int = 0
    items: list[JournalTimelineEntryOut] = Field(default_factory=list)
    operator_hint: str = ""
    workspace_href: str = "/apps-tools/trading-journal?section=timeline#journal-studio-timeline"


class JournalStudioPanelOut(BaseModel):
    """Lazy panel descriptor."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    lazy: bool = True
    status: str = "ready"


class JournalStudioWorkspaceSnapshotOut(BaseModel):
    """TJ1 workspace snapshot — config summary + timeline preview."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    generated_at: datetime
    capability_key: str = "apps.trading.journal_studio.v1"
    panels: list[JournalStudioPanelOut] = Field(default_factory=list)
    routine: JournalStudioRoutineKpiOut | None = None
    timeline_preview: list[JournalTimelineEntryOut] = Field(default_factory=list)
    settings_enabled: bool = True
    obsidian_subfolder: str = "Trading/Journal"
    enabled_field_count: int = 0
    mistake_tag_count: int = 0
    studio_preset: str = "trading"
    module_title: str = "Trading Journal"
    module_subtitle: str = ""
    operator_hint: str = ""
    workspace_href: str = "/apps-tools/trading-journal?section=timeline#journal-studio-timeline"


def _manual_entries_bucket(operator_settings: dict[str, Any] | None) -> list[dict[str, Any]]:
    from app.application.services.journal_studio_settings_service import JOURNAL_STUDIO_SETTINGS_KEY

    root = dict(operator_settings or {})
    bucket = root.get(JOURNAL_STUDIO_SETTINGS_KEY)
    if not isinstance(bucket, dict):
        return []
    raw = bucket.get("manual_entries")
    if not isinstance(raw, list):
        return []
    return [dict(row) for row in raw if isinstance(row, dict)]


def _parse_manual_entry(raw: dict[str, Any]) -> JournalTimelineEntryOut | None:
    entry_id = str(raw.get("id") or "").strip()
    title = str(raw.get("title") or raw.get("thesis") or "Manual journal entry").strip()
    if not entry_id or not title:
        return None
    occurred_raw = raw.get("occurred_at") or raw.get("created_at")
    occurred_at: datetime
    if isinstance(occurred_raw, str):
        try:
            occurred_at = datetime.fromisoformat(occurred_raw.replace("Z", "+00:00"))
        except ValueError:
            occurred_at = datetime.now(tz=UTC)
    else:
        occurred_at = datetime.now(tz=UTC)
    tags_raw = raw.get("tags") or raw.get("mistake_tags")
    tags = [str(t).strip() for t in tags_raw][:12] if isinstance(tags_raw, list) else []
    return JournalTimelineEntryOut(
        id=f"manual:{entry_id}",
        kind="manual_entry",
        title=title[:200],
        detail=str(raw.get("lesson") or raw.get("detail") or raw.get("outcome") or "")[:500],
        occurred_at=occurred_at,
        venue=str(raw.get("venue")) if raw.get("venue") else None,
        symbol=str(raw.get("symbol")) if raw.get("symbol") else None,
        pnl_usd=float(raw["pnl_usd"]) if raw.get("pnl_usd") is not None else None,
        tags=tags,
        href=f"/apps-tools/trading-journal?section=timeline#entry-{entry_id}",
    )


async def compose_journal_timeline(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
    limit: int = 50,
    window_days: int = 90,
) -> JournalTimelineOut:
    """Merge paper fills, live runs, manual entries, and review sessions."""

    now = datetime.now(tz=UTC)
    if not settings.journal_studio_enabled:
        return JournalTimelineOut(
            enabled=False,
            generated_at=now,
            operator_hint="Journal studio disabled.",
        )

    cap = max(1, min(limit, 100))
    window = max(7, min(window_days, 365))
    since = now - timedelta(days=window)
    items: list[JournalTimelineEntryOut] = []

    if tenant is not None:
        for raw in _manual_entries_bucket(tenant.operator_settings):
            parsed = _parse_manual_entry(raw)
            if parsed is None or parsed.occurred_at < since:
                continue
            items.append(parsed)

        lane = dict(tenant.operator_settings or {}).get("trading_lane")
        lane_dict = dict(lane) if isinstance(lane, dict) else {}
        try:
            project = await ensure_primary_trading_project(
                session,
                owner_id=dashboard_user_id,
                tenant=tenant,
                lane=lane_dict,
            )
            fill_rows = await session.scalars(
                select(PaperTradingFill)
                .where(
                    PaperTradingFill.tenant_id == tenant_id,
                    PaperTradingFill.project_id == project.id,
                    PaperTradingFill.created_at >= since,
                )
                .order_by(desc(PaperTradingFill.created_at))
                .limit(cap),
            )
            for fill in fill_rows:
                side = str(fill.side or "").upper()
                items.append(
                    JournalTimelineEntryOut(
                        id=f"fill:{fill.id}",
                        kind="paper_fill",
                        title=f"{side} {fill.symbol}",
                        detail=(fill.signal_note or f"Paper fill @ ${float(fill.fill_price_usd):.2f}").strip()[:500],
                        occurred_at=fill.created_at,
                        venue="paper",
                        symbol=str(fill.symbol),
                        side=side.lower(),
                        notional_usd=float(fill.notional_usd),
                        tags=["paper"],
                        href="/apps-tools/trading-automation?section=cockpit#trading-cockpit",
                    ),
                )

            audit_rows = await session.scalars(
                select(ExternalProjectRunAudit)
                .where(
                    ExternalProjectRunAudit.tenant_id == tenant_id,
                    ExternalProjectRunAudit.project_id == project.id,
                    ExternalProjectRunAudit.created_at >= since,
                )
                .order_by(desc(ExternalProjectRunAudit.created_at))
                .limit(cap),
            )
            for row in audit_rows:
                if row.action_slug not in {"execute_trade", "order_post", "order_create"}:
                    continue
                items.append(
                    JournalTimelineEntryOut(
                        id=f"run:{row.id}",
                        kind="live_run",
                        title=f"Live {row.action_slug}",
                        detail=f"{'OK' if row.ok else 'Blocked'} · latency {row.latency_ms}ms",
                        occurred_at=row.created_at,
                        venue=str(project.settings.get("venue") if isinstance(project.settings, dict) else "polymarket"),
                        tags=["live" if row.ok else "blocked"],
                        href="/apps-tools/trading-automation?section=orders#broker-order-queue",
                    ),
                )
        except Exception as exc:  # noqa: BLE001 — timeline degrades gracefully
            _logger.warning(
                "journal_timeline.project_load_failed",
                agent_id="journal_studio",
                swarm_id=str(tenant_id),
                error=str(exc)[:200],
            )

        session_rows = await session.scalars(
            select(SupervisorSession)
            .where(
                SupervisorSession.tenant_id == tenant_id,
                SupervisorSession.started_at >= since,
            )
            .order_by(desc(SupervisorSession.started_at))
            .limit(cap),
        )
        for sup in session_rows:
            summary = dict(sup.context_summary or {}) if isinstance(sup.context_summary, dict) else {}
            lane = str(summary.get("lane") or "")
            if lane != "journal_studio_review" and "journal" not in str(sup.goal or "").lower():
                continue
            items.append(
                JournalTimelineEntryOut(
                    id=f"session:{sup.id}",
                    kind="review_session",
                    title="Journal review session",
                    detail=str(sup.goal or "")[:280],
                    occurred_at=sup.started_at or sup.created_at,
                    tags=["review"],
                    href=f"/agents/sessions/{sup.id}",
                ),
            )

    items.sort(key=lambda row: row.occurred_at, reverse=True)
    items = items[:cap]

    paper_count = sum(1 for row in items if row.kind == "paper_fill")
    live_count = sum(1 for row in items if row.kind == "live_run")
    manual_count = sum(1 for row in items if row.kind == "manual_entry")
    review_count = sum(1 for row in items if row.kind == "review_session")

    if not items:
        hint = "Timeline empty — paper fills, live runs, and review sessions appear here."
    else:
        hint = f"{len(items)} entries in last {window} days — newest first."

    return JournalTimelineOut(
        enabled=True,
        generated_at=now,
        window_days=window,
        entry_count=len(items),
        paper_fill_count=paper_count,
        live_run_count=live_count,
        manual_entry_count=manual_count,
        review_session_count=review_count,
        items=items,
        operator_hint=hint,
    )


def _default_panels(*, recall_label: str = "Pre-trade recall") -> list[JournalStudioPanelOut]:
    return [
        JournalStudioPanelOut(id="timeline", label="Timeline", lazy=False, status="ready"),
        JournalStudioPanelOut(id="entries", label="Trade entries", lazy=True, status="ready"),
        JournalStudioPanelOut(id="gardener", label="Overnight gardener", lazy=True, status="ready"),
        JournalStudioPanelOut(id="recall", label=recall_label, lazy=True, status="ready"),
        JournalStudioPanelOut(id="patterns", label="Pattern strip", lazy=True, status="ready"),
        JournalStudioPanelOut(id="settings", label="Studio settings", lazy=True, status="ready"),
    ]


async def compose_journal_studio_workspace_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
) -> JournalStudioWorkspaceSnapshotOut:
    """TJ1 single read for trading journal Apps & Tools module."""

    now = datetime.now(tz=UTC)
    if not settings.journal_studio_enabled:
        return JournalStudioWorkspaceSnapshotOut(
            enabled=False,
            generated_at=now,
            operator_hint="Journal studio disabled — enable in deployment config.",
        )

    studio = await get_journal_studio_settings(session, tenant_id=tenant_id)
    routine = await compose_journal_studio_routine_kpi(session, tenant_id=tenant_id)
    timeline = await compose_journal_timeline(
        session,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
        limit=8,
        window_days=90,
    )
    enabled_fields = sum(1 for enabled in studio.field_toggles.values() if enabled)

    hint = timeline.operator_hint or studio.operator_hint
    if routine.routine_status == "missing" and studio.review_cron_enabled:
        hint = "Bootstrap review routine in Studio settings for overnight journal reviews."

    return JournalStudioWorkspaceSnapshotOut(
        enabled=True,
        generated_at=now,
        panels=_default_panels(recall_label=studio.recall_panel_label),
        routine=routine,
        timeline_preview=timeline.items[:8],
        settings_enabled=studio.enabled,
        obsidian_subfolder=studio.obsidian_subfolder,
        enabled_field_count=enabled_fields,
        mistake_tag_count=len(studio.mistake_tags),
        studio_preset=studio.studio_preset,
        module_title=studio.module_title,
        module_subtitle=studio.module_subtitle,
        operator_hint=hint,
    )


__all__ = [
    "JournalStudioWorkspaceSnapshotOut",
    "JournalTimelineEntryOut",
    "JournalTimelineOut",
    "compose_journal_studio_workspace_snapshot",
    "compose_journal_timeline",
]
