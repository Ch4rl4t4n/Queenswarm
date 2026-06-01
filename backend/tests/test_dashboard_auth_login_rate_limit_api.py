"""ASGI tests for dashboard login-specific throttles."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock
import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.application.services.dashboard_crypto import hash_dashboard_password
from app.main import app
from app.presentation.api.deps import get_db
from app.presentation.api.middleware import rate_limit as rate_limit_middleware
from app.presentation.api.routers import dashboard_session as dashboard_session_router


@pytest.fixture
def restore_app_overrides() -> None:
    """Reset dependency overrides between test cases."""

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dashboard_login_when_ip_rate_limited_returns_429(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _scalar(*args, **kwargs):  # noqa: ANN002, ANN003
            del args, kwargs
            return None

        yield SimpleNamespace(scalar=_scalar)

    async def _deny(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        return False

    app.dependency_overrides[get_db] = mock_db
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(rate_limit_middleware, "sliding_window_reserve", AsyncMock(return_value=True))
    monkeypatch.setattr(dashboard_session_router, "sliding_window_reserve", _deny)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@queenswarm.love", "password": "WrongSecret-123"},
        )

    assert response.status_code == 429
    assert response.headers.get("Retry-After") == str(int(settings.rate_limit_login_window_sec))


@pytest.mark.asyncio
async def test_dashboard_login_when_identity_rate_limited_returns_429(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _scalar(*args, **kwargs):  # noqa: ANN002, ANN003
            del args, kwargs
            return None

        yield SimpleNamespace(scalar=_scalar)

    calls = {"count": 0}

    async def _allow_then_deny(*args, **kwargs):  # noqa: ANN002, ANN003
        del args, kwargs
        calls["count"] += 1
        return calls["count"] == 1

    app.dependency_overrides[get_db] = mock_db
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(rate_limit_middleware, "sliding_window_reserve", AsyncMock(return_value=True))
    monkeypatch.setattr(dashboard_session_router, "sliding_window_reserve", _allow_then_deny)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@queenswarm.love", "password": "WrongSecret-123"},
        )

    assert response.status_code == 429
    retry_after = response.headers.get("Retry-After")
    assert retry_after == str(int(max(settings.rate_limit_login_window_sec, settings.rate_limit_login_identity_window_sec)))


@pytest.mark.asyncio
async def test_dashboard_login_identity_bucket_key_is_hashed(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _scalar(*args, **kwargs):  # noqa: ANN002, ANN003
            del args, kwargs
            return None

        yield SimpleNamespace(scalar=_scalar)

    keys: list[str] = []
    calls = {"count": 0}

    async def _capture_then_deny(key: str, **kwargs):  # noqa: ANN003
        del kwargs
        keys.append(key)
        calls["count"] += 1
        return calls["count"] == 1

    app.dependency_overrides[get_db] = mock_db
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(rate_limit_middleware, "sliding_window_reserve", AsyncMock(return_value=True))
    monkeypatch.setattr(dashboard_session_router, "sliding_window_reserve", _capture_then_deny)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@queenswarm.love", "password": "WrongSecret-123"},
        )

    assert response.status_code == 429
    assert any(key.startswith("queenswarm:rl:dashboard_login_identity:hmac-sha256:") for key in keys)
    assert all("admin@queenswarm.love" not in key for key in keys)


@pytest.mark.asyncio
async def test_dashboard_login_success_sets_no_store_headers(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = SimpleNamespace(
        id=uuid.uuid4(),
        email="admin@queenswarm.love",
        is_active=True,
        password_hash=hash_dashboard_password("CorrectSecret-123"),
        totp_secret=None,
        totp_verified_at=None,
    )

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _scalar(*args, **kwargs):  # noqa: ANN002, ANN003
            del args, kwargs
            return user

        yield SimpleNamespace(scalar=_scalar)

    app.dependency_overrides[get_db] = mock_db
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    monkeypatch.setattr(
        dashboard_session_router,
        "_issue_pair",
        AsyncMock(
            return_value={
                "access_token": "tok",
                "refresh_token": "ref",
                "expires_in": 1800,
                "token_type": "bearer",
            }
        ),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@queenswarm.love", "password": "CorrectSecret-123"},
        )

    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("Pragma") == "no-cache"
    assert response.headers.get("Expires") == "0"


@pytest.mark.asyncio
async def test_dashboard_login_when_totp_required_sets_no_store_headers(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = SimpleNamespace(
        id=uuid.uuid4(),
        email="admin@queenswarm.love",
        is_active=True,
        password_hash=hash_dashboard_password("CorrectSecret-123"),
        totp_secret="totp-secret",
        totp_verified_at=object(),
    )

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        async def _scalar(*args, **kwargs):  # noqa: ANN002, ANN003
            del args, kwargs
            return user

        yield SimpleNamespace(scalar=_scalar)

    app.dependency_overrides[get_db] = mock_db
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    monkeypatch.setattr(settings, "enable_2fa", True)
    monkeypatch.setattr(
        dashboard_session_router,
        "create_pre_2fa_token",
        lambda **_kwargs: ("pre-2fa-token", 300),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            json={"email": "admin@queenswarm.love", "password": "CorrectSecret-123"},
        )

    assert response.status_code == 200
    assert response.json().get("requires_totp") is True
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("Pragma") == "no-cache"
    assert response.headers.get("Expires") == "0"


@pytest.mark.asyncio
async def test_dashboard_verify_2fa_success_sets_no_store_headers(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = SimpleNamespace(
        id=uuid.uuid4(),
        email="admin@queenswarm.love",
        is_active=True,
        is_admin=False,
        totp_secret="totp-secret",
        totp_verified_at=None,
        notification_prefs={},
    )

    class _FakeDb:
        async def get(self, *_args, **_kwargs):
            return user

        async def commit(self) -> None:
            return None

        async def refresh(self, _obj) -> None:  # noqa: ANN001
            return None

    async def mock_db() -> AsyncIterator[_FakeDb]:
        yield _FakeDb()

    app.dependency_overrides[get_db] = mock_db
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    monkeypatch.setattr(
        dashboard_session_router,
        "decode_jwt_optional_typ",
        lambda _token: {"typ": "pre_2fa", "sub": str(user.id)},
    )
    monkeypatch.setattr(dashboard_session_router, "totp_verify", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        dashboard_session_router,
        "_issue_pair",
        AsyncMock(
            return_value={
                "access_token": "tok",
                "refresh_token": "ref",
                "expires_in": 1800,
                "token_type": "bearer",
            }
        ),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/verify-2fa",
            json={"pre_auth_token": "pre-2fa-token", "totp_code": "123456"},
        )

    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("Pragma") == "no-cache"
    assert response.headers.get("Expires") == "0"


@pytest.mark.asyncio
async def test_dashboard_refresh_success_sets_no_store_headers(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = SimpleNamespace(
        id=uuid.uuid4(),
        email="admin@queenswarm.love",
        is_active=True,
        is_admin=False,
    )

    class _FakeDb:
        async def get(self, *_args, **_kwargs):
            return user

    async def mock_db() -> AsyncIterator[_FakeDb]:
        yield _FakeDb()

    app.dependency_overrides[get_db] = mock_db
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    monkeypatch.setattr(
        dashboard_session_router,
        "fetch_dashboard_refresh_session",
        AsyncMock(return_value=(str(user.id), int(datetime.now(tz=UTC).timestamp()))),
    )
    monkeypatch.setattr(
        dashboard_session_router,
        "revoke_dashboard_refresh",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        dashboard_session_router,
        "_issue_pair",
        AsyncMock(
            return_value={
                "access_token": "tok",
                "refresh_token": "ref",
                "expires_in": 1800,
                "token_type": "bearer",
            }
        ),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "refresh-token-1234567890"},
        )

    assert response.status_code == 200
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("Pragma") == "no-cache"
    assert response.headers.get("Expires") == "0"


@pytest.mark.asyncio
async def test_dashboard_refresh_rejects_expired_2fa_session(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    user = SimpleNamespace(
        id=uuid.uuid4(),
        email="admin@queenswarm.love",
        is_active=True,
        is_admin=False,
        totp_secret="SECRET",
        totp_verified_at=datetime.now(tz=UTC),
        active_tenant_id=None,
    )

    class _FakeDb:
        async def get(self, *_args, **_kwargs):
            return user

    async def mock_db() -> AsyncIterator[_FakeDb]:
        yield _FakeDb()

    app.dependency_overrides[get_db] = mock_db
    monkeypatch.setattr(settings, "rate_limit_enabled", False)
    monkeypatch.setattr(settings, "enable_2fa", True)
    monkeypatch.setattr(settings, "dashboard_2fa_session_max_hours", 24)
    stale_auth_at = int(datetime.now(tz=UTC).timestamp()) - (25 * 3600)
    monkeypatch.setattr(
        dashboard_session_router,
        "fetch_dashboard_refresh_session",
        AsyncMock(return_value=(str(user.id), stale_auth_at)),
    )
    monkeypatch.setattr(
        dashboard_session_router,
        "revoke_dashboard_refresh",
        AsyncMock(return_value=None),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": "refresh-token-1234567890"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "2FA session expired; sign in again."
