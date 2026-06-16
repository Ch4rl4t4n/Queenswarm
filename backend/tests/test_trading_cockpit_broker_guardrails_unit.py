"""Trading cockpit snapshot tests for RA3 broker guardrails embed."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.trading_cockpit import compose_trading_cockpit_snapshot


@pytest.mark.asyncio
async def test_compose_trading_cockpit_snapshot_includes_broker_guardrails(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    tenant = MagicMock()
    tenant.id = tenant_id
    tenant.operator_settings = {}

    session = AsyncMock()
    project = MagicMock()
    project.id = uuid.uuid4()
    project.slug = "hive-trader"
    project.display_name = "Polymarket Trader"
    project.is_active = True
    project.settings = {}

    monkeypatch.setattr(
        "app.application.services.trading_cockpit.settings",
        MagicMock(
            trading_cockpit_enabled=True,
            broker_guardrails_enabled=True,
            broker_readonly_session_enabled=False,
            broker_order_queue_enabled=False,
            prediction_markets_enabled=True,
            prediction_markets_live_trading_enabled=False,
        ),
    )

    with (
        patch(
            "app.application.services.trading_cockpit.ensure_primary_trading_project",
            AsyncMock(return_value=project),
        ),
        patch("app.application.services.trading_cockpit.sync_project_from_lane", AsyncMock()),
        patch(
            "app.application.services.trading_cockpit._build_funding_snapshot",
            AsyncMock(return_value={"status": "needs_credentials", "message": "test"}),
        ),
        patch(
            "app.application.services.trading_cockpit.aggregate_metrics",
            AsyncMock(return_value={}),
        ),
        patch(
            "app.application.services.trading_cockpit.recent_run_series",
            AsyncMock(return_value=[]),
        ),
        patch(
            "app.application.services.trading_cockpit.build_prediction_markets_status_snapshot",
            AsyncMock(return_value={"live_trading_enabled": False, "connectors_active": {}}),
        ),
        patch(
            "app.application.services.broker_guardrails_service.get_broker_guardrails",
            AsyncMock(
                return_value=MagicMock(
                    kill_switch=True,
                    model_dump=lambda mode, **kwargs: {"kill_switch": True, "max_order_usd": 100.0},
                ),
            ),
        ),
    ):
        session.execute = AsyncMock(return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=lambda: []))))
        snapshot = await compose_trading_cockpit_snapshot(
            session,
            dashboard_user_id=user_id,
            tenant=tenant,
        )

    assert snapshot.broker_guardrails is not None
    assert snapshot.broker_guardrails["kill_switch"] is True
    assert snapshot.performance["is_halted"] is True
