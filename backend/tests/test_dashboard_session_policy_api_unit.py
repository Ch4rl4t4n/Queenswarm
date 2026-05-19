"""ASGI tests for read-only dashboard session policy."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app
from app.presentation.api.deps import require_dashboard_session


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

    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": "dash:00000000-0000-4000-8000-000000000001"}

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/session-policy")

    assert response.status_code == 200
    payload = response.json()
    assert payload["access_token_expire_minutes"] == 12
    assert payload["refresh_token_expire_days"] == 9
    assert payload["rate_limit_requests"] == 240
    assert payload["rate_limit_window_sec"] == 60.0
    assert payload["oauth_state_ttl_sec"] == 600
    assert payload["two_fa_enabled"] is True
    assert payload["editable"] is False
