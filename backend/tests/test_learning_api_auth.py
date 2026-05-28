"""Authentication coverage for learning router."""

from __future__ import annotations

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_session
from app.presentation.api.routers import learning as learning_router


@pytest.fixture
def restore_app_overrides() -> None:
    """Clear dependency overrides after each case."""

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_learning_badges_requires_dashboard_auth(restore_app_overrides: None) -> None:
    """Learning routes reject anonymous callers."""

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/learning/bee-badges/catalog")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_learning_badges_allow_dashboard_session(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Learning routes accept dashboard sessions."""

    async def _db() -> AsyncIterator[AsyncMock]:
        yield AsyncMock()

    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": "dash:operator"}
    app.dependency_overrides[get_db] = _db
    monkeypatch.setattr(learning_router, "bee_gamification_enabled", lambda: True)
    monkeypatch.setattr(learning_router, "list_badge_catalog", lambda: [])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/learning/bee-badges/catalog")

    assert response.status_code == 200
    assert response.json() == []
