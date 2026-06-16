"""Trading Cockpit — Polymarket real-money agent control for Execution Studio."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.prediction_market_trading import (
    PREDICTION_VENUES,
    build_prediction_markets_status_snapshot,
    resolve_connector_slug,
)
from app.core.config import settings
from app.domain.external.registry import aggregate_metrics, list_projects_for_owner, recent_run_series
from app.infrastructure.persistence.models.external_project import ExternalProject, ExternalProjectRunAudit
from app.infrastructure.persistence.models.tenant import Tenant

TradingMode = Literal["real"]
TradingVenueId = Literal["polymarket"]
ExecutionFlow = Literal["simulate_first", "manual_approve", "trusted_auto"]

TRADING_LANE_KEY = "trading_lane"

VENUE_CATALOG: list[dict[str, str]] = [
    {
        "id": "polymarket",
        "label": "Polymarket · prediction markets",
        "mode": "real",
        "description": "Real USDC on Polygon — fund wallet on polymarket.com.",
    },
]

DEFAULT_TRADING_LANE: dict[str, Any] = {
    "default_mode": "real",
    "venue": "polymarket",
    "behavior_principles": (
        "Polymarket live only — no paper simulation. "
        "Run prediction evaluator consensus before any order. "
        "Max 2% bankroll per market. Stop after daily loss limit. "
        "Every live order requires risk gate + operator approval until trusted."
    ),
    "execution_flow": "manual_approve",
    "trusted_auto_min_simulates": 5,
    "auto_tick": False,
    "watchlist": [],
    "risk": {
        "max_order_usd": 100.0,
        "max_daily_loss_usd": 250.0,
        "max_risk_pct_per_trade": 2.0,
        "confidence_threshold": 0.75,
    },
    "notifications": {
        "telegram_on_fill": True,
        "telegram_on_daily_report": True,
    },
}

FUNDING_LINKS: dict[str, str] = {
    "polymarket": "https://polymarket.com",
}


def _trading_lane_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    lane = dict(root.get(TRADING_LANE_KEY) or {})
    merged = {**DEFAULT_TRADING_LANE, **lane}
    merged["default_mode"] = "real"
    merged["venue"] = "polymarket"
    if str(merged.get("venue") or "") == "kalshi" or str(merged.get("venue") or "") == "paper_crypto":
        merged["venue"] = "polymarket"
    risk = {**DEFAULT_TRADING_LANE["risk"], **(lane.get("risk") or {})}
    notifications = {**DEFAULT_TRADING_LANE["notifications"], **(lane.get("notifications") or {})}
    merged["risk"] = risk
    merged["notifications"] = notifications
    return merged


def merge_trading_lane_patch(
    operator_settings: dict[str, Any] | None,
    patch: dict[str, Any],
) -> dict[str, Any]:
    """Deep-merge trading lane config into tenant operator_settings."""

    root = dict(operator_settings or {})
    current = _trading_lane_bucket(root)
    sanitized = {k: v for k, v in patch.items() if k not in {"default_mode", "venue"} or k == "venue" and v == "polymarket"}
    for key, value in sanitized.items():
        if key == "risk" and isinstance(value, dict):
            current["risk"] = {**current.get("risk", {}), **value}
        elif key == "notifications" and isinstance(value, dict):
            current["notifications"] = {**current.get("notifications", {}), **value}
        elif key == "venue":
            current["venue"] = "polymarket"
            current["default_mode"] = "real"
        elif key == "default_mode":
            current["default_mode"] = "real"
        else:
            current[key] = value
    current["default_mode"] = "real"
    current["venue"] = "polymarket"
    root[TRADING_LANE_KEY] = current
    return root


def _project_settings_from_lane(lane: dict[str, Any]) -> dict[str, Any]:
    """Map cockpit lane config to external project settings JSON."""

    venue = "polymarket"
    risk = lane.get("risk") if isinstance(lane.get("risk"), dict) else {}
    return {
        "trading_mode": "real",
        "venue": venue,
        "connector_slug": resolve_connector_slug({"venue": venue}, venue=venue) or "",
        "max_order_usd": float(risk.get("max_order_usd") or 100.0),
        "max_daily_loss_usd": float(risk.get("max_daily_loss_usd") or 250.0),
        "max_risk_pct_per_trade": float(risk.get("max_risk_pct_per_trade") or 2.0),
        "confidence_threshold": float(risk.get("confidence_threshold") or 0.75),
        "watchlist": list(lane.get("watchlist") or []),
        "execution_flow": str(lane.get("execution_flow") or "manual_approve"),
        "trusted_auto_min_simulates": int(lane.get("trusted_auto_min_simulates") or 5),
        "behavior_principles": str(lane.get("behavior_principles") or "")[:8000],
    }


async def ensure_primary_trading_project(
    session: AsyncSession,
    *,
    owner_id: uuid.UUID,
    tenant: Tenant | None,
    lane: dict[str, Any],
) -> ExternalProject:
    """Return or create the tenant's primary trading external project."""

    bucket = _trading_lane_bucket(tenant.operator_settings if tenant is not None else None)
    primary_raw = bucket.get("primary_project_id")
    if primary_raw:
        try:
            project_id = uuid.UUID(str(primary_raw))
            row = await session.get(ExternalProject, project_id)
            if row is not None and row.owner_dashboard_user_id == owner_id:
                return row
        except (TypeError, ValueError):
            pass

    projects = await list_projects_for_owner(session, owner_id=owner_id)
    trading_rows = [p for p in projects if p.project_kind == "trading"]
    if trading_rows:
        return trading_rows[0]

    from app.domain.external.registry import create_external_project_row

    slug = f"hive-trader-{str(owner_id)[:8]}"
    settings_blob = _project_settings_from_lane(lane)
    row = await create_external_project_row(
        session,
        owner_id=owner_id,
        slug=slug,
        display_name="Polymarket Trader",
        project_kind="trading",
        settings_blob=settings_blob,
        webhook_url=None,
        webhook_plain_secret=None,
    )
    if tenant is not None:
        tenant.operator_settings = merge_trading_lane_patch(
            tenant.operator_settings,
            {"primary_project_id": str(row.id)},
        )
    return row


