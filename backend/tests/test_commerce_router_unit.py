"""API unit tests for commerce order-events read lane."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.application.services.commerce_order_sync import CommerceOrderEvent
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
        "sub": "auth0|test",
    }


@pytest.mark.asyncio
async def test_commerce_order_events_when_enabled_then_returns_list(restore_overrides: None) -> None:
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    events = [
        CommerceOrderEvent(
            provider="stripe",
            event_id="evt_1",
            event_type="checkout.session.completed",
            object_id="cs_1",
        ),
    ]

    with patch(
        "app.presentation.api.routers.commerce.list_recent_commerce_order_events",
        AsyncMock(return_value=events),
    ):
        with patch("app.presentation.api.routers.commerce.settings") as mock_settings:
            mock_settings.execution_studio_enabled = True
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/api/v1/commerce/order-events",
                    headers={"Authorization": "Bearer x"},
                )

    assert response.status_code == 200
    body = response.json()
    assert body[0]["event_id"] == "evt_1"


@pytest.mark.asyncio
async def test_commerce_order_events_when_studio_disabled_then_404(restore_overrides: None) -> None:
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    with patch("app.presentation.api.routers.commerce.settings") as mock_settings:
        mock_settings.execution_studio_enabled = False
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/commerce/order-events",
                headers={"Authorization": "Bearer x"},
            )

    assert response.status_code == 404
