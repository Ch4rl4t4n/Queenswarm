"""Live prediction-market order execution — Polymarket CLOB + Kalshi RSA."""

from __future__ import annotations

import json
import uuid
from typing import Any, Literal

import structlog
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.agentic_gates import evaluate_real_money_gate
from app.core.config import settings
from app.core.redis_client import sliding_window_reserve
from app.infrastructure.persistence.models.external_project import ExternalProject

logger = structlog.get_logger(__name__)

PredictionVenue = Literal["polymarket", "kalshi"]
PREDICTION_VENUES: frozenset[str] = frozenset({"polymarket", "kalshi"})

_RATE_PREFIX = "queenswarm:prediction_markets:live"


def _payload_operator_confirmed(payload: dict[str, Any]) -> bool:
    """Return True when payload explicitly confirms operator approval for live money."""

    raw = payload.get("operator_confirmed")
    if raw is True:
        return True
    if isinstance(raw, str):
        return raw.strip().lower() in {"1", "true", "yes", "on"}
    return False


def resolve_venue(project_settings: dict[str, Any]) -> str:
    """Return normalized venue slug from external project settings."""

    return str(project_settings.get("venue") or "").strip().lower()


def resolve_connector_slug(project_settings: dict[str, Any], *, venue: str) -> str:
    """Resolve connector slug with sensible defaults per venue."""

    explicit = str(project_settings.get("connector_slug") or "").strip().lower()
    if explicit:
        return explicit
    if venue == "polymarket":
        return "polymarket_clob"
    if venue == "kalshi":
        return "kalshi_trading"
    return ""


def build_kalshi_order_arguments(payload: dict[str, Any]) -> dict[str, Any]:
    """Map external-project payload to Kalshi order_create JSON."""

    ticker = str(payload.get("market_ticker") or payload.get("symbol") or "").strip()
    if not ticker:
        msg = "payload.market_ticker or payload.symbol required for Kalshi."
        raise ValueError(msg)

    side_raw = str(payload.get("side") or "yes").strip().lower()
    side = "yes" if side_raw in {"yes", "buy", "long"} else "no"

    count = payload.get("count")
    if count is None:
        count = payload.get("quantity")
    try:
        count_int = max(1, int(float(count)))  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        msg = "payload.count or payload.quantity must be a positive integer."
        raise ValueError(msg) from exc

    price = payload.get("yes_price") or payload.get("price_cents") or payload.get("limit_price_cents")
    try:
        yes_price = int(float(price))  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        msg = "payload.yes_price or price_cents required (1–99 cents)."
        raise ValueError(msg) from exc

    if not 1 <= yes_price <= 99:
        msg = "Kalshi yes_price must be between 1 and 99 cents."
        raise ValueError(msg)

    body: dict[str, Any] = {
        "ticker": ticker,
        "action": "buy",
        "side": side,
        "count": count_int,
        "type": "limit",
        "yes_price": yes_price,
    }
    client_order_id = str(payload.get("client_order_id") or "").strip()
    if client_order_id:
        body["client_order_id"] = client_order_id[:64]
    return body


def build_polymarket_order_arguments(payload: dict[str, Any]) -> dict[str, Any]:
    """Map bot-provided signed order blob to CLOB order_post body."""

    signed = payload.get("signed_order")
    if isinstance(signed, dict) and signed:
        return dict(signed)

    order = payload.get("order")
    if isinstance(order, dict) and order:
        return dict(order)

    msg = (
        "Polymarket live orders require payload.signed_order (EIP-712 signed order from your bot). "
        "Queenswarm proxies REST; order signing stays in the trading bot."
    )
    raise ValueError(msg)


