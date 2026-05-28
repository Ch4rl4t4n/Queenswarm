"""Authentication coverage for swarms router."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import dashboard_admin_wall, get_db, require_dashboard_session
from app.presentation.api.routers import swarms as swarms_router


@pytest.fixture
def restore_app_overrides() -> None:
    """Clear dependency overrides after each case."""

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_swarms_list_requires_dashboard_auth(restore_app_overrides: None) -> None:
    """Swarms endpoints reject anonymous callers."""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/swarms")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_swarms_list_allows_dashboard_admin(restore_app_overrides: None) -> None:
    """Swarms list succeeds for dashboard-admin session."""

    async def _db() -> AsyncIterator[AsyncMock]:
        yield AsyncMock()

    async def _fake_list_sub_swarms(*_args: object, **_kwargs: object) -> list[object]:
        return []

    app.dependency_overrides[dashboard_admin_wall] = lambda: True
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": "dash:operator"}
    app.dependency_overrides[get_db] = _db

    original = swarms_router.list_sub_swarms
    swarms_router.list_sub_swarms = _fake_list_sub_swarms
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/v1/swarms")
    finally:
        swarms_router.list_sub_swarms = original

    assert response.status_code == 200
    assert response.json() == []
