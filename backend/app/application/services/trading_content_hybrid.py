"""Trading + Content Hybrid snapshot — dual-lane operator view (P9 #80)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.publish_performance import build_publish_performance_snapshot
from app.application.services.trading_cockpit import compose_trading_cockpit_snapshot
from app.core.config import settings
from app.domain.outputs.service import list_owned_deliverables
from app.infrastructure.persistence.models.tenant import Tenant


class HybridActionOut(BaseModel):
    """One hybrid lane action."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    detail: str
    priority: str
    href: str | None = None


class TradingContentHybridSnapshotOut(BaseModel):
    """Unified trading + publish content hybrid snapshot."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    paper_pnl_usd: float = 0.0
    paper_equity_usd: float = 0.0
    trade_content_drafts: int = 0
    publish_pending: int = 0
    publish_live_posts: int = 0
    polymarket_prep_pct: int = 0
    actions: list[HybridActionOut] = Field(default_factory=list)


async def compose_trading_content_hybrid_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
) -> TradingContentHybridSnapshotOut:
    """Compose trading cockpit + publish performance + trade→content counts."""

    if not settings.trading_content_hybrid_enabled:
        return TradingContentHybridSnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
        )

    trading = await compose_trading_cockpit_snapshot(
        session,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
    )
    perf = build_publish_performance_snapshot(tenant, window_days=30)

    trade_rows = await list_owned_deliverables(
        session,
        dashboard_user_id=dashboard_user_id,
        limit=60,
        tag="trade-to-content",
    )

    perf_data = trading.performance
    pm = trading.prediction_markets
    readiness = pm.get("polymarket_readiness") or {}
    prep_pct = int(readiness.get("progress_pct") or 0)

    actions: list[HybridActionOut] = []
    if prep_pct < 100:
        actions.append(
            HybridActionOut(
                id="polymarket_prep",
                label=f"Polymarket prep {prep_pct}%",
                detail="Complete Gamma + CLOB + live flag before real lane.",
                priority="high",
                href="/integrations?tab=studio#trading-cockpit",
            ),
        )
    if trade_rows:
        actions.append(
            HybridActionOut(
                id="review_trade_content",
                label=f"{len(trade_rows)} trade→content draft(s)",
                detail="Review auto-generated publish packs from paper fills.",
                priority="medium",
                href="/integrations?tab=studio#publish-queue",
            ),
        )
    if perf.live_posts == 0 and perf.totals.get("social_simulate", 0) >= 2:
        actions.append(
            HybridActionOut(
                id="first_live",
                label="Consider first live publish",
                detail=f"{perf.totals.get('social_simulate', 0)} successful simulates in window.",
                priority="low",
                href="/integrations?tab=studio",
            ),
        )

    return TradingContentHybridSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        paper_pnl_usd=float(perf_data.get("total_pnl_usd") or 0.0),
        paper_equity_usd=float(perf_data.get("equity_usd") or 0.0),
        trade_content_drafts=len(trade_rows),
        publish_pending=int(perf.totals.get("queue_approved", 0)) - int(perf.totals.get("social_simulate", 0)),
        publish_live_posts=perf.live_posts,
        polymarket_prep_pct=prep_pct,
        actions=actions[:6],
    )


__all__ = ["TradingContentHybridSnapshotOut", "compose_trading_content_hybrid_snapshot"]