async def sync_project_from_lane(
    session: AsyncSession,
    *,
    project: ExternalProject,
    lane: dict[str, Any],
) -> None:
    """Push lane config into external project settings (in-memory; caller commits)."""

    project.settings = _project_settings_from_lane(lane)


async def _build_funding_snapshot(
    session: AsyncSession,
    *,
    lane: dict[str, Any],
    dashboard_user_id: uuid.UUID,
) -> dict[str, Any]:
    venue = "polymarket"
    pm_status = await build_prediction_markets_status_snapshot(session, dashboard_user_id=dashboard_user_id)
    connectors = pm_status.get("connectors_active") or {}
    connector_key = "polymarket_clob"
    ready = bool(connectors.get(connector_key))
    live = bool(pm_status.get("live_trading_enabled"))

    status_label = "needs_credentials"
    message = f"Install and vault {connector_key} connector, then fund on polymarket.com."
    if ready and not live:
        status_label = "needs_live_flag"
        message = "Connector ready — set PREDICTION_MARKETS_LIVE_TRADING_ENABLED=true after review."
    elif ready and live:
        status_label = "ready"
        message = "Fund USDC on Polymarket — Queenswarm proxies signed orders only."

    return {
        "mode": "real",
        "venue": venue,
        "deposit_allowed": False,
        "external_url": FUNDING_LINKS.get(venue),
        "connector_slug": resolve_connector_slug({"venue": venue}, venue=venue),
        "connector_ready": ready,
        "live_trading_enabled": live,
        "status": status_label,
        "message": message,
    }


