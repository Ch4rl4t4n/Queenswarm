"""Live lane — Polymarket trading + publish OAuth unified prep (#65)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.prediction_market_trading import build_prediction_markets_status_snapshot
from app.application.services.publish_operator_onboarding import (
    _has_live_audit,
    _has_simulate_audit,
    compose_publish_onboarding_snapshot,
)
from app.application.services.social_publish import SOCIAL_OAUTH_CHANNEL_IDS, build_social_publish_snapshot
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant


class LiveLaneStepOut(BaseModel):
    """One live-lane checklist row."""

    model_config = ConfigDict(extra="ignore")

    id: str
    lane: str
    label: str
    status: str
    detail: str


class LiveLaneActionOut(BaseModel):
    """Operator action for live lane."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    detail: str
    priority: str
    href: str | None = None


class LiveLaneSnapshotOut(BaseModel):
    """Unified trading + publish live lane readiness."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    progress_pct: int = 0
    polymarket_prep_pct: int = 0
    publish_prep_pct: int = 0
    trading_live_flag: bool = False
    publish_live_flag: bool = False
    ready_for_trading_live: bool = False
    ready_for_publish_live: bool = False
    steps: list[LiveLaneStepOut] = Field(default_factory=list)
    actions: list[LiveLaneActionOut] = Field(default_factory=list)
    docs: str = "docs/OPERATOR_PREDICTION_MARKETS_SETUP.md"


class LiveLanePreflightLaneOut(BaseModel):
    """Preflight result for one lane."""

    model_config = ConfigDict(extra="ignore")

    allowed: bool
    blockers: list[str] = Field(default_factory=list)


class LiveLanePreflightOut(BaseModel):
    """Dry-run preflight — no orders, no live posts."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    trading: LiveLanePreflightLaneOut
    publish: LiveLanePreflightLaneOut


async def compose_live_lane_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
) -> LiveLaneSnapshotOut:
    """Merge Polymarket readiness + publish OAuth/simulate into one operator view."""

    if not settings.live_lane_snapshot_enabled:
        return LiveLaneSnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
        )

    pm = await build_prediction_markets_status_snapshot(session, dashboard_user_id=dashboard_user_id)
    readiness = pm.get("polymarket_readiness") or {}
    polymarket_pct = int(readiness.get("progress_pct") or 0)
    pm_ready = bool(readiness.get("ready"))

    publish_onboard = await compose_publish_onboarding_snapshot(
        session,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
    )
    publish_pct = publish_onboard.progress_pct

    social = await build_social_publish_snapshot(
        session,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
        limit=5,
    )
    oauth_count = sum(
        1
        for row in social.channels
        if row.channel in SOCIAL_OAUTH_CHANNEL_IDS and row.credentials_ok and row.active
    )
    simulate_ok = _has_simulate_audit(tenant)
    publish_live_audit = _has_live_audit(tenant)

    trading_flag = bool(settings.prediction_markets_live_trading_enabled)
    publish_flag = bool(settings.social_publish_live_enabled)

    steps: list[LiveLaneStepOut] = []
    for step in readiness.get("steps") or []:
        if not isinstance(step, dict):
            continue
        steps.append(
            LiveLaneStepOut(
                id=f"pm_{step.get('id', 'step')}",
                lane="trading",
                label=str(step.get("label") or ""),
                status="done" if step.get("done") else "pending",
                detail=str(step.get("detail") or "")[:240],
            ),
        )

    steps.extend(
        [
            LiveLaneStepOut(
                id="social_oauth",
                lane="publish",
                label="Social OAuth connected",
                status="done" if oauth_count > 0 else "pending",
                detail=f"{oauth_count} channel(s) with valid OAuth." if oauth_count else "Connect Instagram/X/TikTok.",
            ),
            LiveLaneStepOut(
                id="social_simulate",
                lane="publish",
                label="Social simulate OK",
                status="done" if simulate_ok else "pending",
                detail="Run simulate in Execution Studio before live API.",
            ),
            LiveLaneStepOut(
                id="publish_live_flag",
                lane="publish",
                label="Publish live flag",
                status="done" if publish_flag else "pending",
                detail="SOCIAL_PUBLISH_LIVE_ENABLED=true after OAuth + simulate review.",
            ),
        ],
    )

    done = sum(1 for step in steps if step.status == "done")
    progress_pct = int(round(100 * done / max(len(steps), 1)))

    ready_trading = pm_ready and trading_flag
    ready_publish = oauth_count > 0 and simulate_ok and publish_flag

    actions: list[LiveLaneActionOut] = []
    if polymarket_pct < 100:
        actions.append(
            LiveLaneActionOut(
                id="polymarket_vault",
                label=f"Polymarket prep {polymarket_pct}%",
                detail="Install Gamma + vault CLOB credentials.",
                priority="high",
                href="/integrations?tab=studio#trading-cockpit",
            ),
        )
    if not trading_flag and pm_ready:
        actions.append(
            LiveLaneActionOut(
                id="trading_live_flag",
                label="Enable trading live flag (env)",
                detail="PREDICTION_MARKETS_LIVE_TRADING_ENABLED=true — operator script only.",
                priority="high",
                href="/integrations?tab=studio#trading-cockpit",
            ),
        )
    if oauth_count == 0:
        actions.append(
            LiveLaneActionOut(
                id="social_oauth",
                label="Connect social OAuth",
                detail="Marketplace → social connector → Connector Hub OAuth.",
                priority="medium",
                href="/integrations?tab=marketplace",
            ),
        )
    if not simulate_ok and oauth_count > 0:
        actions.append(
            LiveLaneActionOut(
                id="social_simulate",
                label="Run social simulate",
                detail="Approve pack → Social publish → Simulate.",
                priority="medium",
                href="/integrations?tab=studio#social-publish",
            ),
        )
    if not publish_flag and simulate_ok:
        actions.append(
            LiveLaneActionOut(
                id="publish_live_flag",
                label="Enable publish live flag (env)",
                detail="SOCIAL_PUBLISH_LIVE_ENABLED=true after review.",
                priority="medium",
                href="/integrations?tab=studio#social-publish",
            ),
        )

    return LiveLaneSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        progress_pct=progress_pct,
        polymarket_prep_pct=polymarket_pct,
        publish_prep_pct=publish_pct,
        trading_live_flag=trading_flag,
        publish_live_flag=publish_flag,
        ready_for_trading_live=ready_trading,
        ready_for_publish_live=ready_publish or publish_live_audit,
        steps=steps[:14],
        actions=actions[:8],
    )