async def check_prediction_market_rate_limit(*, owner_user_id: uuid.UUID, venue: str) -> tuple[bool, str]:
    """Sliding-window cap on live prediction-market orders per operator."""

    if not settings.prediction_markets_live_trading_enabled:
        return True, ""

    per_venue_max = int(settings.prediction_markets_live_daily_max_per_venue)
    global_max = int(settings.prediction_markets_live_daily_max_global)
    window_sec = float(settings.prediction_markets_rate_limit_window_sec)

    venue_key = f"{_RATE_PREFIX}:{owner_user_id}:{venue}"
    global_key = f"{_RATE_PREFIX}:{owner_user_id}:all"

    try:
        if not await sliding_window_reserve(venue_key, limit=max(per_venue_max, 1), window_sec=window_sec):
            return False, f"Live order rate limit for {venue} ({per_venue_max}/window)."
        if not await sliding_window_reserve(global_key, limit=max(global_max, 1), window_sec=window_sec):
            return False, f"Global live prediction-market rate limit ({global_max}/window)."
    except RedisError as exc:
        logger.error(
            "prediction_markets.rate_limit_redis_error",
            agent_id="prediction_markets",
            error=str(exc)[:200],
        )
        if settings.prediction_markets_rate_limit_fail_closed:
            return False, "Rate limiter unavailable — live orders blocked (fail-closed)."
    return True, ""


async def execute_live_prediction_trade(
    session: AsyncSession,
    *,
    project: ExternalProject,
    payload: dict[str, Any],
    project_settings: dict[str, Any],
) -> dict[str, Any]:
    """Place a real-money order on Polymarket or Kalshi via installed connectors."""

    venue = resolve_venue(project_settings)
    if venue not in PREDICTION_VENUES:
        return {
            "status": "blocked",
            "reason": "unknown_venue",
            "detail": f"Unsupported venue {venue!r} — use polymarket or kalshi.",
            "venue": venue,
        }

    if not settings.prediction_markets_enabled:
        return {
            "status": "blocked",
            "reason": "prediction_markets_disabled",
            "detail": "PREDICTION_MARKETS_ENABLED=false.",
        }

    if not settings.prediction_markets_live_trading_enabled:
        return {
            "status": "blocked",
            "reason": "live_trading_disabled",
            "detail": "Set PREDICTION_MARKETS_LIVE_TRADING_ENABLED=true after credentials + review.",
        }

    connector_slug = resolve_connector_slug(project_settings, venue=venue)
    if not connector_slug:
        return {
            "status": "blocked",
            "reason": "missing_connector",
            "detail": "settings.connector_slug required.",
        }

    allowed, rate_msg = await check_prediction_market_rate_limit(
        owner_user_id=project.owner_dashboard_user_id,
        venue=venue,
    )
    if not allowed:
        return {"status": "blocked", "reason": "rate_limit", "detail": rate_msg, "venue": venue}

    max_usd = float(project_settings.get("max_order_usd") or settings.prediction_markets_max_order_usd)
    notional = float(payload.get("notional_usd") or 0.0)
    if notional <= 0 and venue == "kalshi":
        try:
            count = int(float(payload.get("count") or payload.get("quantity") or 0))
            cents = int(float(payload.get("yes_price") or payload.get("price_cents") or 0))
            notional = (count * cents) / 100.0
        except (TypeError, ValueError):
            notional = 0.0
    if notional > max_usd > 0:
        return {
            "status": "blocked",
            "reason": "risk_limit",
            "detail": f"Notional ${notional:.2f} exceeds max_order_usd={max_usd}.",
            "venue": venue,
        }

    operator_confirmed = _payload_operator_confirmed(payload)
    money_gate = evaluate_real_money_gate(
        operator_confirmed=operator_confirmed,
        action=f"prediction_markets:{venue}:live_order",
        paper_mode=False,
        position_size_ok=notional <= max_usd if max_usd > 0 else True,
    )
    if not money_gate.allowed:
        return {
            "status": "blocked",
            "reason": money_gate.error_code or "real_money_gate",
            "detail": money_gate.message or "Real-money gate blocked live order.",
            "venue": venue,
            "gate": money_gate.gate.value,
        }

    try:
        if venue == "kalshi":
            tool_name = "order_create"
            arguments = build_kalshi_order_arguments(payload)
        else:
            tool_name = "order_post"
            arguments = build_polymarket_order_arguments(payload)
    except ValueError as exc:
        return {"status": "blocked", "reason": "invalid_payload", "detail": str(exc), "venue": venue}

    from app.infrastructure.connectors.dynamic.service import invoke_dynamic_tool

    raw = await invoke_dynamic_tool(
        session,
        connector_slug=connector_slug,
        tool_name=tool_name,
        arguments=arguments,
        manager_slug="execution_operations",
        agent_task_id=str(project.id),
    )

    if raw.startswith("dynamic_invoke_http_") or raw.startswith("dynamic_invoke_error"):
        logger.warning(
            "prediction_markets.live_failed",
            agent_id="prediction_markets",
            swarm_id=connector_slug,
            task_id=str(project.id),
            venue=venue,
            snippet=raw[:300],
        )
        return {
            "status": "error",
            "reason": "upstream_rejected",
            "detail": raw[:800],
            "venue": venue,
            "connector_slug": connector_slug,
            "tool_name": tool_name,
            "verified": False,
        }

    parsed: Any
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        parsed = {"raw": raw[:2000]}

    logger.info(
        "prediction_markets.live_executed",
        agent_id="prediction_markets",
        swarm_id=connector_slug,
        task_id=str(project.id),
        venue=venue,
        tool_name=tool_name,
    )
    return {
        "status": "executed",
        "mode": "real",
        "venue": venue,
        "connector_slug": connector_slug,
        "tool_name": tool_name,
        "upstream": parsed if isinstance(parsed, dict) else {"raw": str(parsed)[:2000]},
        "verified": True,
    }


