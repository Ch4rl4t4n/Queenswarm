"""Trading Cockpit — config merge and project settings mapping."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.trading_cockpit import (
    DEFAULT_TRADING_LANE,
    merge_trading_lane_patch,
    _project_settings_from_lane,
    apply_trading_cockpit_config,
    TradingCockpitConfigPatch,
)


def test_merge_trading_lane_patch_deep_merges_risk() -> None:
    root = merge_trading_lane_patch(
        {},
        {"risk": {"max_order_usd": 1000}, "venue": "polymarket"},
    )
    lane = root["trading_lane"]
    assert lane["risk"]["max_order_usd"] == 1000
    assert lane["risk"]["max_daily_loss_usd"] == DEFAULT_TRADING_LANE["risk"]["max_daily_loss_usd"]
    assert lane["venue"] == "polymarket"


def test_project_settings_from_lane_paper() -> None:
    lane = {**DEFAULT_TRADING_LANE, "venue": "paper_crypto"}
    settings = _project_settings_from_lane(lane)
    assert settings["trading_mode"] == "paper"
    assert settings["venue"] == ""
    assert "BTC" in settings["watchlist"]


def test_project_settings_from_lane_polymarket() -> None:
    lane = {**DEFAULT_TRADING_LANE, "venue": "polymarket", "default_mode": "real"}
    settings = _project_settings_from_lane(lane)
    assert settings["trading_mode"] == "real"
    assert settings["venue"] == "polymarket"
    assert settings["connector_slug"] == "polymarket_clob"


@pytest.mark.asyncio
async def test_apply_trading_cockpit_config_sets_real_mode_for_polymarket() -> None:
    owner_id = uuid.uuid4()
    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        operator_settings={},
    )
    project = SimpleNamespace(
        id=uuid.uuid4(),
        slug="hive-trader",
        settings={},
        owner_dashboard_user_id=owner_id,
        project_kind="trading",
        is_active=True,
    )
    session = AsyncMock()

    with (
        patch(
            "app.application.services.trading_cockpit.ensure_primary_trading_project",
            new_callable=AsyncMock,
            return_value=project,
        ),
        patch(
            "app.application.services.trading_cockpit.sync_project_from_lane",
            new_callable=AsyncMock,
        ) as sync_mock,
    ):
        lane = await apply_trading_cockpit_config(
            session,
            tenant=tenant,
            owner_id=owner_id,
            patch=TradingCockpitConfigPatch(venue="polymarket"),
        )
    assert lane["default_mode"] == "real"
    assert lane["venue"] == "polymarket"
    sync_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_deposit_paper_cash_rejects_real_project() -> None:
    from app.application.services.paper_trading_service import deposit_paper_cash
    from app.infrastructure.persistence.models.external_project import ExternalProject

    project = ExternalProject(
        id=uuid.uuid4(),
        slug="live",
        display_name="Live",
        project_kind="trading",
        owner_dashboard_user_id=uuid.uuid4(),
        settings={"trading_mode": "real", "venue": "polymarket"},
        webhook_url=None,
        webhook_secret_hash=None,
        is_active=True,
    )
    session = AsyncMock()
    with pytest.raises(ValueError, match="Paper deposit"):
        await deposit_paper_cash(session, project=project, amount_usd=100.0)
