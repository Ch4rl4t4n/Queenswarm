"""Authentication coverage for agents router."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import dashboard_admin_wall, get_db, require_dashboard_session
from app.presentation.api.routers import agents as agents_router


@pytest.fixture
def restore_app_overrides() -> None:
    """Clear dependency overrides after each case."""

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_agents_list_requires_dashboard_auth(restore_app_overrides: None) -> None:
    """Agents endpoints reject anonymous callers."""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/agents")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_agents_list_allows_dashboard_admin(restore_app_overrides: None) -> None:
    """Agents list succeeds for dashboard-admin session."""

    async def _db() -> AsyncIterator[AsyncMock]:
        yield AsyncMock()

    async def _fake_list_agents(*_args: object, **_kwargs: object) -> list[object]:
        return []

    app.dependency_overrides[dashboard_admin_wall] = lambda: True
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": "dash:operator"}
    app.dependency_overrides[get_db] = _db

    original = agents_router.list_agents
    agents_router.list_agents = _fake_list_agents
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/agents")
    finally:
        agents_router.list_agents = original

    assert response.status_code == 200
    assert response.json() == []
