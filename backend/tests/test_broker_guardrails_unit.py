"""Unit tests for Track P RA3 broker guardrails service."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.broker_guardrails_service import (
    BrokerGuardrailsOut,
    BrokerGuardrailsPatchIn,
    approve_mode_to_execution_flow,
    evaluate_broker_order_gate,
    save_broker_guardrails,
)


def test_evaluate_broker_order_gate_blocks_kill_switch() -> None:
    guardrails = BrokerGuardrailsOut(kill_switch=True)
    result = evaluate_broker_order_gate(guardrails, venue="polymarket", notional_usd=10.0, operator_confirmed=True)
    assert result.allowed is False
    assert result.reason == "kill_switch"


def test_evaluate_broker_order_gate_blocks_max_order() -> None:
    guardrails = BrokerGuardrailsOut(max_order_usd=50.0)
    result = evaluate_broker_order_gate(guardrails, venue="polymarket", notional_usd=75.0, operator_confirmed=True)
    assert result.allowed is False
    assert result.reason == "max_order"


def test_evaluate_broker_order_gate_blocks_daily_cap() -> None:
    guardrails = BrokerGuardrailsOut(daily_cap_usd=100.0, daily_spent_usd=90.0, daily_spend_date="2099-01-01")
    result = evaluate_broker_order_gate(guardrails, venue="polymarket", notional_usd=20.0, operator_confirmed=True)
    assert result.allowed is False
    assert result.reason == "daily_cap"


def test_evaluate_broker_order_gate_requires_approval() -> None:
    guardrails = BrokerGuardrailsOut(approve_mode="always")
    result = evaluate_broker_order_gate(guardrails, venue="polymarket", notional_usd=10.0, operator_confirmed=False)
    assert result.allowed is False
    assert result.reason == "approval_required"


def test_evaluate_broker_order_gate_allows_when_ok() -> None:
    guardrails = BrokerGuardrailsOut(max_order_usd=100.0, daily_cap_usd=500.0, approve_mode="trusted_auto")
    result = evaluate_broker_order_gate(guardrails, venue="polymarket", notional_usd=25.0, operator_confirmed=False)
    assert result.allowed is True


def test_approve_mode_to_execution_flow() -> None:
    assert approve_mode_to_execution_flow("always") == "manual_approve"
    assert approve_mode_to_execution_flow("simulate_first") == "simulate_first"


@pytest.mark.asyncio
async def test_save_broker_guardrails_persists_and_syncs_lane() -> None:
    tenant_id = uuid.uuid4()
    tenant = MagicMock()
    tenant.operator_settings = {}
    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)
    session.flush = AsyncMock()

    saved = await save_broker_guardrails(
        session,
        tenant_id=tenant_id,
        patch=BrokerGuardrailsPatchIn(
            kill_switch=True,
            max_order_usd=75.0,
            daily_cap_usd=300.0,
            approve_mode="simulate_first",
        ),
    )
    assert saved.kill_switch is True
    assert saved.max_order_usd == 75.0
    bucket = tenant.operator_settings["broker_guardrails"]
    assert bucket["max_order_usd"] == 75.0
    assert tenant.operator_settings["trading_lane"]["execution_flow"] == "simulate_first"
    assert tenant.operator_settings["trading_lane"]["risk"]["max_order_usd"] == 75.0


@pytest.mark.asyncio
async def test_get_broker_guardrails_from_tenant_bucket() -> None:
    tenant_id = uuid.uuid4()
    tenant = MagicMock()
    tenant.operator_settings = {
        "broker_guardrails": {
            "enabled": True,
            "kill_switch": False,
            "max_order_usd": 120.0,
            "daily_cap_usd": 600.0,
            "approve_mode": "always",
            "venues": ["polymarket"],
            "daily_spend": {"date": "2099-01-01", "spent_usd": 50.0},
        },
    }
    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)

    from app.application.services.broker_guardrails_service import get_broker_guardrails

    out = await get_broker_guardrails(session, tenant_id=tenant_id)
    assert out.max_order_usd == 120.0
    assert out.venues == ["polymarket"]


@pytest.mark.asyncio
async def test_record_broker_daily_spend_increments() -> None:
    tenant_id = uuid.uuid4()
    tenant = MagicMock()
    tenant.operator_settings = {
        "broker_guardrails": {
            "max_order_usd": 100.0,
            "daily_cap_usd": 500.0,
            "daily_spend": {"date": __import__("datetime").datetime.now(__import__("datetime").UTC).date().isoformat(), "spent_usd": 10.0},
        },
    }
    session = AsyncMock()
    session.get = AsyncMock(return_value=tenant)
    session.flush = AsyncMock()

    from app.application.services.broker_guardrails_service import get_broker_guardrails, record_broker_daily_spend

    await record_broker_daily_spend(session, tenant_id=tenant_id, notional_usd=15.0)
    out = await get_broker_guardrails(session, tenant_id=tenant_id)
    assert out.daily_spent_usd == 25.0
