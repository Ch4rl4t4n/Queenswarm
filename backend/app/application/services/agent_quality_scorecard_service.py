"""POS-H6 — Agent Quality scorecard for Mission Home (simulation pass rate + session health)."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.simulation_pass_rate_service import compose_simulation_pass_rate_trend
from app.core.config import settings
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession

QualityStatus = Literal["healthy", "warn", "critical", "unknown"]


class MissionAgentQualityStripOut(BaseModel):
    """Compact agent quality rollup on Mission Home."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    status: QualityStatus = "unknown"
    pass_rate_7d_pct: float | None = None
    pass_rate_trend: str = "stable"
    stuck_sessions: int = 0
    active_sessions: int = 0
    operator_hint: str = ""
    harness_href: str = "/settings/harness#harness-closed-review-loop"
    scorecard_href: str = "/cockpit#business"


async def compose_agent_quality_strip(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> MissionAgentQualityStripOut:
    """Build agent quality KPI strip from simulation pass rate + session counts."""

    if not settings.agent_quality_scorecard_enabled:
        return MissionAgentQualityStripOut(enabled=False)

    trend = await compose_simulation_pass_rate_trend(session, tenant_id=tenant_id)

    stuck_stmt = select(func.count()).select_from(SupervisorSession).where(
        SupervisorSession.tenant_id == tenant_id,
        SupervisorSession.status == "needs_input",
    )
    active_stmt = select(func.count()).select_from(SupervisorSession).where(
        SupervisorSession.tenant_id == tenant_id,
        SupervisorSession.status == "running",
    )
    stuck = int((await session.scalar(stuck_stmt)) or 0)
    active = int((await session.scalar(active_stmt)) or 0)

    status: QualityStatus = trend.status if trend.enabled else "unknown"
    if stuck >= 2 and status == "healthy":
        status = "warn"
    if stuck >= 4:
        status = "critical"

    hint = trend.operator_hint
    if stuck > 0:
        hint = f"{stuck} session(s) need input — unblock verify loop before starting new work."
    elif trend.pass_rate_7d_pct is not None and trend.pass_rate_7d_pct >= trend.gate_threshold_pct:
        hint = "Simulation pass rate healthy — harness verify-first loop is holding."

    return MissionAgentQualityStripOut(
        enabled=True,
        status=status,
        pass_rate_7d_pct=trend.pass_rate_7d_pct,
        pass_rate_trend=trend.trend,
        stuck_sessions=stuck,
        active_sessions=active,
        operator_hint=hint,
    )


__all__ = ["MissionAgentQualityStripOut", "compose_agent_quality_strip"]
