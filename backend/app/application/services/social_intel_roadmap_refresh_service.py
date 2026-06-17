"""SIG2 — Social intel → quarterly Tech SCV roadmap refresh (Forager + CBO action)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.mission_kanban import create_mission_triage_task
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.knowledge import KnowledgeItem
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

SETTINGS_KEY = "social_intel_roadmap_refresh"
SOCIAL_INTEL_TAGS = frozenset({"social-intel", "hivemind-candidate", "intel"})

RefreshStatus = Literal["due", "scheduled", "recent", "disabled", "insufficient_signals"]


class SocialIntelSignalPreviewOut(BaseModel):
    """One social intel row for quarterly digest preview."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    source_type: str
    source_url: str | None = None
    scraped_at: datetime | None = None
    confidence_score: float = 0.5


class SocialIntelRoadmapRefreshKpiOut(BaseModel):
    """Compact SIG2 rollup for CBO snapshot."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    status: RefreshStatus = "disabled"
    window_days: int = 90
    signal_count: int = 0
    due: bool = False
    last_refresh_at: datetime | None = None
    next_due_at: datetime | None = None
    last_task_id: str | None = None
    preview_signals: list[SocialIntelSignalPreviewOut] = Field(default_factory=list)
    operator_hint: str = ""
    innovation_lab_href: str = "/innovation-lab"
    four_lane_href: str = "/cockpit#four-lanes"


class SocialIntelRoadmapRefreshOut(BaseModel):
    """Full SIG2 snapshot for operator panel."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    kpi: SocialIntelRoadmapRefreshKpiOut
    goal_template: str = ""


class SocialIntelRoadmapRefreshRunOut(BaseModel):
    """Result of quarterly roadmap refresh run."""

    model_config = ConfigDict(extra="ignore")

    ok: bool = True
    status: str
    task_id: str | None = None
    href: str = "/tasks"
    signal_count: int = 0
    message: str = ""


GOAL_TEMPLATE = """\
SIG2 Quarterly Roadmap Refresh (Tech SCV lane — simulate-first).

Review social intel signals from the last 90 days and propose ROADMAP.md deltas:
1. List top 5 external signals with canonical source URLs.
2. Map each to a P10 track item (existing ⏳ row or new suggestion with ID).
3. Score each 1–5 on Queenswarm fit + revenue unblock potential.
4. Draft a quarterly refresh ticket — operator prioritizes; no auto-merge to main.
5. Route high-priority platform items to Innovation Lab (tech_scv lane).

Skills: social-intel-evaluator, competitor-scrape-analyze, decision-frameworks.
Deliver simulate-first digest tagged sig2-roadmap-refresh. Operator approves before commit.
""".strip()


def _settings_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    bucket = root.get(SETTINGS_KEY)
    return dict(bucket) if isinstance(bucket, dict) else {}


def _signal_title(row: KnowledgeItem) -> str:
    text = (row.content_text or "").strip().splitlines()
    if text:
        head = text[0].strip().lstrip("#").strip()
        if head:
            return head[:160]
    if row.source_url:
        return row.source_url[:160]
    return f"{row.source_type} signal"


def _has_social_intel_tag(tags: list[str] | None) -> bool:
    if not tags:
        return False
    lowered = {str(tag).strip().lower() for tag in tags}
    return bool(lowered & SOCIAL_INTEL_TAGS)


async def _load_social_intel_signals(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    window_days: int,
    limit: int = 24,
) -> list[KnowledgeItem]:
    """Load HiveMind rows tagged for social intel within the quarterly window."""

    since = datetime.now(tz=UTC) - timedelta(days=max(30, min(window_days, 120)))
    rows = list(
        (
            await session.scalars(
                select(KnowledgeItem)
                .where(
                    KnowledgeItem.tenant_id == tenant_id,
                    KnowledgeItem.scraped_at >= since,
                )
                .order_by(desc(KnowledgeItem.scraped_at))
                .limit(max(limit * 3, 40)),
            )
        ).all(),
    )
    filtered = [row for row in rows if _has_social_intel_tag(list(row.topic_tags or []))]
    return filtered[:limit]