class TradingCockpitConfigPatch(BaseModel):
    """Partial update for tenant trading lane."""

    model_config = ConfigDict(extra="ignore")

    behavior_principles: str | None = Field(default=None, max_length=8000)
    execution_flow: ExecutionFlow | None = None
    trusted_auto_min_simulates: int | None = Field(default=None, ge=1, le=100)
    watchlist: list[str] | None = None
    risk: dict[str, float] | None = None
    notifications: dict[str, bool] | None = None


class TradingCockpitSnapshotOut(BaseModel):
    """Single lazy-load snapshot for Trading Cockpit panel."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    config: dict[str, Any]
    venues: list[dict[str, str]]
    funding: dict[str, Any]
    project: dict[str, Any] | None
    performance: dict[str, Any]
    recent_runs: list[dict[str, Any]]
    prediction_markets: dict[str, Any]
    flags: dict[str, bool]
    links: dict[str, str]
    broker_guardrails: dict[str, Any] | None = None
    broker_readonly: dict[str, Any] | None = None
    broker_order_queue: dict[str, Any] | None = None
    pretrade_recall: dict[str, Any] | None = None


async def compose_trading_cockpit_snapshot(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
) -> TradingCockpitSnapshotOut:
    """Build Polymarket-only trading cockpit snapshot."""

    lane = _trading_lane_bucket(tenant.operator_settings if tenant is not None else None)
    project = await ensure_primary_trading_project(
        session,
        owner_id=dashboard_user_id,
        tenant=tenant,
        lane=lane,
    )
    await sync_project_from_lane(session, project=project, lane=lane)

    funding = await _build_funding_snapshot(
        session,
        lane=lane,
        dashboard_user_id=dashboard_user_id,
    )

    metrics = await aggregate_metrics(session, project_id=project.id)
    run_series = await recent_run_series(session, project_id=project.id, limit=20)

    exec_runs = await session.execute(
        select(ExternalProjectRunAudit)
        .where(ExternalProjectRunAudit.project_id == project.id)
        .order_by(desc(ExternalProjectRunAudit.created_at))
        .limit(12),
    )
    recent_runs = [
        {
            "id": str(row.id),
            "action": row.action_slug,
            "ok": row.ok,
            "latency_ms": row.latency_ms,
            "cost_usd": float(row.cost_usd or 0),
            "human_approval_required": row.human_approval_required,
            "human_approved": row.human_approved,
            "created_at": row.created_at.isoformat(),
        }
        for row in exec_runs.scalars().all()
    ]

    pm_status = await build_prediction_markets_status_snapshot(session, dashboard_user_id=dashboard_user_id)
    broker_guardrails: dict[str, Any] | None = None
    is_halted = False
    halt_reason: str | None = None
    if tenant is not None and settings.broker_guardrails_enabled:
        from app.application.services.broker_guardrails_service import get_broker_guardrails

        guardrails = await get_broker_guardrails(session, tenant_id=tenant.id)
        broker_guardrails = guardrails.model_dump(mode="json")
        if guardrails.kill_switch:
            is_halted = True
            halt_reason = "Broker kill switch is ON."
    broker_readonly: dict[str, Any] | None = None
    if tenant is not None and settings.broker_readonly_session_enabled:
        from app.application.services.broker_readonly_session_service import compose_broker_readonly_kpi

        readonly_kpi = await compose_broker_readonly_kpi(
            session,
            tenant_id=tenant.id,
            dashboard_user_id=dashboard_user_id,
        )
        broker_readonly = readonly_kpi.model_dump(mode="json")
        if readonly_kpi.readonly_required and not is_halted:
            is_halted = True
            halt_reason = readonly_kpi.operator_hint
    broker_order_queue: dict[str, Any] | None = None
    pretrade_recall: dict[str, Any] | None = None
    if tenant is not None and settings.broker_order_queue_enabled:
        from app.application.services.broker_order_queue_service import build_broker_order_queue_snapshot

        queue_snapshot = await build_broker_order_queue_snapshot(session, tenant_id=tenant.id)
        broker_order_queue = queue_snapshot.model_dump(mode="json")
    if tenant is not None and settings.journal_studio_pretrade_recall_enabled and settings.journal_studio_enabled:
        from app.application.services.journal_studio_pretrade_recall_service import compose_pretrade_recall

        recall = await compose_pretrade_recall(
            session,
            tenant_id=tenant.id,
            dashboard_user_id=dashboard_user_id,
        )
        pretrade_recall = recall.model_dump(mode="json")
    performance: dict[str, Any] = {
        "mode": "real",
        "venue": "polymarket",
        "external_metrics": metrics,
        "is_halted": is_halted,
        "halt_reason": halt_reason,
    }

    return TradingCockpitSnapshotOut(
        enabled=bool(settings.trading_cockpit_enabled),
        generated_at=datetime.now(tz=UTC),
        config=lane,
        venues=list(VENUE_CATALOG),
        funding=funding,
        project={
            "id": str(project.id),
            "slug": project.slug,
            "display_name": project.display_name,
            "is_active": project.is_active,
            "settings": dict(project.settings or {}),
        },
        performance=performance,
        recent_runs=recent_runs or run_series[:12],
        prediction_markets=pm_status,
        flags={
            "prediction_markets_enabled": bool(settings.prediction_markets_enabled),
            "live_trading_enabled": bool(settings.prediction_markets_live_trading_enabled),
        },
        links={
            "external_projects": "/external-projects",
            "connectors": "/integrations?tab=hub",
            "manual": "docs/OPERATOR_PREDICTION_MARKETS_SETUP.md",
            "prediction_setup": "docs/OPERATOR_PREDICTION_MARKETS_SETUP.md",
            "evaluator_swarm": "/swarms/new?template=polymarket-prediction-evaluator",
            "live_swarm": "/swarms/new?template=polymarket-trading",
            "broker_guardrails": "/apps-tools/trading-automation?section=guardrails#broker-guardrails",
            "broker_readonly": "/apps-tools/trading-automation?section=connect#broker-readonly-session",
            "broker_order_queue": "/apps-tools/trading-automation?section=orders#broker-order-queue",
        },
        broker_guardrails=broker_guardrails,
        broker_readonly=broker_readonly,
        broker_order_queue=broker_order_queue,
        pretrade_recall=pretrade_recall,
    )


async def compose_trading_cockpit_action_signals(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
) -> dict[str, Any]:
    """Minimal trading signals for operator loop — Polymarket live prep only."""

    if not settings.trading_cockpit_enabled:
        return {"config": {}, "performance": {}}

    lane = _trading_lane_bucket(tenant.operator_settings if tenant is not None else None)
    pm_status = await build_prediction_markets_status_snapshot(session, dashboard_user_id=dashboard_user_id)
    readiness = pm_status.get("polymarket_readiness") or {}
    performance: dict[str, Any] = {
        "is_halted": False,
        "halt_reason": None,
        "live_ready": bool(readiness.get("ready")),
        "live_trading_enabled": bool(pm_status.get("live_trading_enabled")),
    }
    return {"config": lane, "performance": performance}


async def apply_trading_cockpit_config(
    session: AsyncSession,
    *,
    tenant: Tenant,
    owner_id: uuid.UUID,
    patch: TradingCockpitConfigPatch,
) -> dict[str, Any]:
    """Persist lane config and sync primary trading project."""

    payload = patch.model_dump(exclude_none=True)
    tenant.operator_settings = merge_trading_lane_patch(tenant.operator_settings, payload)
    lane = _trading_lane_bucket(tenant.operator_settings)
    project = await ensure_primary_trading_project(
        session,
        owner_id=owner_id,
        tenant=tenant,
        lane=lane,
    )
    await sync_project_from_lane(session, project=project, lane=lane)
    return lane


__all__ = [
    "TradingCockpitConfigPatch",
    "TradingCockpitSnapshotOut",
    "apply_trading_cockpit_config",
    "compose_trading_cockpit_snapshot",
    "compose_trading_cockpit_action_signals",
    "merge_trading_lane_patch",
]
