"""BA3 — Background Business Team: 3 heartbeat bees (no LLM, snapshot-only)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.marketing_product_catalog import build_catalog
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

BackgroundBeeId = Literal["marketing_ops", "revenue_ops", "factory_ops"]
BackgroundBeeStatus = Literal["idle", "ok", "attention", "disabled"]


class BackgroundBeeOut(BaseModel):
    """One background business bee heartbeat row."""

    model_config = ConfigDict(extra="ignore")

    bee_id: BackgroundBeeId
    label: str
    status: BackgroundBeeStatus = "idle"
    summary: str = ""
    pending_count: int = 0
    last_run_at: datetime | None = None
    href: str | None = None


class BackgroundBusinessTeamOut(BaseModel):
    """3-bee team rollup for CBO."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    generated_at: datetime
    bees: list[BackgroundBeeOut] = Field(default_factory=list)
    active_bee_count: int = 0
    attention_count: int = 0


TEAM_SETTINGS_KEY = "business_background_team"

BEE_LABELS: dict[BackgroundBeeId, str] = {
    "marketing_ops": "Marketing Ops",
    "revenue_ops": "Revenue Ops",
    "factory_ops": "Factory Ops",
}

BEE_HREFS: dict[BackgroundBeeId, str] = {
    "marketing_ops": "/integrations?tab=studio",
    "revenue_ops": "/factory",
    "factory_ops": "/factory",
}


def _team_root(tenant: Tenant | None) -> dict[str, Any]:
    if tenant is None:
        return {}
    root = dict(tenant.operator_settings or {})
    block = root.get(TEAM_SETTINGS_KEY)
    return dict(block) if isinstance(block, dict) else {}


def _persist_bee_state(
    tenant: Tenant,
    *,
    bee_id: BackgroundBeeId,
    status: BackgroundBeeStatus,
    summary: str,
    pending_count: int,
) -> None:
    """Store last heartbeat for one bee (caller commits)."""

    root = dict(tenant.operator_settings or {})
    team = dict(root.get(TEAM_SETTINGS_KEY) or {})
    team[bee_id] = {
        "status": status,
        "summary": summary[:500],
        "pending_count": pending_count,
        "last_run_at": datetime.now(tz=UTC).isoformat(),
    }
    root[TEAM_SETTINGS_KEY] = team
    tenant.operator_settings = root


