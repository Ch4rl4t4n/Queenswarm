"""Roadmap P9 tail — hook optimizer, forager v2, hybrid, transparency, marketplace beta."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.forager_intelligence_v2 import compose_forager_v2_snapshot
from app.application.services.public_trading_transparency import build_public_trading_transparency
from app.application.services.publish_hook_optimizer import build_hook_winner_stats
from app.application.services.recipe_marketplace_beta import compose_recipe_marketplace_beta_snapshot


@pytest.mark.asyncio
async def test_build_hook_winner_stats_disabled() -> None:
    session = AsyncMock()
    with patch("app.application.services.publish_hook_optimizer.settings") as mock_settings:
        mock_settings.publish_hook_optimizer_enabled = False
        rows = await build_hook_winner_stats(session, dashboard_user_id=uuid.uuid4())
    assert rows == []


@pytest.mark.asyncio
async def test_build_hook_winner_stats_aggregates_styles() -> None:
    session = AsyncMock()
    deliverable = SimpleNamespace(
        structured_json={
            "channel": "twitter",
            "hook_variants": [
                {"style": "curiosity", "hook": "What if paper trading worked?"},
                {"style": "curiosity", "hook": "Another curiosity hook"},
                {"style": "stat", "hook": "87% simulate success"},
            ],
        },
    )
    with (
        patch("app.application.services.publish_hook_optimizer.settings") as mock_settings,
        patch(
            "app.application.services.publish_hook_optimizer.list_owned_deliverables",
            new_callable=AsyncMock,
        ) as list_mock,
    ):
        mock_settings.publish_hook_optimizer_enabled = True
        list_mock.return_value = [deliverable]
        rows = await build_hook_winner_stats(session, dashboard_user_id=uuid.uuid4())

    assert len(rows) == 1
    assert rows[0].channel == "twitter"
    assert rows[0].winning_style == "curiosity"
    assert rows[0].pack_count == 3


@pytest.mark.asyncio
async def test_compose_forager_v2_snapshot_enabled() -> None:
    session = AsyncMock()
    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        operator_settings={"execution_studio": {"recent_activity": [{"x": 1}] * 5}},
    )

    with (
        patch("app.application.services.forager_intelligence_v2.settings") as mock_settings,
        patch("app.application.services.forager_intelligence_v2.run_intelligence_scan") as scan_mock,
        patch(
            "app.application.services.prediction_market_trading.build_prediction_markets_status_snapshot",
            new_callable=AsyncMock,
        ) as pm_mock,
    ):
        mock_settings.forager_intelligence_v2_enabled = True
        scan_mock.return_value = {"proposal_count": 2, "proposals": [{"kind": "mcp", "target": "x", "priority": "low", "rationale": "r"}]}
        pm_mock.return_value = {
            "connectors_active": {"polymarket_gamma": True, "polymarket_clob": False},
        }
        snap = await compose_forager_v2_snapshot(
            session,
            tenant=tenant,
            dashboard_user_id=uuid.uuid4(),
        )

    assert snap.enabled is True
    assert snap.global_proposal_count == 2
    assert any("polymarket_clob" in gap for gap in snap.connector_gaps)


@pytest.mark.asyncio
async def test_build_public_trading_transparency_sanitized() -> None:
    """Paper transparency lane removed — public endpoint returns disabled stub."""

    session = AsyncMock()
    snap = await build_public_trading_transparency(session)

    assert snap.enabled is False
    assert snap.total_pnl_usd == 0.0
    assert snap.recent_fills == []
    assert "Paper trading removed" in snap.disclaimer


@pytest.mark.asyncio
async def test_compose_recipe_marketplace_beta_snapshot() -> None:
    session = AsyncMock()
    session.scalar = AsyncMock(side_effect=[3, 1, 4])

    with patch("app.application.services.recipe_marketplace_beta.settings") as mock_settings:
        mock_settings.recipe_marketplace_beta_enabled = True
        snap = await compose_recipe_marketplace_beta_snapshot(session)

    assert snap.enabled is True
    assert snap.approved_count == 3
    assert snap.pending_count == 1
    assert snap.total_listings == 4
