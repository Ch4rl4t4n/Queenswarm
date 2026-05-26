"""Publish Performance Loop — aggregate publish audit into operator insights."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.execution_studio_activity import list_execution_activity
from app.application.services.publish_hook_optimizer import HookWinnerOut, build_hook_winner_stats
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant

PublishPerfInsightPriority = Literal["high", "medium", "low"]


class PublishChannelStatsOut(BaseModel):
    """Per-channel publish counts."""

    model_config = ConfigDict(extra="ignore")

    channel: str
    simulate_ok: int = 0
    live_ok: int = 0
    queue_approved: int = 0
    rejected: int = 0


class PublishPerformanceInsightOut(BaseModel):
    """One actionable insight from publish history."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    detail: str
    priority: PublishPerfInsightPriority


class PublishPerformanceSnapshotOut(BaseModel):
    """Single snapshot for Publish Performance panel."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    window_days: int = 30
    totals: dict[str, int] = Field(default_factory=dict)
    by_channel: list[PublishChannelStatsOut] = Field(default_factory=list)
    simulate_success_rate_pct: float = 0.0
    live_posts: int = 0
    queue_approval_rate_pct: float = 0.0
    insights: list[PublishPerformanceInsightOut] = Field(default_factory=list)
    recent_highlights: list[str] = Field(default_factory=list)
    hook_winners: list[HookWinnerOut] = Field(default_factory=list)


def _parse_at(value: str) -> datetime | None:
    raw = value.strip()
    if not raw:
        return None
    try:
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _derive_insights(
    *,
    totals: dict[str, int],
    by_channel: list[PublishChannelStatsOut],
    simulate_rate: float,
) -> list[PublishPerformanceInsightOut]:
    """Build operator insights from aggregated publish metrics."""

    insights: list[PublishPerformanceInsightOut] = []
    pending_sim = totals.get("queue_approved", 0) - totals.get("social_simulate", 0)
    if pending_sim > 0:
        insights.append(
            PublishPerformanceInsightOut(
                id="simulate_backlog",
                label=f"{pending_sim} approved pack(s) not yet simulated",
                detail="Run simulate in Social publish before first live post.",
                priority="high",
            ),
        )

    live = totals.get("social_live", 0) + totals.get("social_live_auto", 0)
    if live == 0 and totals.get("social_simulate", 0) >= 3:
        insights.append(
            PublishPerformanceInsightOut(
                id="ready_for_live",
                label="Simulate history looks good — consider first live",
                detail=f"{totals.get('social_simulate', 0)} successful simulates in window.",
                priority="medium",
            ),
        )

    if simulate_rate > 0 and simulate_rate < 70:
        insights.append(
            PublishPerformanceInsightOut(
                id="low_simulate_rate",
                label=f"Simulate success rate {simulate_rate:.0f}%",
                detail="Review failed simulates in Publish audit — fix OAuth or media.",
                priority="high",
            ),
        )

    top_channel = max(by_channel, key=lambda row: row.simulate_ok + row.live_ok, default=None)
    if top_channel and top_channel.live_ok >= 2:
        insights.append(
            PublishPerformanceInsightOut(
                id="channel_winner",
                label=f"Best channel: {top_channel.channel}",
                detail=f"{top_channel.live_ok} live posts — double down on hook variants.",
                priority="low",
            ),
        )

    if totals.get("queue_rejected", 0) >= 3:
        insights.append(
            PublishPerformanceInsightOut(
                id="high_reject",
                label=f"{totals['queue_rejected']} packs rejected",
                detail="Tune Marketing Ops bee or critic thresholds before scaling.",
                priority="medium",
            ),
        )

    return insights[:6]


def build_publish_performance_snapshot(
    tenant: Tenant | None,
    *,
    window_days: int = 30,
) -> PublishPerformanceSnapshotOut:
    """Aggregate publish audit events into performance metrics."""

    if not settings.publish_performance_enabled:
        return PublishPerformanceSnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            window_days=window_days,
        )

    cap_days = max(1, min(window_days, 90))
    cutoff = datetime.now(tz=UTC) - timedelta(days=cap_days)
    rows = list_execution_activity(tenant, limit=200)

    totals: dict[str, int] = {
        "events": 0,
        "queue_approved": 0,
        "queue_rejected": 0,
        "social_simulate": 0,
        "social_simulate_ok": 0,
        "social_live": 0,
        "social_live_auto": 0,
        "scheduled_simulate": 0,
        "scheduled_live_auto": 0,
    }
    channel_map: dict[str, PublishChannelStatsOut] = {}
    highlights: list[str] = []

    for row in rows:
        event_type = str(row.get("event_type") or "")
        if not event_type.startswith("publish_"):
            continue
        at_raw = str(row.get("at") or "")
        at_dt = _parse_at(at_raw)
        if at_dt is not None and at_dt < cutoff:
            continue

        totals["events"] += 1
        payload = dict(row.get("payload") or {})
        channel = str(payload.get("channel") or "unknown").strip() or "unknown"
        ok = payload.get("ok") if isinstance(payload.get("ok"), bool) else None

        if channel not in channel_map:
            channel_map[channel] = PublishChannelStatsOut(channel=channel)
        ch = channel_map[channel]

        if event_type == "publish_queue_approved":
            totals["queue_approved"] += 1
            ch.queue_approved += 1
        elif event_type == "publish_queue_rejected":
            totals["queue_rejected"] += 1
            ch.rejected += 1
        elif event_type == "publish_social_simulate":
            totals["social_simulate"] += 1
            if ok is not False:
                totals["social_simulate_ok"] += 1
                ch.simulate_ok += 1
        elif event_type == "publish_social_live":
            totals["social_live"] += 1
            if ok is not False:
                ch.live_ok += 1
                highlights.append(str(row.get("message") or "")[:120])
        elif event_type == "publish_social_live_auto":
            totals["social_live_auto"] += 1
            if ok is not False:
                ch.live_ok += 1
        elif event_type == "publish_scheduled_simulate":
            totals["scheduled_simulate"] += 1
        elif event_type == "publish_scheduled_live_auto":
            totals["scheduled_live_auto"] += 1

    sim_total = totals["social_simulate"]
    sim_ok = totals["social_simulate_ok"]
    simulate_rate = round(100.0 * sim_ok / sim_total, 1) if sim_total else 0.0

    reviewed = totals["queue_approved"] + totals["queue_rejected"]
    approval_rate = round(100.0 * totals["queue_approved"] / reviewed, 1) if reviewed else 0.0

    live_posts = totals["social_live"] + totals["social_live_auto"] + totals["scheduled_live_auto"]
    by_channel = sorted(channel_map.values(), key=lambda r: r.live_ok + r.simulate_ok, reverse=True)

    insights = _derive_insights(totals=totals, by_channel=by_channel, simulate_rate=simulate_rate)

    return PublishPerformanceSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        window_days=cap_days,
        totals=totals,
        by_channel=by_channel[:12],
        simulate_success_rate_pct=simulate_rate,
        live_posts=live_posts,
        queue_approval_rate_pct=approval_rate,
        insights=insights,
        recent_highlights=highlights[:5],
    )


async def compose_publish_performance_snapshot(
    session: AsyncSession,
    *,
    tenant: Tenant | None,
    dashboard_user_id: uuid.UUID,
    window_days: int = 30,
) -> PublishPerformanceSnapshotOut:
    """Build publish performance snapshot with hook optimizer winners."""

    snap = build_publish_performance_snapshot(tenant, window_days=window_days)
    hook_winners = await build_hook_winner_stats(session, dashboard_user_id=dashboard_user_id)
    return snap.model_copy(update={"hook_winners": hook_winners})


__all__ = [
    "PublishPerformanceSnapshotOut",
    "build_publish_performance_snapshot",
    "compose_publish_performance_snapshot",
]
