"""Phase 2.5 external integration unit coverage (managers + registry helpers)."""

from __future__ import annotations

import pytest

from app.domain.external.managers.food_ordering_manager import FoodOrderingManager
from app.domain.external.managers.generic_project_manager import GenericProjectManager
from app.domain.external.managers.trading_manager import TradingManager
from app.domain.external.registry import estimate_run_cost_usd, normalize_external_slug, permission_allowed


@pytest.mark.asyncio
async def test_trading_quote_returns_verified_payload_when_symbol_present() -> None:
    """Quotes succeed under conservative risk envelopes."""

    mgr = TradingManager()
    out = await mgr.handle(
        action="quote",
        payload={"symbol": "btc", "quantity": 0.25, "assumed_price_usd": 42_000},
        project_settings={"trading_mode": "real", "max_order_usd": 50_000},
    )
    assert out["status"] == "ok"
    assert out["verified"] is True


@pytest.mark.asyncio
async def test_trading_quote_blocks_paper_mode_after_removal() -> None:
    """Paper lane removed — callers must use real mode + Polymarket CLOB."""

    mgr = TradingManager()
    out = await mgr.handle(
        action="quote",
        payload={"symbol": "btc", "quantity": 0.25, "assumed_price_usd": 42_000},
        project_settings={"trading_mode": "paper", "max_order_usd": 50_000},
    )
    assert out["status"] == "blocked"
    assert out["reason"] == "paper_trading_removed"


@pytest.mark.asyncio
async def test_trading_live_execution_blocks_without_human_ticket() -> None:
    """Human-in-the-loop gate closes unless confirmations arrive."""

    mgr = TradingManager()
    out = await mgr.handle(
        action="execute_trade",
        payload={"symbol": "eth", "quantity": 1, "assumed_price_usd": 2500},
        project_settings={"trading_mode": "real"},
    )
    assert out["status"] == "blocked"
    assert out["reason"] == "human_approval_required"


@pytest.mark.asyncio
async def test_trading_live_execution_queues_when_ticket_present() -> None:
    """Confirmed tickets transition into queued broker stub state."""

    mgr = TradingManager()
    out = await mgr.handle(
        action="execute_trade",
        payload={
            "symbol": "sol",
            "quantity": 2,
            "assumed_price_usd": 140,
            "human_approval_confirmed": True,
            "human_approval_ticket": "TICKET-phase25-demo",
        },
        project_settings={"trading_mode": "real"},
    )
    assert out["status"] == "queued_for_execution"


@pytest.mark.asyncio
async def test_food_preview_requires_vendor_and_items() -> None:
    """Cart preview validates vendor + SKUs."""

    mgr = FoodOrderingManager()
    out = await mgr.handle(
        action="preview_cart",
        payload={"vendor_id": "hive-kitchen", "items": [{"sku": "honey-latte", "qty": 2}]},
        project_settings={},
    )
    assert out["status"] == "ok"


@pytest.mark.asyncio
async def test_food_submit_requires_customer_ref() -> None:
    """Submit lane refuses anonymous diners."""

    mgr = FoodOrderingManager()
    with pytest.raises(ValueError):
        await mgr.handle(
            action="submit_order",
            payload={"vendor_id": "hive-kitchen", "items": [{"sku": "combo-1", "qty": 1}]},
            project_settings={},
        )


@pytest.mark.asyncio
async def test_generic_simulate_marks_verified() -> None:
    """Generic lane emits deterministic simulation markers."""

    mgr = GenericProjectManager()
    out = await mgr.handle(action="simulate", payload={"hello": "hive"}, project_settings={})
    assert out["verified"] is True


def test_normalize_external_slug_rejects_reserved_results_token() -> None:
    """Reserve `/external/results` lane collisions."""

    with pytest.raises(ValueError):
        normalize_external_slug("results")


def test_permission_star_grants_all() -> None:
    """Wildcard scopes bypass fine-grained checks."""

    assert permission_allowed(["*"], "run") is True


def test_estimate_run_cost_usd_scales_with_execute_suffix() -> None:
    """Heuristic pricing elevates trading executions."""

    low = estimate_run_cost_usd("quote", "trading")
    high = estimate_run_cost_usd("execute_trade", "trading")
    assert high > low


@pytest.mark.asyncio
async def test_trading_quote_requires_symbol() -> None:
    mgr = TradingManager()
    with pytest.raises(ValueError, match="symbol"):
        await mgr.handle(
            action="quote",
            payload={"quantity": 1},
            project_settings={"trading_mode": "real"},
        )


@pytest.mark.asyncio
async def test_trading_rejects_unknown_mode() -> None:
    mgr = TradingManager()
    with pytest.raises(ValueError, match="trading_mode"):
        await mgr.handle(
            action="quote",
            payload={"symbol": "btc", "quantity": 1, "assumed_price_usd": 1},
            project_settings={"trading_mode": "sandbox"},
        )


@pytest.mark.asyncio
async def test_trading_unsupported_action_raises() -> None:
    mgr = TradingManager()
    with pytest.raises(ValueError, match="Unsupported"):
        await mgr.handle(
            action="liquidate_all",
            payload={"symbol": "btc", "quantity": 1},
            project_settings={"trading_mode": "real"},
        )


@pytest.mark.asyncio
async def test_trading_risk_limit_blocks_large_notional() -> None:
    """Risk rails honour JSON-configured USD ceilings."""

    mgr = TradingManager()
    out = await mgr.handle(
        action="quote",
        payload={"symbol": "mega", "quantity": 1, "notional_usd": 999_999},
        project_settings={"max_order_usd": 10},
    )
    assert out["status"] == "blocked"
    assert out["reason"] == "risk_limit"
