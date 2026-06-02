"""ASGI tests for dashboard session policy."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.presentation.api.deps import require_dashboard_user_with_tenant_role


@pytest.fixture
def restore_app_overrides() -> None:
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_session_policy_returns_effective_limits(restore_app_overrides: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "access_token_expire_minutes", 12)
    monkeypatch.setattr(settings, "refresh_token_expire_days", 9)
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_user_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_user_sustain_max", 240)
    monkeypatch.setattr(settings, "rate_limit_user_sustain_window_sec", 60.0)
    monkeypatch.setattr(settings, "oauth_state_ttl_sec", 600)
    monkeypatch.setattr(settings, "production_security_mode", False)
    monkeypatch.setattr(settings, "enable_2fa", True)

    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(id=tenant_id, operator_settings={})

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model, key):  # noqa: ANN001
            if key == tenant_id:
                return tenant
            return None

        yield SimpleNamespace(get=_get, commit=lambda: None, refresh=lambda _obj: None)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "tenant_id": tenant_id,
        "tenant_role": "owner",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/auth/session-policy",
            headers={"Authorization": "Bearer x"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token_expire_minutes"] == 12
    assert payload["refresh_token_expire_days"] == 9
    assert payload["rate_limit_requests"] == 240
    assert payload["rate_limit_window_sec"] == 60.0
    assert payload["oauth_state_ttl_sec"] == 600
    assert payload["two_fa_enabled"] is True
    assert payload["dashboard_2fa_session_max_hours_deployment"] == settings.dashboard_2fa_session_max_hours
    assert payload["editable"] is True


@pytest.mark.asyncio
async def test_session_policy_patch_persists_tenant_override(restore_app_overrides: None) -> None:
    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(id=tenant_id, operator_settings={})

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model, key):  # noqa: ANN001
            if key == tenant_id:
                return tenant
            return None

        async def _commit() -> None:
            return None

        async def _refresh(_obj: object) -> None:
            return None

        yield SimpleNamespace(get=_get, commit=_commit, refresh=_refresh)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "tenant_id": tenant_id,
        "tenant_role": "owner",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            "/api/v1/auth/session-policy",
            headers={"Authorization": "Bearer x"},
            json={"access_token_source": "tenant", "access_token_minutes": 30},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["access_token_expire_minutes"] == 30
    assert body["access_token_source"] == "tenant"
    assert tenant.operator_settings["session_policy"]["access_token_minutes"] == 30


@pytest.mark.asyncio
async def test_session_policy_patch_persists_2fa_session_hours(restore_app_overrides: None) -> None:
    tenant_id = uuid.uuid4()
    tenant = SimpleNamespace(id=tenant_id, operator_settings={})

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _get(_model, key):  # noqa: ANN001
            if key == tenant_id:
                return tenant
            return None

        async def _commit() -> None:
            return None

        async def _refresh(_obj: object) -> None:
            return None

        yield SimpleNamespace(get=_get, commit=_commit, refresh=_refresh)

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "tenant_id": tenant_id,
        "tenant_role": "owner",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            "/api/v1/auth/session-policy",
            headers={"Authorization": "Bearer x"},
            json={"dashboard_2fa_session_source": "tenant", "dashboard_2fa_session_max_hours": 4},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["dashboard_2fa_session_max_hours"] == 4
    assert body["dashboard_2fa_session_source"] == "tenant"
    assert tenant.operator_settings["session_policy"]["dashboard_2fa_session_max_hours"] == 4
