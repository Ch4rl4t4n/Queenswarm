"""Regret Simulator — pre-mortem score before live publish/trading (compose-only)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.publish_performance import compose_publish_performance_snapshot
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant

RegretRecommendation = Literal["go", "simulate_again", "abort"]


class RegretScenarioOut(BaseModel):
    """One pre-mortem failure scenario."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    detail: str
    severity: Literal["low", "medium", "high"]


class RegretSimulatorSnapshotOut(BaseModel):
    """Pre-mortem snapshot for live-gate UX."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    regret_score: int = Field(default=0, ge=0, le=100)
    recommendation: RegretRecommendation = "simulate_again"
    summary: str = ""
    scenarios: list[RegretScenarioOut] = Field(default_factory=list)


async def compose_regret_simulator_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
    lane: Literal["publish", "trading", "factory"] = "publish",
) -> RegretSimulatorSnapshotOut:
    """Heuristic pre-mortem from publish performance + trading readiness."""

    if not settings.operator_control_plane_enabled:
        return RegretSimulatorSnapshotOut(enabled=False, generated_at=datetime.now(tz=UTC))

    scenarios: list[RegretScenarioOut] = []
    score = 15

    perf = await compose_publish_performance_snapshot(
        session,
        tenant=tenant,
        dashboard_user_id=dashboard_user_id,
    )
    sim_rate = float(perf.simulate_success_rate_pct or 0)
    live_posts = int(perf.live_posts or 0)
    pending_sim = int(perf.totals.get("queue_approved", 0)) - int(perf.totals.get("social_simulate", 0))

    if pending_sim > 0:
        score += min(25, pending_sim * 8)
        scenarios.append(
            RegretScenarioOut(
                id="pending_simulate",
                label="Unsimulated queue items",
                detail=f"{pending_sim} approved pack(s) never simulated — live may fail channel validation.",
                severity="high" if pending_sim >= 2 else "medium",
            ),
        )

    if sim_rate < 70 and perf.totals.get("social_simulate", 0) >= 2:
        score += 20
        scenarios.append(
            RegretScenarioOut(
                id="low_sim_rate",
                label="Low simulate success rate",
                detail=f"Simulate OK rate {sim_rate:.0f}% in window — fix hooks/media before live.",
                severity="high",
            ),
        )

    if live_posts == 0 and lane in {"publish", "factory"}:
        score += 10
        scenarios.append(
            RegretScenarioOut(
                id="no_live_history",
                label="No live posts yet",
                detail="First live post carries reputational risk — prefer simulate + trusted auto.",
                severity="medium",
            ),
        )

    if lane == "trading":
        try:
            from app.application.services.prediction_market_trading import build_prediction_markets_status_snapshot

            pm = await build_prediction_markets_status_snapshot(session, dashboard_user_id=dashboard_user_id)
            if not pm.get("live_ready"):
                score += 30
                scenarios.append(
                    RegretScenarioOut(
                        id="trading_not_ready",
                        label="Live trading lane not ready",
                        detail="Polymarket CLOB / vault incomplete — abort live until preflight green.",
                        severity="high",
                    ),
                )
        except Exception:
            score += 15
            scenarios.append(
                RegretScenarioOut(
                    id="trading_unknown",
                    label="Trading status unavailable",
                    detail="Could not load trading preflight — simulate only.",
                    severity="medium",
                ),
            )

    score = min(100, score)
    if score >= 70:
        recommendation: RegretRecommendation = "abort"
        summary = "High regret risk — do not go live without fixing blockers."
    elif score >= 40:
        recommendation = "simulate_again"
        summary = "Moderate risk — run simulate again and review Oracle warnings."
    else:
        recommendation = "go"
        summary = "Low regret score — live gate acceptable with operator confirm."

    return RegretSimulatorSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        regret_score=score,
        recommendation=recommendation,
        summary=summary,
        scenarios=scenarios[:5],
    )


__all__ = [
    "RegretRecommendation",
    "RegretScenarioOut",
    "RegretSimulatorSnapshotOut",
    "compose_regret_simulator_snapshot",
]
