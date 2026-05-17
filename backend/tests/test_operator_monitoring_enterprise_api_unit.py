"""Enterprise gate coverage for operator monitoring endpoints."""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_user_with_tenant_role
from app.presentation.api.routers import operator_monitoring


@pytest.fixture
def restore_app_overrides() -> None:
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_monitoring_snapshot_when_enterprise_mode_disabled_returns_403(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "tenant_role": "owner",
        "tenant_id": "11111111-1111-4111-8111-111111111111",
    }
    monkeypatch.setattr(settings, "advanced_monitoring_enabled", True)
    monkeypatch.setattr(settings, "enterprise_monitoring_enabled", False)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/operator/monitoring/snapshot", headers={"Authorization": "Bearer x"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_monitoring_snapshot_when_non_admin_role_returns_403(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "tenant_role": "member",
        "tenant_id": "11111111-1111-4111-8111-111111111111",
    }
    monkeypatch.setattr(settings, "advanced_monitoring_enabled", True)
    monkeypatch.setattr(settings, "enterprise_monitoring_enabled", True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/operator/monitoring/snapshot", headers={"Authorization": "Bearer x"})
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_monitoring_snapshot_when_enterprise_tier_returns_payload(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    async def fake_sub(_db, *, tenant_id):  # noqa: ANN001
        del tenant_id
        return SimpleNamespace(tier="enterprise")

    async def fake_snapshot(_db, *, tenant_id=None):  # noqa: ANN001
        return {"ok": True, "tenant_id": str(tenant_id)}

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "tenant_role": "owner",
        "tenant_id": "11111111-1111-4111-8111-111111111111",
    }
    monkeypatch.setattr(settings, "advanced_monitoring_enabled", True)
    monkeypatch.setattr(settings, "enterprise_monitoring_enabled", True)
    monkeypatch.setattr(operator_monitoring, "ensure_tenant_subscription", fake_sub)
    monkeypatch.setattr(operator_monitoring, "build_monitoring_snapshot", fake_snapshot)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/operator/monitoring/snapshot", headers={"Authorization": "Bearer x"})
    assert res.status_code == 200
    assert res.json()["ok"] is True
