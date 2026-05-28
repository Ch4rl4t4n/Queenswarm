"""Trading Cockpit — unified paper + real-money agent control for Execution Studio."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.paper_trading_service import (
    build_portfolio_snapshot,
    deposit_paper_cash,
    reset_paper_account,
    run_paper_trading_tick_for_project,
)
from app.application.services.prediction_market_trading import (
    PREDICTION_VENUES,
    build_prediction_markets_status_snapshot,
    resolve_connector_slug,
)
from app.core.config import settings
from app.domain.external.registry import aggregate_metrics, list_projects_for_owner, recent_run_series
from app.infrastructure.persistence.models.external_project import ExternalProject, ExternalProjectRunAudit
from app.infrastructure.persistence.models.paper_trading import PaperTradingFill
from app.infrastructure.persistence.models.tenant import Tenant

TradingMode = Literal["paper", "real"]
TradingVenueId = Literal["paper_crypto", "polymarket"]
ExecutionFlow = Literal["simulate_first", "manual_approve", "trusted_auto"]

TRADING_LANE_KEY = "trading_lane"

VENUE_CATALOG: list[dict[str, str]] = [
    {
        "id": "paper_crypto",
        "label": "Paper · crypto simulation",
        "mode": "paper",
        "description": "Simulated BTC/ETH/SOL fills — deposit virtual USD in-app.",
    },
    {
        "id": "polymarket",
        "label": "Polymarket · prediction markets",
        "mode": "real",
        "description": "Real USDC on Polygon — fund wallet on polymarket.com.",
    },
]

DEFAULT_TRADING_LANE: dict[str, Any] = {
    "default_mode": "paper",
    "venue": "paper_crypto",
    "behavior_principles": (
        "Trade only verified signals. Max 2% equity per trade. "
        "Stop after daily loss limit. Never chase momentum without confidence ≥ threshold."
    ),
    "execution_flow": "simulate_first",
    "trusted_auto_min_simulates": 5,
    "auto_tick": True,
    "watchlist": ["BTC", "ETH"],
    "risk": {
        "max_order_usd": 2_500.0,
        "max_daily_loss_usd": 500.0,
        "max_risk_pct_per_trade": 2.0,
        "confidence_threshold": 0.8,
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
    if str(merged.get("venue") or "") == "kalshi":
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
    for key, value in patch.items():
        if key == "risk" and isinstance(value, dict):
            current["risk"] = {**current.get("risk", {}), **value}
        elif key == "notifications" and isinstance(value, dict):
            current["notifications"] = {**current.get("notifications", {}), **value}
        else:
            current[key] = value
    root[TRADING_LANE_KEY] = current
    return root


def _project_settings_from_lane(lane: dict[str, Any]) -> dict[str, Any]:
    """Map cockpit lane config to external project settings JSON."""

    venue = str(lane.get("venue") or "paper_crypto")
    mode: TradingMode = "paper" if venue == "paper_crypto" else "real"
    risk = lane.get("risk") if isinstance(lane.get("risk"), dict) else {}
    return {
        "trading_mode": mode,
        "venue": venue if venue in PREDICTION_VENUES else "",
        "connector_slug": resolve_connector_slug({"venue": venue}, venue=venue) if venue in PREDICTION_VENUES else "",
        "max_order_usd": float(risk.get("max_order_usd") or 2_500.0),
        "max_daily_loss_usd": float(risk.get("max_daily_loss_usd") or 500.0),
        "max_risk_pct_per_trade": float(risk.get("max_risk_pct_per_trade") or 2.0),
        "confidence_threshold": float(risk.get("confidence_threshold") or settings.paper_trading_confidence_threshold),
        "watchlist": list(lane.get("watchlist") or ["BTC", "ETH"]),
        "paper_trading_auto_tick": bool(lane.get("auto_tick", True)),
        "starting_cash_usd": float(risk.get("starting_cash_usd") or settings.paper_trading_default_cash_usd),
        "execution_flow": str(lane.get("execution_flow") or "simulate_first"),
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
        display_name="Hive Trader",
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


def _compute_paper_stats(fills: list[PaperTradingFill]) -> dict[str, Any]:
    sells = [f for f in fills if f.side.lower() == "sell"]
    buys = [f for f in fills if f.side.lower() == "buy"]
    return {
        "total_fills": len(fills),
        "buy_count": len(buys),
        "sell_count": len(sells),
        "last_fill_at": fills[0].created_at.isoformat() if fills else None,
    }


async def _build_funding_snapshot(
    session: AsyncSession,
    *,
    project: ExternalProject | None,
    lane: dict[str, Any],
    dashboard_user_id: uuid.UUID,
) -> dict[str, Any]:
    venue = str(lane.get("venue") or "paper_crypto")
    mode = str(lane.get("default_mode") or "paper")

    if venue == "paper_crypto" or mode == "paper":
        cash = 0.0
        starting = float(
            (lane.get("risk") or {}).get("starting_cash_usd") or settings.paper_trading_default_cash_usd,
        )
        if project is not None:
            try:
                snap = await build_portfolio_snapshot(session, project=project)
                cash = float(snap.get("cash_usd") or 0.0)
                starting = float(snap.get("starting_cash_usd") or starting)
            except Exception:
                pass
        return {
            "mode": "paper",
            "venue": "paper_crypto",
            "cash_usd": round(cash, 2),
            "starting_cash_usd": round(starting, 2),
            "deposit_allowed": True,
            "message": "Virtual USD — deposit in-app, no real money.",
        }

    pm_status = await build_prediction_markets_status_snapshot(session, dashboard_user_id=dashboard_user_id)
    connectors = pm_status.get("connectors_active") or {}
    connector_key = "polymarket_clob"
    ready = bool(connectors.get(connector_key))
    live = bool(pm_status.get("live_trading_enabled"))

    status_label = "needs_credentials"
    message = f"Install and vault {connector_key} connector, then fund on {venue}."
    if ready and not live:
        status_label = "needs_live_flag"
        message = "Connector ready — set PREDICTION_MARKETS_LIVE_TRADING_ENABLED=true after review."
    elif ready and live:
        status_label = "ready"
        message = f"Fund USDC/USD on {venue} — Queenswarm proxies signed orders only."

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

    default_mode: TradingMode | None = None
    venue: TradingVenueId | None = None
    behavior_principles: str | None = Field(default=None, max_length=8000)
    execution_flow: ExecutionFlow | None = None
    trusted_auto_min_simulates: int | None = Field(default=None, ge=1, le=100)
    auto_tick: bool | None = None
    watchlist: list[str] | None = None
    risk: dict[str, float] | None = None
    notifications: dict[str, bool] | None = None


class TradingCockpitDepositBody(BaseModel):
    """Paper capital deposit."""

    model_config = ConfigDict(extra="forbid")

    amount_usd: float = Field(..., gt=0, le=1_000_000)


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
    positions: list[dict[str, Any]]
    recent_fills: list[dict[str, Any]]
    recent_runs: list[dict[str, Any]]
    prediction_markets: dict[str, Any]
    flags: dict[str, bool]
    links: dict[str, str]


async def compose_trading_cockpit_snapshot(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
) -> TradingCockpitSnapshotOut:
    """Build unified trading cockpit snapshot."""

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
        project=project,
        lane=lane,
        dashboard_user_id=dashboard_user_id,
    )

    portfolio: dict[str, Any] = {}
    positions: list[dict[str, Any]] = []
    recent_fills: list[dict[str, Any]] = []
    performance: dict[str, Any] = {
        "mode": lane.get("default_mode", "paper"),
        "venue": lane.get("venue", "paper_crypto"),
        "equity_usd": 0.0,
        "total_pnl_usd": 0.0,
        "total_pnl_pct": 0.0,
        "realized_pnl_usd": 0.0,
        "daily_realized_pnl_usd": 0.0,
        "is_halted": False,
        "halt_reason": None,
    }

    if str(lane.get("venue") or "paper_crypto") == "paper_crypto":
        portfolio = await build_portfolio_snapshot(session, project=project)
        positions = list(portfolio.get("positions") or [])
        recent_fills = list(portfolio.get("recent_fills") or [])
        performance.update(
            {
                "equity_usd": portfolio.get("equity_usd", 0.0),
                "total_pnl_usd": portfolio.get("total_pnl_usd", 0.0),
                "total_pnl_pct": portfolio.get("total_pnl_pct", 0.0),
                "realized_pnl_usd": portfolio.get("realized_pnl_usd", 0.0),
                "daily_realized_pnl_usd": portfolio.get("daily_realized_pnl_usd", 0.0),
                "is_halted": portfolio.get("is_halted", False),
                "halt_reason": portfolio.get("halt_reason"),
            },
        )

    exec_result = await session.execute(
        select(PaperTradingFill)
        .where(PaperTradingFill.project_id == project.id)
        .order_by(desc(PaperTradingFill.created_at))
        .limit(50),
    )
    fill_rows = list(exec_result.scalars().all())
    stats = _compute_paper_stats(fill_rows)
    performance["stats"] = stats

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
        performance={**performance, "external_metrics": metrics},
        positions=positions,
        recent_fills=recent_fills,
        recent_runs=recent_runs or run_series[:12],
        prediction_markets=pm_status,
        flags={
            "paper_trading_enabled": bool(settings.paper_trading_enabled),
            "prediction_markets_enabled": bool(settings.prediction_markets_enabled),
            "live_trading_enabled": bool(settings.prediction_markets_live_trading_enabled),
        },
        links={
            "external_projects": "/external-projects",
            "connectors": "/integrations?tab=hub",
            "manual": "docs/OPERATOR_TRADING_COCKPIT_MANUAL.md",
            "prediction_setup": "docs/OPERATOR_PREDICTION_MARKETS_SETUP.md",
        },
    )


async def compose_trading_cockpit_action_signals(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
) -> dict[str, Any]:
    """Minimal trading signals for operator loop actions — skips metrics and run history."""

    if not settings.trading_cockpit_enabled:
        return {"config": {}, "performance": {}}

    lane = _trading_lane_bucket(tenant.operator_settings if tenant is not None else None)
    performance: dict[str, Any] = {
        "is_halted": False,
        "halt_reason": None,
    }

    if str(lane.get("venue") or "paper_crypto") == "paper_crypto" and settings.paper_trading_enabled:
        project = await ensure_primary_trading_project(
            session,
            owner_id=dashboard_user_id,
            tenant=tenant,
            lane=lane,
        )
        portfolio = await build_portfolio_snapshot(session, project=project)
        performance = {
            "is_halted": portfolio.get("is_halted", False),
            "halt_reason": portfolio.get("halt_reason"),
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
    venue = payload.get("venue")
    if venue == "paper_crypto":
        payload.setdefault("default_mode", "paper")
    elif venue == "polymarket":
        payload.setdefault("default_mode", "real")
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


async def run_cockpit_paper_deposit(
    session: AsyncSession,
    *,
    owner_id: uuid.UUID,
    tenant: Tenant | None,
    amount_usd: float,
) -> dict[str, Any]:
    """Deposit virtual USD into primary paper project."""

    lane = _trading_lane_bucket(tenant.operator_settings if tenant is not None else None)
    project = await ensure_primary_trading_project(
        session,
        owner_id=owner_id,
        tenant=tenant,
        lane=lane,
    )
    return await deposit_paper_cash(session, project=project, amount_usd=amount_usd)


async def run_cockpit_paper_tick(
    session: AsyncSession,
    *,
    owner_id: uuid.UUID,
    tenant: Tenant | None,
) -> dict[str, Any]:
    """Manual paper trading tick for primary project."""

    lane = _trading_lane_bucket(tenant.operator_settings if tenant is not None else None)
    project = await ensure_primary_trading_project(
        session,
        owner_id=owner_id,
        tenant=tenant,
        lane=lane,
    )
    return await run_paper_trading_tick_for_project(session, project=project)


async def run_cockpit_paper_reset(
    session: AsyncSession,
    *,
    owner_id: uuid.UUID,
    tenant: Tenant | None,
) -> dict[str, Any]:
    """Reset paper cash balance for primary project."""

    lane = _trading_lane_bucket(tenant.operator_settings if tenant is not None else None)
    project = await ensure_primary_trading_project(
        session,
        owner_id=owner_id,
        tenant=tenant,
        lane=lane,
    )
    return await reset_paper_account(session, project=project)


__all__ = [
    "TradingCockpitConfigPatch",
    "TradingCockpitDepositBody",
    "TradingCockpitSnapshotOut",
    "apply_trading_cockpit_config",
    "compose_trading_cockpit_snapshot",
    "compose_trading_cockpit_action_signals",
    "merge_trading_lane_patch",
    "run_cockpit_paper_deposit",
    "run_cockpit_paper_reset",
    "run_cockpit_paper_tick",
]
