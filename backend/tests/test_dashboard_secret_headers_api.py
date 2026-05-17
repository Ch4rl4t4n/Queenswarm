"""ASGI tests for no-store headers on secret-bearing dashboard routes."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.application.services.dashboard_crypto import hash_dashboard_password
from app.core.config import settings
from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_session
from app.presentation.api.routers import dashboard_session as dashboard_session_router


@pytest.fixture
def restore_app_overrides() -> None:
    """Reset dependency overrides between tests."""

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_profile_totp_provision_sets_no_store_headers(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = SimpleNamespace(
        id=uuid.uuid4(),
        email="admin@queenswarm.love",
        password_hash=hash_dashboard_password("CorrectSecret-123"),
        notification_prefs={},
        totp_secret=None,
        totp_verified_at=None,
        totp_required=False,
    )

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace(
            commit=AsyncMock(return_value=None),
            refresh=AsyncMock(return_value=None),
        )

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": f"dash:{user.id}", "scope": "dash:read"}
    monkeypatch.setattr(settings, "security_2fa_advanced_enabled", True)
    monkeypatch.setattr(dashboard_session_router, "_current_dashboard_user", AsyncMock(return_value=user))
    monkeypatch.setattr(dashboard_session_router, "mint_totp_secret", lambda: "JBSWY3DPEHPK3PXP")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/profile/totp/provision",
            json={"password": "CorrectSecret-123"},
            headers={"Authorization": "Bearer dummy"},
        )

    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("Pragma") == "no-cache"
    assert response.headers.get("Expires") == "0"


@pytest.mark.asyncio
async def test_profile_totp_backup_regenerate_sets_no_store_headers(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = SimpleNamespace(
        id=uuid.uuid4(),
        email="admin@queenswarm.love",
        password_hash=hash_dashboard_password("CorrectSecret-123"),
        notification_prefs={},
        totp_secret="JBSWY3DPEHPK3PXP",
        totp_verified_at=datetime.now(tz=UTC),
        totp_required=True,
    )

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace(
            commit=AsyncMock(return_value=None),
            refresh=AsyncMock(return_value=None),
        )

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": f"dash:{user.id}", "scope": "dash:read"}
    monkeypatch.setattr(settings, "security_2fa_advanced_enabled", True)
    monkeypatch.setattr(dashboard_session_router, "_current_dashboard_user", AsyncMock(return_value=user))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/profile/totp/backup-codes/regenerate",
            json={"password": "CorrectSecret-123"},
            headers={"Authorization": "Bearer dummy"},
        )

    assert response.status_code == 200
    assert "codes" in response.json()
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("Pragma") == "no-cache"
    assert response.headers.get("Expires") == "0"


@pytest.mark.asyncio
async def test_dashboard_api_key_mint_sets_no_store_headers(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = SimpleNamespace(id=uuid.uuid4())
    row = SimpleNamespace(
        id=uuid.uuid4(),
        source_name="automation",
        label="ci",
        created_at=datetime.now(tz=UTC),
        last_used_at=None,
        revoked_at=None,
    )

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace(
            commit=AsyncMock(return_value=None),
            refresh=AsyncMock(return_value=None),
        )

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": f"dash:{user.id}", "scope": "dash:read"}
    monkeypatch.setattr(settings, "api_key_management_enabled", True)
    monkeypatch.setattr(dashboard_session_router, "_current_dashboard_user", AsyncMock(return_value=user))
    monkeypatch.setattr(dashboard_session_router, "create_dashboard_api_key", AsyncMock(return_value=(row, "qs_api_secret")))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/api-keys",
            json={"source_name": "automation", "label": "ci"},
            headers={"Authorization": "Bearer dummy"},
        )

    assert response.status_code == 200
    assert response.json().get("plaintext") == "qs_api_secret"
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("Pragma") == "no-cache"
    assert response.headers.get("Expires") == "0"


@pytest.mark.asyncio
async def test_profile_totp_confirm_sets_no_store_headers(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = SimpleNamespace(
        id=uuid.uuid4(),
        email="admin@queenswarm.love",
        password_hash=hash_dashboard_password("CorrectSecret-123"),
        notification_prefs={},
        totp_secret="JBSWY3DPEHPK3PXP",
        totp_verified_at=None,
        totp_required=True,
    )

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace(
            commit=AsyncMock(return_value=None),
            refresh=AsyncMock(return_value=None),
        )

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": f"dash:{user.id}", "scope": "dash:read"}
    monkeypatch.setattr(settings, "security_2fa_advanced_enabled", True)
    monkeypatch.setattr(dashboard_session_router, "_current_dashboard_user", AsyncMock(return_value=user))
    monkeypatch.setattr(dashboard_session_router, "totp_verify", lambda *args, **kwargs: True)
    monkeypatch.setattr(
        dashboard_session_router,
        "mint_plain_backup_codes",
        lambda: ["bee-alpha", "bee-bravo", "bee-charlie", "bee-delta", "bee-echo", "bee-foxtrot", "bee-golf", "bee-hotel"],
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/profile/totp/confirm",
            json={"code": "123456"},
            headers={"Authorization": "Bearer dummy"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("verified") is True
    assert isinstance(payload.get("backup_codes"), list)
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("Pragma") == "no-cache"
    assert response.headers.get("Expires") == "0"


@pytest.mark.asyncio
async def test_setup_totp_sets_no_store_headers(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = SimpleNamespace(
        id=uuid.uuid4(),
        email="admin@queenswarm.love",
        totp_secret=None,
        totp_required=False,
    )

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace(
            commit=AsyncMock(return_value=None),
            refresh=AsyncMock(return_value=None),
        )

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {
        "sub": f"dash:{user.id}",
        "scope": "dash:admin dash:read",
    }
    monkeypatch.setattr(settings, "security_2fa_advanced_enabled", True)
    monkeypatch.setattr(dashboard_session_router, "_current_dashboard_user", AsyncMock(return_value=user))
    monkeypatch.setattr(dashboard_session_router, "mint_totp_secret", lambda: "JBSWY3DPEHPK3PXP")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/2fa/setup",
            headers={"Authorization": "Bearer dummy"},
        )

    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("Pragma") == "no-cache"
    assert response.headers.get("Expires") == "0"