def _parse_last_refresh(bucket: dict[str, Any]) -> datetime | None:
    raw = bucket.get("last_refresh_at")
    if not raw:
        return None
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None


def _compose_kpi(
    *,
    bucket: dict[str, Any],
    signals: list[KnowledgeItem],
    window_days: int,
    now: datetime,
) -> SocialIntelRoadmapRefreshKpiOut:
    last_refresh = _parse_last_refresh(bucket)
    refresh_days = int(settings.social_intel_roadmap_refresh_interval_days)
    min_signals = int(settings.social_intel_roadmap_refresh_min_signals)
    signal_count = len(signals)

    next_due_at: datetime | None = None
    if last_refresh is not None:
        next_due_at = last_refresh + timedelta(days=refresh_days)

    if not settings.social_intel_roadmap_refresh_enabled:
        status: RefreshStatus = "disabled"
        due = False
        hint = "SIG2 quarterly roadmap refresh disabled in deployment config."
    elif signal_count < min_signals:
        status = "insufficient_signals"
        due = False
        hint = (
            f"Need ≥{min_signals} social intel signals in last {window_days}d "
            f"(have {signal_count}). Run Social Intel foragers first."
        )
    elif last_refresh is None:
        status = "due"
        due = True
        hint = "First quarterly refresh — review weak signals and propose ROADMAP deltas."
    elif next_due_at is not None and now >= next_due_at:
        status = "due"
        due = True
        hint = f"Quarterly refresh due — last run {last_refresh.date().isoformat()}."
    else:
        status = "recent"
        due = False
        next_label = next_due_at.date().isoformat() if next_due_at else "—"
        hint = f"Last refresh {last_refresh.date().isoformat()} — next due ~{next_label}."

    preview = [
        SocialIntelSignalPreviewOut(
            id=str(row.id),
            title=_signal_title(row),
            source_type=str(row.source_type),
            source_url=row.source_url,
            scraped_at=row.scraped_at,
            confidence_score=float(row.confidence_score or 0.5),
        )
        for row in signals[:8]
    ]

    return SocialIntelRoadmapRefreshKpiOut(
        enabled=settings.social_intel_roadmap_refresh_enabled,
        generated_at=now,
        status=status,
        window_days=window_days,
        signal_count=signal_count,
        due=due,
        last_refresh_at=last_refresh,
        next_due_at=next_due_at,
        last_task_id=str(bucket.get("last_task_id") or "") or None,
        preview_signals=preview,
        operator_hint=hint,
    )


def _build_digest(*, signals: list[KnowledgeItem], window_days: int) -> str:
    lines = [
        f"=== SIG2 Social Intel Digest ({len(signals)} signals / {window_days}d) ===",
        "",
    ]
    for idx, row in enumerate(signals[:12], start=1):
        title = _signal_title(row)
        url = row.source_url or "—"
        excerpt = (row.content_text or "").strip().replace("\n", " ")[:280]
        lines.extend(
            [
                f"{idx}. **{title}**",
                f"   - source: {row.source_type} · {url}",
                f"   - confidence: {float(row.confidence_score or 0.5):.2f}",
                f"   - excerpt: {excerpt}",
                "",
            ],
        )
    lines.append(GOAL_TEMPLATE)
    return "\n".join(lines)


async def compose_social_intel_roadmap_refresh_kpi(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    tenant: Tenant | None = None,
) -> SocialIntelRoadmapRefreshKpiOut:
    """SIG2 KPI strip for CBO snapshot."""

    now = datetime.now(tz=UTC)
    if not settings.social_intel_roadmap_refresh_enabled:
        return SocialIntelRoadmapRefreshKpiOut(
            enabled=False,
            generated_at=now,
            status="disabled",
            operator_hint="SIG2 disabled.",
        )

    bucket = _settings_bucket(tenant.operator_settings if tenant else None)
    window_days = int(settings.social_intel_roadmap_refresh_window_days)
    signals = await _load_social_intel_signals(
        session,
        tenant_id=tenant_id,
        window_days=window_days,
    )
    return _compose_kpi(bucket=bucket, signals=signals, window_days=window_days, now=now)


