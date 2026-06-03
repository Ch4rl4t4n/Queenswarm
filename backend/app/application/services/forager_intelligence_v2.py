"""Forager Intelligence v2 — tenant-scoped stale scan + connector gaps (P8 #77)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.forager_intelligence import run_intelligence_scan
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant


class ForagerV2ProposalOut(BaseModel):
    """One forager v2 proposal row."""

    model_config = ConfigDict(extra="ignore")

    kind: str
    target: str
    priority: str
    rationale: str


class ForagerV2SnapshotOut(BaseModel):
    """Tenant forager intelligence v2 snapshot."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    global_proposal_count: int = 0
    connector_gaps: list[str] = Field(default_factory=list)
    proposals: list[ForagerV2ProposalOut] = Field(default_factory=list)


async def compose_forager_v2_snapshot(
    session: AsyncSession,
    *,
    tenant: Tenant | None,
    dashboard_user_id: uuid.UUID,
) -> ForagerV2SnapshotOut:
    """Combine global intelligence scan with tenant connector readiness gaps."""

    if not settings.forager_intelligence_v2_enabled:
        return ForagerV2SnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
        )

    scan = run_intelligence_scan()
    proposals_raw = list(scan.get("proposals") or [])[:20]
    proposals = [
        ForagerV2ProposalOut(
            kind=str(row.get("kind") or "unknown"),
            target=str(row.get("target") or ""),
            priority=str(row.get("priority") or "medium"),
            rationale=str(row.get("rationale") or "")[:300],
        )
        for row in proposals_raw
        if isinstance(row, dict)
    ]

    connector_gaps: list[str] = []
    existing_targets = {row.target for row in proposals if row.kind == "mcp_preset_skill"}

    if tenant is not None:
        from app.application.services.tool_gap_signal import list_tool_gaps

        for gap in await list_tool_gaps(tenant_id=tenant.id, limit=6):
            slug = str(gap.get("connector_slug") or "").strip()
            message = str(gap.get("message") or "").strip()
            if slug:
                connector_gaps.append(f"{slug}: {message[:120]}")
            template_id = str(gap.get("suggested_template_id") or "").strip()
            if template_id and template_id not in existing_targets:
                existing_targets.add(template_id)
                proposals.insert(
                    0,
                    ForagerV2ProposalOut(
                        kind="mcp_preset_skill",
                        target=template_id,
                        priority="high",
                        rationale=f"Session tool gap ({gap.get('kind')}): {message[:200]}",
                    ),
                )

    try:
        from app.application.services.prediction_market_trading import build_prediction_markets_status_snapshot

        pm = await build_prediction_markets_status_snapshot(session, dashboard_user_id=dashboard_user_id)
        active = pm.get("connectors_active") or {}
        if not active.get("polymarket_gamma"):
            connector_gaps.append("Install polymarket_gamma for market research.")
        if not active.get("polymarket_clob"):
            connector_gaps.append("Vault polymarket_clob before live trading lane.")
    except Exception:
        connector_gaps.append("Connector status unavailable — refresh Execution Studio.")

    if tenant is not None:
        studio = dict((tenant.operator_settings or {}).get("execution_studio") or {})
        recent = studio.get("recent_activity")
        if not isinstance(recent, list) or len(recent) < 3:
            proposals.append(
                ForagerV2ProposalOut(
                    kind="activity_cold",
                    target="execution_studio",
                    priority="medium",
                    rationale="Low publish/trading activity — run simulate workflows to warm recipes.",
                ),
            )

    return ForagerV2SnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        global_proposal_count=int(scan.get("proposal_count") or 0),
        connector_gaps=connector_gaps[:6],
        proposals=proposals[:25],
    )


__all__ = ["ForagerV2SnapshotOut", "compose_forager_v2_snapshot"]
