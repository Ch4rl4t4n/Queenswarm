"""API unit tests for Robinhood MCP trading cockpit routes."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
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
async def test_robinhood_mcp_readiness_get(restore_overrides: None) -> None:
    from app.application.services.broker_robinhood_mcp_service import RobinhoodMcpReadinessOut

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    readiness = RobinhoodMcpReadinessOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        connector_installed=True,
        oauth_ready=False,
        operator_hint="Seal OAuth token",
    )

    with patch(
        "app.presentation.api.routers.trading_cockpit.compose_robinhood_mcp_readiness",
        AsyncMock(return_value=readiness),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/trading-cockpit/robinhood-mcp",
                headers={"Authorization": "Bearer x"},
            )

    assert response.status_code == 200
    assert response.json()["connector_installed"] is True


@pytest.mark.asyncio
async def test_robinhood_mcp_readiness_get_disabled(restore_overrides: None) -> None:
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    with patch(
        "app.presentation.api.routers.trading_cockpit.settings",
        type("S", (), {"trading_cockpit_enabled": True, "robinhood_mcp_preset_enabled": False})(),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/trading-cockpit/robinhood-mcp",
                headers={"Authorization": "Bearer x"},
            )

    assert response.status_code == 404
