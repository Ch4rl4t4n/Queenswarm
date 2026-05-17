"""ASGI tests for global security no-store middleware behavior."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import settings
from app.main import app


@pytest.mark.asyncio
async def test_security_headers_middleware_when_oauth_requires_auth_sets_no_store() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/oauth/providers")

    assert response.status_code in {401, 403}
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("Pragma") == "no-cache"
    assert response.headers.get("Expires") == "0"
    assert response.headers.get("Content-Security-Policy") is not None
    assert response.headers.get("X-Content-Type-Options") == "nosniff"


@pytest.mark.asyncio
async def test_security_headers_middleware_when_auth_requires_auth_sets_no_store() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/auth/me")

    assert response.status_code in {401, 403}
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("Pragma") == "no-cache"
    assert response.headers.get("Expires") == "0"
    assert response.headers.get("Content-Security-Policy") is not None


@pytest.mark.asyncio
async def test_security_headers_middleware_when_connectors_oauth_requires_auth_sets_no_store() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/connectors/oauth/token",
            json={"grant_type": "refresh_token", "connector_slug": "gmail"},
        )

    assert response.status_code in {401, 403}
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("Pragma") == "no-cache"
    assert response.headers.get("Expires") == "0"


@pytest.mark.asyncio
async def test_security_headers_middleware_does_not_force_no_store_on_health() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code in {200, 503}
    assert response.headers.get("Cache-Control") != "no-store"
    assert response.headers.get("Content-Security-Policy") is not None


@pytest.mark.asyncio
async def test_security_headers_middleware_does_not_force_no_store_on_connectors_catalog() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/connectors/catalog")

    assert response.status_code in {401, 403}
    assert response.headers.get("Cache-Control") != "no-store"


@pytest.mark.asyncio
async def test_security_headers_middleware_when_prod_mode_and_bad_origin_blocks_mutating_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "production_security_mode", True)
    monkeypatch.setattr(settings, "cors_origins", ["https://queenswarm.love"])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/login",
            headers={"Origin": "https://evil.example"},
            json={"email": "test@queenswarm.love", "password": "WrongPassword-123"},
        )

    assert response.status_code == 403
    assert response.json().get("detail") == "Request origin is not allowed."
    assert response.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains; preload"
