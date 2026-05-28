"""Auth and policy checks for simulations API routes."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.presentation.api.deps import dashboard_admin_wall, require_dashboard_session
from app.presentation.api.routers import simulations as simulations_router


@pytest.fixture
def restore_app_overrides() -> None:
    """Clear FastAPI dependency overrides between tests."""

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_simulations_endpoint_requires_dashboard_auth() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/simulations")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_simulations_endpoint_returns_403_when_feature_disabled(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_db():
        yield object()

    app.dependency_overrides[dashboard_admin_wall] = lambda: True
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": "dash:operator"}
    app.dependency_overrides[get_db] = _fake_db
    monkeypatch.setattr(settings, "simulations_enabled", False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/simulations", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_simulations_endpoint_allows_dashboard_admin_session(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_db():
        yield object()

    async def _fake_list_recent(
        _db: object,
        task_id: uuid.UUID | None,
        result_type: object | None,
        limit: int,
    ) -> list[dict[str, object]]:
        _ = task_id, result_type, limit
        return []

    app.dependency_overrides[dashboard_admin_wall] = lambda: True
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": "dash:operator"}
    app.dependency_overrides[get_db] = _fake_db
    monkeypatch.setattr(settings, "simulations_enabled", True)
    simulations_router.list_recent_simulation_audits = _fake_list_recent  # type: ignore[assignment]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/simulations", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    assert response.json() == []
