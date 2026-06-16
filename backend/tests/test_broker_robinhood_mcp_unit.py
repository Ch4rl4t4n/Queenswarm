"""Unit tests for Track P RA1/RA2 Robinhood Agentic MCP preset."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.broker_robinhood_mcp_service import (
    ROBINHOOD_MCP_SLUG,
    ROBINHOOD_MCP_TEMPLATE_ID,
    compose_robinhood_mcp_readiness,
    run_robinhood_mcp_probe,
)
from app.application.services.broker_guardrails_service import BrokerGuardrailsOut


@pytest.mark.asyncio
async def test_compose_robinhood_mcp_readiness_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.application.services.broker_robinhood_mcp_service.settings",
        MagicMock(trading_cockpit_enabled=True, robinhood_mcp_preset_enabled=False, broker_guardrails_enabled=True),
    )
    out = await compose_robinhood_mcp_readiness(
        AsyncMock(),
        tenant_id=uuid.uuid4(),
        dashboard_user_id=uuid.uuid4(),
        tenant=MagicMock(),
    )
    assert out.enabled is False


@pytest.mark.asyncio
async def test_compose_robinhood_mcp_readiness_checklist(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    tenant = MagicMock(operator_settings={})
    tenant.id = tenant_id

    guardrails = BrokerGuardrailsOut(
        enabled=True,
        venues=["polymarket", "robinhood"],
        max_order_usd=100.0,
        daily_cap_usd=500.0,
        kill_switch=False,
        approve_mode="always",
    )
    connector_row = MagicMock(is_active=True, last_tested_at=None, secrets_cipher="cipher")

    monkeypatch.setattr(
        "app.application.services.broker_robinhood_mcp_service.settings",
        MagicMock(
            trading_cockpit_enabled=True,
            robinhood_mcp_preset_enabled=True,
            broker_guardrails_enabled=True,
        ),
    )
    svc = MagicMock()
    svc.fetch_by_slug = AsyncMock(return_value=connector_row)
    svc._secrets_dict = MagicMock(return_value={"oauth2_access_token": "tok"})
    with (
        patch(
            "app.application.services.broker_robinhood_mcp_service.get_phase3_template",
            MagicMock(return_value=MagicMock()),
        ),
        patch(
            "app.application.services.broker_robinhood_mcp_service.DynamicConnectorService",
            MagicMock(return_value=svc),
        ),
        patch(
            "app.application.services.broker_robinhood_mcp_service.get_broker_guardrails",
            AsyncMock(return_value=guardrails),
        ),
    ):
        out = await compose_robinhood_mcp_readiness(
            AsyncMock(),
            tenant_id=tenant_id,
            dashboard_user_id=user_id,
            tenant=tenant,
        )

    assert out.enabled is True
    assert out.connector_installed is True
    assert out.oauth_ready is True
    assert out.guardrails_ready is True
    assert out.template_id == ROBINHOOD_MCP_TEMPLATE_ID
    assert out.connector_slug == ROBINHOOD_MCP_SLUG
    assert len(out.steps) == 4


@pytest.mark.asyncio
async def test_run_robinhood_mcp_probe_persists_bucket(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant = MagicMock(operator_settings={})
    tenant.id = uuid.uuid4()
    ready = MagicMock(
        connector_installed=True,
        oauth_ready=True,
        guardrails_kill_switch=False,
        operator_hint="ok",
    )
    with patch(
        "app.application.services.broker_robinhood_mcp_service.compose_robinhood_mcp_readiness",
        AsyncMock(return_value=ready),
    ):
        result = await run_robinhood_mcp_probe(AsyncMock(), tenant=tenant, dashboard_user_id=uuid.uuid4())

    assert result["ok"] is True
    assert result["status"] == "passed"
    assert tenant.operator_settings["broker_robinhood_mcp"]["last_probe_status"] == "passed"
