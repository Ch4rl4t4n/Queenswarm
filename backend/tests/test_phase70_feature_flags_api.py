"""Phase 7.0 feature-flag API gates."""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_session, require_subject


@pytest.fixture
def restore_app_overrides() -> None:
    yield
    app.dependency_overrides.clear()


def _fake_dashboard_claims() -> dict[str, str]:
    return {
        "sub": "dash:11111111-1111-4111-8111-111111111111",
        "typ": "dashboard_access",
        "scope": "dash:read dash:operator dash:admin",
    }


@pytest.mark.asyncio
async def test_monitoring_snapshot_when_advanced_disabled_returns_403(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_subject] = lambda: "pytest"
    monkeypatch.setattr(settings, "advanced_monitoring_enabled", False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/operator/monitoring/snapshot", headers={"Authorization": "Bearer x"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_simulations_when_disabled_returns_403(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_subject] = lambda: "pytest"
    monkeypatch.setattr(settings, "simulations_enabled", False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/simulations", headers={"Authorization": "Bearer x"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_recipes_when_disabled_returns_403(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_subject] = lambda: "pytest"
    monkeypatch.setattr(settings, "recipes_enabled", False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/recipes/search?q=phase70", headers={"Authorization": "Bearer x"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_api_key_management_when_disabled_returns_403(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = _fake_dashboard_claims
    monkeypatch.setattr(settings, "api_key_management_enabled", False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/auth/api-keys", headers={"Authorization": "Bearer x"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_advanced_2fa_when_disabled_returns_403(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = _fake_dashboard_claims
    monkeypatch.setattr(settings, "security_2fa_advanced_enabled", False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/profile/totp/provision",
            headers={"Authorization": "Bearer x"},
            json={"password": "irrelevant"},
        )
    assert res.status_code == 403