async def build_prediction_markets_status_snapshot(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
) -> dict[str, Any]:
    """Operator-facing readiness for real-money prediction-market trading."""

    from app.infrastructure.connectors.dynamic.service import DynamicConnectorService

    svc = DynamicConnectorService()
    slugs = {
        "polymarket_gamma": "polymarket_gamma",
        "polymarket_clob": "polymarket_clob",
    }
    connectors: dict[str, bool] = {}
    for key, slug in slugs.items():
        row = await svc.fetch_by_slug(session, slug=slug)
        connectors[key] = bool(row and row.is_active)

    live = bool(settings.prediction_markets_live_trading_enabled)
    readiness = build_polymarket_readiness(connectors, live_enabled=live)

    return {
        "enabled": bool(settings.prediction_markets_enabled),
        "live_trading_enabled": live,
        "connectors_active": connectors,
        "polymarket_readiness": readiness,
        "max_order_usd_default": float(settings.prediction_markets_max_order_usd),
        "rate_limits": {
            "per_venue_daily": int(settings.prediction_markets_live_daily_max_per_venue),
            "global_daily": int(settings.prediction_markets_live_daily_max_global),
        },
        "required_api_key_scope": "trading:live",
        "docs": "docs/OPERATOR_PREDICTION_MARKETS_SETUP.md",
    }


def build_polymarket_readiness(
    connectors: dict[str, bool],
    *,
    live_enabled: bool,
) -> dict[str, Any]:
    """Operator checklist for Polymarket real-money lane."""

    gamma = bool(connectors.get("polymarket_gamma"))
    clob = bool(connectors.get("polymarket_clob"))
    steps: list[dict[str, Any]] = [
        {
            "id": "gamma",
            "label": "Gamma connector (market research)",
            "done": gamma,
            "detail": "Install polymarket_gamma — browse markets before trading.",
        },
        {
            "id": "clob",
            "label": "CLOB connector vaulted",
            "done": clob,
            "detail": "Seal L2 apiKey, secret, passphrase, wallet in Connector Vault.",
        },
        {
            "id": "live_flag",
            "label": "Live trading flag enabled",
            "done": live_enabled,
            "detail": "PREDICTION_MARKETS_LIVE_TRADING_ENABLED=true after review.",
        },
        {
            "id": "fund",
            "label": "Fund USDC on polymarket.com",
            "done": clob and live_enabled,
            "detail": "Deposit on venue — Queenswarm proxies signed orders only.",
        },
    ]
    done_count = sum(1 for step in steps if step["done"])
    progress = int(round(100 * done_count / max(len(steps), 1)))
    return {
        "steps": steps,
        "progress_pct": progress,
        "ready": clob and live_enabled,
    }


__all__ = [
    "PREDICTION_VENUES",
    "PredictionVenue",
    "build_kalshi_order_arguments",
    "build_polymarket_order_arguments",
    "build_polymarket_readiness",
    "build_prediction_markets_status_snapshot",
    "execute_live_prediction_trade",
    "resolve_connector_slug",
    "resolve_venue",
]
