"""API unit tests for RA4 broker read-only session routes."""

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
        "sub": "auth0|test",
    }


@pytest.mark.asyncio
async def test_trading_cockpit_readonly_session_get(restore_overrides: None) -> None:
    from app.application.services.broker_readonly_session_service import BrokerReadonlyKpiOut

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    app.dependency_overrides[get_db] = lambda: AsyncMock()

    kpi = BrokerReadonlyKpiOut(enabled=True, readonly_required=True, live_eligible=False)

    with patch(
        "app.presentation.api.routers.trading_cockpit.compose_broker_readonly_kpi",
        AsyncMock(return_value=kpi),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/api/v1/trading-cockpit/readonly-session",
                headers={"Authorization": "Bearer x"},
            )

    assert response.status_code == 200
    assert response.json()["readonly_required"] is True


@pytest.mark.asyncio
async def test_trading_cockpit_readonly_smoke_post(restore_overrides: None) -> None:
    from app.application.services.broker_readonly_session_service import BrokerReadonlySmokeOut

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    result = BrokerReadonlySmokeOut(ok=True, smoke_status="passed", message="ok", live_eligible=True)

    with patch(
        "app.presentation.api.routers.trading_cockpit.run_broker_readonly_smoke_probe",
        AsyncMock(return_value=result),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/trading-cockpit/readonly-session/smoke",
                headers={"Authorization": "Bearer x"},
            )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_trading_cockpit_readonly_bootstrap_post(restore_overrides: None) -> None:
    from app.application.services.broker_readonly_session_service import BrokerReadonlyBootstrapOut

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal
    mock_db = AsyncMock()
    mock_db.commit = AsyncMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    result = BrokerReadonlyBootstrapOut(ok=True, session_id="abc", session_href="/agents/sessions/abc")

    with patch(
        "app.presentation.api.routers.trading_cockpit.bootstrap_broker_readonly_session",
        AsyncMock(return_value=result),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/trading-cockpit/readonly-session/bootstrap",
                headers={"Authorization": "Bearer x"},
            )

    assert response.status_code == 200
    assert response.json()["session_id"] == "abc"
