"""Authentication coverage for dashboard router."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import dashboard_admin_wall, get_db, require_dashboard_session


@pytest.fixture
def restore_app_overrides() -> None:
    """Clear dependency overrides after each case."""

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dashboard_summary_requires_dashboard_auth(restore_app_overrides: None) -> None:
    """Dashboard routes reject anonymous callers."""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/dashboard/summary")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_dashboard_summary_allows_dashboard_admin(restore_app_overrides: None) -> None:
    """Dashboard summary succeeds for dashboard-admin sessions."""

    async def _db() -> AsyncIterator[AsyncMock]:
        session = AsyncMock()
        session.scalar = AsyncMock(side_effect=[0, 0])
        execute_result = MagicMock()
        execute_result.all.return_value = []
        session.execute = AsyncMock(return_value=execute_result)
        yield session

    app.dependency_overrides[dashboard_admin_wall] = lambda: True
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": "dash:operator"}
    app.dependency_overrides[get_db] = _db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["agents"]["total"] == 0
    assert body["tasks"]["pending"] == 0
