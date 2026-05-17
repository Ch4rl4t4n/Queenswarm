"""ASGI tests for dashboard tenant list/switch endpoints."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_session
from app.presentation.api.routers import dashboard_session as dashboard_router


@pytest.fixture
def restore_app_overrides() -> None:
    """Reset DI overrides between tests."""

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dashboard_tenants_list_returns_current_and_memberships(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tenant list endpoint returns active tenant and membership rows."""

    active_tenant_id = str(uuid.uuid4())
    user = SimpleNamespace(id=uuid.uuid4(), active_tenant_id=uuid.UUID(active_tenant_id))

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _commit() -> None:
            return None

        yield SimpleNamespace(commit=_commit)

    async def _fake_current_user(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return user

    async def _fake_ensure(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return None

    async def _fake_list(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return [
            {"id": active_tenant_id, "slug": "personal", "name": "Personal", "role": "owner", "is_active": True},
        ]

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": f"dash:{user.id}"}
    monkeypatch.setattr(dashboard_router, "_current_dashboard_user", _fake_current_user)
    monkeypatch.setattr(dashboard_router, "ensure_default_tenant_for_user", _fake_ensure)
    monkeypatch.setattr(dashboard_router, "list_user_tenants", _fake_list)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/auth/tenants", headers={"Authorization": "Bearer x"})
    assert res.status_code == 200
    body = res.json()
    assert body["current_tenant_id"] == active_tenant_id
    assert body["tenants"][0]["slug"] == "personal"


@pytest.mark.asyncio
async def test_dashboard_tenant_switch_rotates_token_bundle(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tenant switch returns a fresh token bundle for scoped context."""

    user = SimpleNamespace(id=uuid.uuid4(), active_tenant_id=None)

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _commit() -> None:
            return None

        async def _refresh(_row: object) -> None:
            return None

        async def _rollback() -> None:
            return None

        yield SimpleNamespace(commit=_commit, refresh=_refresh, rollback=_rollback)

    async def _fake_current_user(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return user

    async def _fake_switch(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return SimpleNamespace(id=uuid.uuid4())

    async def _fake_issue(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return {"access_token": "at", "refresh_token": "rt", "expires_in": 900, "token_type": "bearer"}

    audit_called: dict[str, bool] = {"ok": False}

    async def _fake_audit(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        audit_called["ok"] = True

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": f"dash:{user.id}"}
    monkeypatch.setattr(dashboard_router, "_current_dashboard_user", _fake_current_user)
    monkeypatch.setattr(dashboard_router, "switch_active_tenant", _fake_switch)
    monkeypatch.setattr(dashboard_router, "_issue_pair", _fake_issue)
    monkeypatch.setattr(dashboard_router, "_safe_tenant_audit", _fake_audit)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/api/v1/auth/tenants/switch",
            headers={"Authorization": "Bearer x"},
            json={"tenant_id": str(uuid.uuid4())},
        )
    assert res.status_code == 200
    assert res.json()["access_token"] == "at"
    assert audit_called["ok"] is True
