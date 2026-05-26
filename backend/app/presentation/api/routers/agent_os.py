"""Agent OS API — P8 autonomy snapshot + analysis consensus."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.agent_os import AgentOsSnapshotOut, compose_agent_os_snapshot
from app.application.services.analysis_swarm import AnalysisConsensusOut, run_analysis_consensus
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/agent-os", tags=["Agent OS"])


class AnalysisConsensusRequest(BaseModel):
    """Request body for analysis swarm consensus."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    task: str = Field(min_length=2, max_length=500)
    symbol: str = Field(min_length=1, max_length=32)
    side_hint: str = Field(default="buy", max_length=16)
    signal_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


def _require_enabled() -> None:
    if not settings.agent_os_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent OS disabled.")


@router.get("", response_model=AgentOsSnapshotOut, summary="Agent OS autonomy snapshot")
async def get_agent_os_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> AgentOsSnapshotOut:
    """Unified P8 snapshot — cross-swarm, imitation, behavioral proposals."""

    _require_enabled()
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    return await compose_agent_os_snapshot(db, tenant_id=tenant_id, tenant=tenant)


@router.post(
    "/analysis/consensus",
    response_model=AnalysisConsensusOut,
    summary="Run Analysis Swarm consensus",
)
async def post_analysis_consensus(
    body: AnalysisConsensusRequest,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> AnalysisConsensusOut:
    """3-lane consensus — simulate-first, no live execution."""

    if not settings.analysis_swarm_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis swarm disabled.")
    _ = principal
    return await run_analysis_consensus(
        task=body.task,
        symbol=body.symbol,
        side_hint=body.side_hint,
        signal_confidence=body.signal_confidence,
    )


__all__ = ["router"]