async def preflight_live_lane(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
) -> LiveLanePreflightOut:
    """Dry-run blockers for trading + publish live lanes — no side effects."""

    if not settings.live_lane_snapshot_enabled:
        return LiveLanePreflightOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            trading=LiveLanePreflightLaneOut(allowed=False, blockers=["live_lane_disabled"]),
            publish=LiveLanePreflightLaneOut(allowed=False, blockers=["live_lane_disabled"]),
        )

    snap = await compose_live_lane_snapshot(
        session,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
    )

    trading_blockers: list[str] = []
    if not settings.prediction_markets_enabled:
        trading_blockers.append("PREDICTION_MARKETS_ENABLED=false")
    if snap.polymarket_prep_pct < 100:
        trading_blockers.append(f"Polymarket prep incomplete ({snap.polymarket_prep_pct}%)")
    if not snap.trading_live_flag:
        trading_blockers.append("PREDICTION_MARKETS_LIVE_TRADING_ENABLED=false")

    publish_blockers: list[str] = []
    if not any(step.id == "social_oauth" and step.status == "done" for step in snap.steps):
        publish_blockers.append("Social OAuth not connected")
    if not any(step.id == "social_simulate" and step.status == "done" for step in snap.steps):
        publish_blockers.append("No successful social simulate in audit")
    if not snap.publish_live_flag:
        publish_blockers.append("SOCIAL_PUBLISH_LIVE_ENABLED=false")

    return LiveLanePreflightOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        trading=LiveLanePreflightLaneOut(allowed=not trading_blockers, blockers=trading_blockers),
        publish=LiveLanePreflightLaneOut(allowed=not publish_blockers, blockers=publish_blockers),
    )


__all__ = [
    "LiveLanePreflightOut",
    "LiveLaneSnapshotOut",
    "compose_live_lane_snapshot",
    "preflight_live_lane",
]
