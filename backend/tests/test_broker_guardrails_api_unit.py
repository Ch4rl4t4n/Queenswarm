"""API unit tests for RA3 broker guardrails routes."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_user_with_tenant_role


@pytest.fixture
def restore_overrides() -> None:
    yield
    app.dependency_overrides.clear()


def _owner_principal() -> dict[str, object]:
    return {
        "user": type("U", (), {"id": uuid.uuid4()})(),
        "tenant_id": uuid.uuid4(),
        "tenant_role": "owner",
        "permissions": ["*"],
    }


@pytest.mark.asyncio
async def test_trading_cockpit_guardrails_get(restore_overrides: None) -> None:
    from app.application.services.broker_guardrails_service import BrokerGuardrailsOut

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    snapshot = BrokerGuardrailsOut(kill_switch=False, source="deployment")

    with patch(
        "app.presentation.api.routers.trading_cockpit.get_broker_guardrails",
        AsyncMock(return_value=snapshot),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/trading-cockpit/guardrails",
                headers={"Authorization": "Bearer x"},
            )

    assert response.status_code == 200
    assert response.json()["max_order_usd"] == 100.0


@pytest.mark.asyncio
async def test_trading_cockpit_guardrails_patch(restore_overrides: None) -> None:
    from app.application.services.broker_guardrails_service import BrokerGuardrailsOut

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    saved = BrokerGuardrailsOut(kill_switch=True, max_order_usd=50.0, source="tenant")

    with patch(
        "app.presentation.api.routers.trading_cockpit.save_broker_guardrails",
        AsyncMock(return_value=saved),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/api/v1/trading-cockpit/guardrails",
                headers={"Authorization": "Bearer x"},
                json={"kill_switch": True, "max_order_usd": 50},
            )

    assert response.status_code == 200
    assert response.json()["kill_switch"] is True
    mock_db.commit.assert_awaited_once()
