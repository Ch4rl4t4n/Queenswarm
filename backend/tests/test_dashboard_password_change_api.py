"""ASGI tests for dashboard self-service password rotation."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.presentation.api.deps import get_db, require_dashboard_session
from app.application.services.dashboard_crypto import hash_dashboard_password, verify_dashboard_password
from app.infrastructure.persistence.models.dashboard_user import DashboardUser
from app.main import app


@pytest.fixture
def restore_app_overrides() -> None:
    """Ensure FastAPI dependency overrides are reset after each case."""

    yield
    app.dependency_overrides.clear()


class _FakeSession:
    """Minimal async session for password-rotation route tests."""

    def __init__(self, user: DashboardUser) -> None:
        self._user = user
        self.commits = 0
        self.rollbacks = 0
        self.refreshes = 0

    async def get(self, _model: object, identity: uuid.UUID) -> DashboardUser | None:
        return self._user if identity == self._user.id else None

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def refresh(self, _entity: object) -> None:
        self.refreshes += 1


def _make_user(*, plain_password: str) -> DashboardUser:
    user_id = uuid.uuid4()
    return DashboardUser(
        id=user_id,
        email="admin@queenswarm.love",
        password_hash=hash_dashboard_password(plain_password),
        display_name="Hive Admin",
        timezone=None,
        notification_prefs={},
        totp_secret=None,
        totp_verified_at=None,
        totp_required=False,
        is_admin=True,
        is_active=True,
    )


@pytest.mark.asyncio
async def test_change_password_when_current_matches_updates_hash(restore_app_overrides: None) -> None:
    """Route stores a new digest after validating the current password."""

    current = "OldSecret-123"
    fresh = "NewSecret-789"
    user = _make_user(plain_password=current)
    fake_db = _FakeSession(user)

    async def mock_db() -> AsyncIterator[_FakeSession]:
        yield fake_db

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {
        "sub": f"dash:{user.id}",
        "typ": "dashboard_access",
        "scope": "dash:read dash:operator",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/me/password",
            json={"current_password": current, "new_password": fresh},
            headers={"Authorization": "Bearer dummy"},
        )

    assert response.status_code == 200
    assert response.json() == {"ok": True}
    assert fake_db.commits == 1
    assert fake_db.rollbacks == 0
    assert fake_db.refreshes == 1
    assert verify_dashboard_password(fresh, user.password_hash)
    assert not verify_dashboard_password(current, user.password_hash)


@pytest.mark.asyncio
async def test_change_password_when_current_invalid_returns_401(restore_app_overrides: None) -> None:
    """Route rejects rotation if current password does not verify."""

    user = _make_user(plain_password="OldSecret-123")
    old_hash = user.password_hash
    fake_db = _FakeSession(user)

    async def mock_db() -> AsyncIterator[_FakeSession]:
        yield fake_db

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {
        "sub": f"dash:{user.id}",
        "typ": "dashboard_access",
        "scope": "dash:read dash:operator",
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/me/password",
            json={"current_password": "WrongSecret-123", "new_password": "NewSecret-789"},
            headers={"Authorization": "Bearer dummy"},
        )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid current password."
    assert fake_db.commits == 0
    assert fake_db.rollbacks == 0
    assert fake_db.refreshes == 0
    assert user.password_hash == old_hash
