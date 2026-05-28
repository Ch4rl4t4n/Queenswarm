"""Authentication coverage for operator router."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import dashboard_admin_wall, require_dashboard_session
from app.presentation.api.routers import operator as operator_router


@pytest.fixture
def restore_app_overrides() -> None:
    """Clear dependency overrides after each case."""

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_operator_plugins_requires_dashboard_auth(restore_app_overrides: None) -> None:
    """Operator routes reject anonymous callers."""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/operator/plugins")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_operator_plugins_allows_dashboard_admin(restore_app_overrides: None) -> None:
    """Operator routes allow dashboard-admin sessions."""

    app.dependency_overrides[dashboard_admin_wall] = lambda: True
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": "dash:operator"}

    original = operator_router.plugin_manifest
    operator_router.plugin_manifest = lambda: {"plugins": []}
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/operator/plugins")
    finally:
        operator_router.plugin_manifest = original

    assert response.status_code == 200
    assert response.json() == {"plugins": []}
