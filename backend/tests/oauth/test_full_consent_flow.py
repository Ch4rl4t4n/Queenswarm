"""OAuth consent flow regression tests (mocked Redis + HTTP)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from redis.exceptions import RedisError

from app.application.services.oauth_consent.service import complete_oauth_callback, start_oauth_authorization
from app.core.config import get_settings
from app.core.jwt_tokens import create_dashboard_access_token
from app.main import app
from app.presentation.api.deps import get_db


def _oauth_callback_settings() -> SimpleNamespace:
    return SimpleNamespace(
        oauth_callback_rate_per_ip=30,
        oauth_callback_rate_window_sec=60.0,
        oauth_public_origin="http://localhost:3000",
    )


@pytest.fixture
def restore_app_overrides() -> None:
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_oauth_providers_requires_dashboard_session(restore_app_overrides: None) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/oauth/providers")
    assert resp.status_code in {401, 403}


@pytest.mark.asyncio
async def test_oauth_start_unknown_provider_returns_400(restore_app_overrides: None) -> None:
    get_settings.cache_clear()

    uid = uuid.uuid4()
    token, _ = create_dashboard_access_token(user_id=uid, email="oauth-pytest@queenswarm.test", scopes="dash:standard")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/oauth/start",
            headers={"Authorization": f"Bearer {token}"},
            json={"provider": "unknown_vendor"},
        )
    assert resp.status_code == 400
    assert resp.headers.get("Cache-Control") == "no-store"
    assert resp.headers.get("Pragma") == "no-cache"
    assert resp.headers.get("Expires") == "0"


@pytest.mark.asyncio
async def test_oauth_start_google_returns_authorize_url(monkeypatch: pytest.MonkeyPatch, restore_app_overrides: None) -> None:
    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_ID", "unit-google-id")
    monkeypatch.setenv("OAUTH_GOOGLE_CLIENT_SECRET", "unit-google-secret")
    get_settings.cache_clear()

    stored: dict[str, object] = {}

    async def fake_set_json(key: str, value: object, ttl: int | None = None) -> None:  # noqa: ARG001
        stored["key"] = key
        stored["value"] = value

    monkeypatch.setattr("app.application.services.oauth_consent.service.set_json", fake_set_json)

    uid = uuid.uuid4()
    token, _ = create_dashboard_access_token(user_id=uid, email="oauth-pytest@queenswarm.test", scopes="dash:standard")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/oauth/start",
            headers={"Authorization": f"Bearer {token}"},
            json={"provider": "google_gmail"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert "authorization_url" in body
    assert "accounts.google.com" in body["authorization_url"]
    assert "code_challenge=" in body["authorization_url"]
    assert isinstance(stored.get("value"), dict)


@pytest.mark.asyncio
async def test_oauth_start_sets_no_store_headers(
    monkeypatch: pytest.MonkeyPatch,
    restore_app_overrides: None,
) -> None:
    monkeypatch.setattr(
        "app.presentation.api.routers.oauth_consent.start_oauth_authorization",
        AsyncMock(return_value={"authorization_url": "https://example.com/auth", "state": "opaque-state"}),
    )
    uid = uuid.uuid4()
    token, _ = create_dashboard_access_token(user_id=uid, email="oauth-pytest@queenswarm.test", scopes="dash:standard")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/oauth/start",
            headers={"Authorization": f"Bearer {token}"},
            json={"provider": "google_gmail"},
        )

    assert resp.status_code == 200
    assert resp.headers.get("Cache-Control") == "no-store"
    assert resp.headers.get("Pragma") == "no-cache"
    assert resp.headers.get("Expires") == "0"


@pytest.mark.asyncio
async def test_oauth_callback_sets_no_store_headers(
    monkeypatch: pytest.MonkeyPatch,
    restore_app_overrides: None,
) -> None:
    async def mock_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = mock_db
    monkeypatch.setattr(
        "app.presentation.api.routers.oauth_consent.complete_oauth_callback",
        AsyncMock(return_value="http://localhost:3000/connectors?oauth=ok"),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/oauth/callback?code=abc&state=def")

    assert resp.status_code == 200
    assert resp.json().get("redirect_url") == "http://localhost:3000/connectors?oauth=ok"
    assert resp.headers.get("Cache-Control") == "no-store"
    assert resp.headers.get("Pragma") == "no-cache"
    assert resp.headers.get("Expires") == "0"


@pytest.mark.asyncio
async def test_complete_oauth_callback_rate_limited_returns_error_redirect(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_reserve(*args: object, **kwargs: object) -> bool:  # noqa: ARG002
        return False

    monkeypatch.setattr("app.application.services.oauth_consent.service.sliding_window_reserve", fake_reserve)
    monkeypatch.setattr("app.application.services.oauth_consent.service.mirror_external_audit_to_vault", AsyncMock())

    db = AsyncMock()
    settings = _oauth_callback_settings()
    url = await complete_oauth_callback(
        db,
        settings=settings,
        client_host="198.51.100.7",
        code="abc",
        state="def",
        oauth_error=None,
    )
    assert "oauth=error" in url
    assert "rate_limited" in url


@pytest.mark.asyncio
async def test_complete_oauth_callback_when_rate_limit_redis_fails_degrades_open(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_reserve(*args: object, **kwargs: object) -> bool:  # noqa: ARG002
        raise RedisError("redis unavailable")

    monkeypatch.setattr("app.application.services.oauth_consent.service.sliding_window_reserve", fake_reserve)
    monkeypatch.setattr("app.application.services.oauth_consent.service.mirror_external_audit_to_vault", AsyncMock())

    db = AsyncMock()
    settings = _oauth_callback_settings()
    url = await complete_oauth_callback(
        db,
        settings=settings,
        client_host="198.51.100.7",
        code="abc",
        state="def",
        oauth_error="access_denied",
    )
    assert "oauth=error" in url
    assert "reason=access_denied" in url
    assert "rate_limited" not in url


@pytest.mark.asyncio
async def test_oauth_providers_returns_registry_when_authenticated(restore_app_overrides: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.presentation.api.routers.oauth_consent.oauth_catalog_snapshot",
        lambda _settings: {
            "providers": [{"provider": "google_gmail", "configured": True}],
            "redirect_uri": "http://localhost:3000/api/auth/callback/connect",
        },
    )

    uid = uuid.uuid4()
    token, _ = create_dashboard_access_token(user_id=uid, email="oauth-list@queenswarm.test", scopes="dash:standard")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/oauth/providers", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert "providers" in body
    assert "redirect_uri" in body
    assert isinstance(body["providers"], list)
    assert resp.headers.get("Cache-Control") == "no-store"
    assert resp.headers.get("Pragma") == "no-cache"
    assert resp.headers.get("Expires") == "0"


@pytest.mark.asyncio
async def test_start_oauth_authorization_requires_client_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OAUTH_STRIPE_CLIENT_ID", "")
    monkeypatch.setenv("OAUTH_STRIPE_CLIENT_SECRET", "")
    get_settings.cache_clear()

    uid = uuid.uuid4()
    settings = get_settings()
    sub = f"dash:{uid}"
    with pytest.raises(ValueError, match="oauth_client_not_configured"):
        await start_oauth_authorization(
            settings=settings,
            provider_key="stripe_billing",
            dashboard_sub=sub,
        )