async def _compose_marketing_ops(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> tuple[BackgroundBeeStatus, str, int]:
    """Marketing ops — four-lane digest + publish queue (read-only)."""

    from app.application.services.solo_operator_four_lanes import compose_four_lane_snapshot

    snap = await compose_four_lane_snapshot(db, tenant_id=tenant_id)
    marketing = next((lane for lane in snap.lanes if lane.lane_id == "marketing_najman"), None)
    pending = int(marketing.pending_digest_count if marketing else 0)
    promote = int(marketing.promote_ready_count if marketing else 0)
    active = bool(marketing and marketing.routine.is_active)

    if pending > 0 or promote > 0:
        summary = f"{pending} digest(s) need input, {promote} ready to promote"
        return "attention", summary, pending + promote
    if active:
        return "ok", "Marketing lane active — no pending digests", 0
    return "idle", "Marketing lane routine paused — enable in Agentic OS Lanes", 0


async def _compose_revenue_ops(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> tuple[BackgroundBeeStatus, str, int]:
    """Revenue ops — Gumroad scorecard gaps (read-only, no export LLM)."""

    _ = db, tenant_id
    from app.application.services.business_operator import compose_revenue_summary

    revenue = compose_revenue_summary()
    catalog = build_catalog()
    gap = max(0, catalog.product_count - catalog.gumroad_linked_count if hasattr(catalog, "gumroad_linked_count") else 0)
    linked = sum(1 for p in catalog.products if p.gumroad_url)
    gap = max(0, catalog.product_count - linked)

    if revenue.missing_reports:
        return "attention", f"Missing reports: {', '.join(revenue.missing_reports[:3])}", len(revenue.missing_reports)
    if gap > 0:
        return "attention", f"{gap} listing(s) without Gumroad URL", gap
    if linked > 0:
        return "ok", f"{linked} Gumroad listing(s) linked — {revenue.next_operator_action[:80]}", 0
    return "idle", revenue.next_operator_action or "No revenue artifacts yet", 0


async def _compose_factory_ops(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> tuple[BackgroundBeeStatus, str, int]:
    """Factory ops — skill factory queue depth (read-only)."""

    if not settings.skill_factory_enabled:
        return "disabled", "Skill Factory disabled in env", 0

    from app.application.services.skill_factory_service import compose_skill_factory_snapshot

    snap = await compose_skill_factory_snapshot(db, tenant_id=tenant_id)
    queued = int(snap.queue_count or 0)
    building = int(snap.building_count or 0)
    pending = queued + building
    launch = snap.launch_readiness
    sellable = int(launch.sellable_count if launch is not None else 0)

    if pending > 0:
        severity: BackgroundBeeStatus = "attention" if pending >= 3 else "ok"
        return severity, f"{queued} queued, {building} building, {sellable} sellable", pending
    if sellable > 0:
        return "ok", f"{sellable} sellable skill(s) — queue clear", 0
    return "idle", "Factory queue empty — run Research → Queue", 0


async def run_background_business_team_heartbeat(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    tenant: Tenant,
) -> BackgroundBusinessTeamOut:
    """Run snapshot-only heartbeat for all 3 bees and persist state."""

    if not settings.business_background_team_enabled:
        return BackgroundBusinessTeamOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
        )

    composers = {
        "marketing_ops": _compose_marketing_ops,
        "revenue_ops": _compose_revenue_ops,
        "factory_ops": _compose_factory_ops,
    }
    bees: list[BackgroundBeeOut] = []
    attention = 0

    for bee_id, compose in composers.items():
        try:
            status, summary, pending = await compose(db, tenant_id=tenant_id)
        except Exception as exc:
            _logger.warning(
                "background_business_team.bee_failed",
                agent_id=bee_id,
                swarm_id=str(tenant_id),
                error=str(exc)[:200],
            )
            status, summary, pending = "idle", f"Heartbeat skipped: {str(exc)[:120]}", 0

        if status == "attention":
            attention += 1
        _persist_bee_state(
            tenant,
            bee_id=bee_id,
            status=status,
            summary=summary,
            pending_count=pending,
        )
        bees.append(
            BackgroundBeeOut(
                bee_id=bee_id,
                label=BEE_LABELS[bee_id],
                status=status,
                summary=summary,
                pending_count=pending,
                last_run_at=datetime.now(tz=UTC),
                href=BEE_HREFS[bee_id],
            ),
        )

    active = sum(1 for bee in bees if bee.status in {"ok", "attention"})
    return BackgroundBusinessTeamOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        bees=bees,
        active_bee_count=active,
        attention_count=attention,
    )


async def compose_background_business_team(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    tenant: Tenant | None,
    refresh: bool = False,
) -> BackgroundBusinessTeamOut:
    """Read cached bee state or optionally refresh heartbeat."""

    if not settings.business_background_team_enabled:
        return BackgroundBusinessTeamOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
        )

    if refresh and tenant is not None:
        return await run_background_business_team_heartbeat(db, tenant_id=tenant_id, tenant=tenant)

    team = _team_root(tenant)
    bees: list[BackgroundBeeOut] = []
    attention = 0
    for bee_id in ("marketing_ops", "revenue_ops", "factory_ops"):
        row = team.get(bee_id)
        if not isinstance(row, dict):
            bees.append(
                BackgroundBeeOut(
                    bee_id=bee_id,
                    label=BEE_LABELS[bee_id],
                    status="idle",
                    summary="Awaiting first heartbeat",
                    href=BEE_HREFS[bee_id],
                ),
            )
            continue
        status_raw = str(row.get("status") or "idle")
        status: BackgroundBeeStatus = status_raw if status_raw in {"idle", "ok", "attention", "disabled"} else "idle"
        if status == "attention":
            attention += 1
        last_raw = row.get("last_run_at")
        last_run: datetime | None = None
        if isinstance(last_raw, str):
            try:
                last_run = datetime.fromisoformat(last_raw.replace("Z", "+00:00"))
            except ValueError:
                last_run = None
        bees.append(
            BackgroundBeeOut(
                bee_id=bee_id,
                label=BEE_LABELS[bee_id],
                status=status,
                summary=str(row.get("summary") or ""),
                pending_count=int(row.get("pending_count") or 0),
                last_run_at=last_run,
                href=BEE_HREFS[bee_id],
            ),
        )

    active = sum(1 for bee in bees if bee.status in {"ok", "attention"})
    return BackgroundBusinessTeamOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        bees=bees,
        active_bee_count=active,
        attention_count=attention,
    )


__all__ = [
    "BackgroundBeeOut",
    "BackgroundBusinessTeamOut",
    "compose_background_business_team",
    "run_background_business_team_heartbeat",
]