async def compose_social_intel_roadmap_refresh_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    tenant: Tenant | None = None,
) -> SocialIntelRoadmapRefreshOut:
    """Full SIG2 snapshot for operator APIs."""

    kpi = await compose_social_intel_roadmap_refresh_kpi(
        session,
        tenant_id=tenant_id,
        tenant=tenant,
    )
    return SocialIntelRoadmapRefreshOut(
        enabled=kpi.enabled,
        generated_at=kpi.generated_at,
        kpi=kpi,
        goal_template=GOAL_TEMPLATE,
    )


async def _persist_refresh_meta(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    task_id: uuid.UUID,
    signal_count: int,
) -> None:
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        return
    root = dict(tenant.operator_settings or {})
    root[SETTINGS_KEY] = {
        "last_refresh_at": datetime.now(tz=UTC).isoformat(),
        "last_task_id": str(task_id),
        "last_signal_count": signal_count,
    }
    tenant.operator_settings = root
    await session.flush()


async def run_social_intel_roadmap_refresh(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    tenant: Tenant | None,
    created_by_subject: str,
    force: bool = False,
) -> SocialIntelRoadmapRefreshRunOut:
    """Create Tech SCV quarterly roadmap refresh triage task from social intel digest."""

    if not settings.social_intel_roadmap_refresh_enabled:
        raise ValueError("Social intel roadmap refresh is disabled.")

    snapshot = await compose_social_intel_roadmap_refresh_snapshot(
        session,
        tenant_id=tenant_id,
        tenant=tenant,
    )
    kpi = snapshot.kpi
    if not force and not kpi.due:
        return SocialIntelRoadmapRefreshRunOut(
            ok=False,
            status=kpi.status,
            signal_count=kpi.signal_count,
            message=kpi.operator_hint,
        )
    if kpi.signal_count < int(settings.social_intel_roadmap_refresh_min_signals):
        raise ValueError(kpi.operator_hint)

    window_days = kpi.window_days
    signals = await _load_social_intel_signals(
        session,
        tenant_id=tenant_id,
        window_days=window_days,
        limit=24,
    )
    digest = _build_digest(signals=signals, window_days=window_days)
    title = f"SIG2 · Quarterly roadmap refresh ({kpi.signal_count} signals)"

    triage = await create_mission_triage_task(
        session,
        task_text=digest,
        title=title[:120],
        priority=8,
        skills=[
            "social-intel-evaluator",
            "competitor-scrape-analyze",
            "decision-frameworks",
        ],
        extra_payload={
            "four_lane_id": "tech_scv",
            "sig2_roadmap_refresh": True,
            "signal_count": kpi.signal_count,
            "window_days": window_days,
        },
    )
    await _persist_refresh_meta(
        session,
        tenant_id=tenant_id,
        task_id=triage.task.id,
        signal_count=kpi.signal_count,
    )
    _logger.info(
        "social_intel_roadmap_refresh.created",
        agent_id="social_intel_roadmap_refresh",
        swarm_id=str(tenant_id),
        task_id=str(triage.task.id),
        signal_count=kpi.signal_count,
    )
    return SocialIntelRoadmapRefreshRunOut(
        ok=True,
        status="created",
        task_id=str(triage.task.id),
        href="/tasks",
        signal_count=kpi.signal_count,
        message="Quarterly roadmap refresh triage task created — review in Mission Control.",
    )


async def count_social_intel_signals(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    window_days: int | None = None,
) -> int:
    """Count social intel tagged rows in window (for tests/metrics)."""

    days = window_days or int(settings.social_intel_roadmap_refresh_window_days)
    signals = await _load_social_intel_signals(
        session,
        tenant_id=tenant_id,
        window_days=days,
        limit=100,
    )
    return len(signals)


__all__ = [
    "GOAL_TEMPLATE",
    "SETTINGS_KEY",
    "SocialIntelRoadmapRefreshKpiOut",
    "SocialIntelRoadmapRefreshOut",
    "SocialIntelRoadmapRefreshRunOut",
    "SocialIntelSignalPreviewOut",
    "compose_social_intel_roadmap_refresh_kpi",
    "compose_social_intel_roadmap_refresh_snapshot",
    "count_social_intel_signals",
    "run_social_intel_roadmap_refresh",
]
