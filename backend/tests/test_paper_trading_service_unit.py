"""Unit coverage for paper trading bee (simulated fills + guardrails)."""

from __future__ import annotations

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.paper_trading_service import (
    _is_paper_project,
    build_portfolio_snapshot,
    get_or_create_account,
    run_paper_trading_tick_for_project,
)
from app.infrastructure.persistence.models.external_project import ExternalProject
from app.infrastructure.persistence.models.paper_trading import PaperTradingAccount


def test_is_paper_project_when_trading_mode_paper() -> None:
    project = ExternalProject(
        id=uuid.uuid4(),
        slug="desk",
        display_name="Desk",
        project_kind="trading",
        owner_dashboard_user_id=uuid.uuid4(),
        settings={"trading_mode": "paper"},
        webhook_url=None,
        webhook_secret_hash=None,
        is_active=True,
    )
    assert _is_paper_project(project) is True


@pytest.mark.asyncio
async def test_get_or_create_account_when_missing_then_inserts() -> None:
    project_id = uuid.uuid4()
    project = ExternalProject(
        id=project_id,
        slug="desk",
        display_name="Desk",
        project_kind="trading",
        owner_dashboard_user_id=uuid.uuid4(),
        settings={"trading_mode": "paper", "starting_cash_usd": 5000},
        webhook_url=None,
        webhook_secret_hash=None,
        is_active=True,
    )
    session = AsyncMock()
    exec_result = MagicMock()
    exec_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=exec_result)
    session.add = MagicMock()
    session.flush = AsyncMock()

    row = await get_or_create_account(session, project=project)
    assert float(row.cash_usd) == 5000.0
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_run_paper_trading_tick_when_halted_skips(monkeypatch: pytest.MonkeyPatch) -> None:
    project_id = uuid.uuid4()
    project = ExternalProject(
        id=project_id,
        slug="halted",
        display_name="Halted",
        project_kind="trading",
        owner_dashboard_user_id=uuid.uuid4(),
        settings={"trading_mode": "paper"},
        webhook_url=None,
        webhook_secret_hash=None,
        is_active=True,
    )
    account = PaperTradingAccount(
        project_id=project_id,
        cash_usd=Decimal("1000"),
        starting_cash_usd=Decimal("1000"),
        is_halted=True,
        halt_reason="operator manual halt",
        watchlist=["BTC"],
    )

    async def fake_get_or_create(*_args: object, **_kwargs: object) -> PaperTradingAccount:
        return account

    monkeypatch.setattr(
        "app.application.services.paper_trading_service.get_or_create_account",
        fake_get_or_create,
    )
    monkeypatch.setattr("app.application.services.paper_trading_service.settings.paper_trading_enabled", True)

    session = AsyncMock()
    out = await run_paper_trading_tick_for_project(session, project=project)
    assert out["status"] == "halted"
