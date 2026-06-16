"""Unit tests for Track P RA4 broker read-only session service."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.broker_guardrails_service import BrokerGuardrailsOut
from app.application.services.broker_readonly_session_service import (
    assert_live_broker_allowed,
    compose_broker_readonly_kpi,
    is_live_broker_eligible,
    run_broker_readonly_smoke_probe,
)


def test_is_live_broker_eligible_when_smoke_and_guardrails_ok() -> None:
    guardrails = BrokerGuardrailsOut(source="tenant", kill_switch=False)
    bucket = {"smoke_passed": True}
    assert is_live_broker_eligible(guardrails=guardrails, readonly_bucket=bucket, gamma_ready=True) is True


def test_is_live_broker_eligible_blocks_without_smoke() -> None:
    guardrails = BrokerGuardrailsOut(source="tenant")
    bucket: dict[str, object] = {}
    assert is_live_broker_eligible(guardrails=guardrails, readonly_bucket=bucket, gamma_ready=True) is False


def test_is_live_broker_eligible_blocks_deployment_guardrails() -> None:
    guardrails = BrokerGuardrailsOut(source="deployment")
    bucket = {"smoke_passed": True}
    assert is_live_broker_eligible(guardrails=guardrails, readonly_bucket=bucket, gamma_ready=True) is False


@pytest.mark.asyncio
async def test_compose_broker_readonly_kpi_readonly_required(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    session = AsyncMock()
    tenant = MagicMock(operator_settings={"broker_readonly": {"smoke_passed": False}})
    session.get = AsyncMock(return_value=tenant)

    monkeypatch.setattr(
        "app.application.services.broker_readonly_session_service.settings",
        MagicMock(broker_readonly_session_enabled=True),
    )

    with (
        patch(
            "app.application.services.broker_readonly_session_service.get_broker_guardrails",
            AsyncMock(return_value=BrokerGuardrailsOut(source="deployment")),
        ),
        patch(
            "app.application.services.broker_readonly_session_service.build_prediction_markets_status_snapshot",
            AsyncMock(return_value={"connectors_active": {"polymarket_gamma": True}}),
        ),
    ):
        kpi = await compose_broker_readonly_kpi(session, tenant_id=tenant_id, dashboard_user_id=user_id)

    assert kpi.enabled is True
    assert kpi.readonly_required is True
    assert kpi.live_eligible is False
    assert kpi.gamma_connector_ready is True


@pytest.mark.asyncio
async def test_run_smoke_probe_fails_without_gamma(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    session = AsyncMock()
    tenant = MagicMock(operator_settings={})
    session.get = AsyncMock(return_value=tenant)

    monkeypatch.setattr(
        "app.application.services.broker_readonly_session_service.settings",
        MagicMock(broker_readonly_session_enabled=True),
    )

    with (
        patch(
            "app.application.services.broker_readonly_session_service.get_broker_guardrails",
            AsyncMock(return_value=BrokerGuardrailsOut(source="tenant")),
        ),
        patch(
            "app.application.services.broker_readonly_session_service.build_prediction_markets_status_snapshot",
            AsyncMock(return_value={"connectors_active": {"polymarket_gamma": False}}),
        ),
    ):
        result = await run_broker_readonly_smoke_probe(session, tenant_id=tenant_id, dashboard_user_id=user_id)

    assert result.ok is False
    assert result.smoke_status == "failed"
    assert tenant.operator_settings["broker_readonly"]["smoke_passed"] is False


@pytest.mark.asyncio
async def test_run_smoke_probe_passes_when_ready(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    session = AsyncMock()
    tenant = MagicMock(operator_settings={})
    session.get = AsyncMock(return_value=tenant)

    monkeypatch.setattr(
        "app.application.services.broker_readonly_session_service.settings",
        MagicMock(broker_readonly_session_enabled=True),
    )

    with (
        patch(
            "app.application.services.broker_readonly_session_service.get_broker_guardrails",
            AsyncMock(return_value=BrokerGuardrailsOut(source="tenant")),
        ),
        patch(
            "app.application.services.broker_readonly_session_service.build_prediction_markets_status_snapshot",
            AsyncMock(return_value={"connectors_active": {"polymarket_gamma": True}}),
        ),
    ):
        result = await run_broker_readonly_smoke_probe(session, tenant_id=tenant_id, dashboard_user_id=user_id)

    assert result.ok is True
    assert result.smoke_status == "passed"
    assert result.live_eligible is True


@pytest.mark.asyncio
async def test_assert_live_broker_allowed_blocks_smoke_required(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    session = AsyncMock()
    tenant = MagicMock(operator_settings={"broker_readonly": {"smoke_passed": False}})
    session.get = AsyncMock(return_value=tenant)

    monkeypatch.setattr(
        "app.application.services.broker_readonly_session_service.settings",
        MagicMock(broker_readonly_session_enabled=True),
    )

    with (
        patch(
            "app.application.services.broker_readonly_session_service.get_broker_guardrails",
            AsyncMock(return_value=BrokerGuardrailsOut(source="tenant")),
        ),
        patch(
            "app.application.services.broker_readonly_session_service.build_prediction_markets_status_snapshot",
            AsyncMock(return_value={"connectors_active": {"polymarket_gamma": True}}),
        ),
    ):
        block = await assert_live_broker_allowed(session, tenant_id=tenant_id, dashboard_user_id=user_id)

    assert block is not None
    assert block.reason == "broker_readonly_smoke_required"
