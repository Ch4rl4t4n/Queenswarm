"""ASGI smoke tests for the hive M2M token exchange."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwt as jose_jwt

from app.api.routers.auth import HiveTokenExchangeConfig, hive_token_exchange_config
from app.core.config import settings
from app.main import app


@pytest.fixture
def restore_dependency_overrides() -> None:
    """Ensure FastAPI overrides never leak across cases."""

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_auth_token_exchange_success(restore_dependency_overrides: None) -> None:
    app.dependency_overrides[hive_token_exchange_config] = lambda: HiveTokenExchangeConfig(
        True,
        "worker",
        "x" * 32,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/token",
            auth=("worker", "x" * 32),
            json={"subject": "bee-ci-runner"},
        )
    assert response.status_code == 200
    data = response.json()
    assert data["token_type"] == "bearer"
    assert "access_token" in data
    assert data["expires_in"] >= 60


@pytest.mark.asyncio
async def test_auth_token_exchange_disabled_returns_503(restore_dependency_overrides: None) -> None:
    app.dependency_overrides[hive_token_exchange_config] = lambda: HiveTokenExchangeConfig(False, "", "")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/token",
            auth=("any", "y" * 32),
            json={"subject": "noop"},
        )
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_auth_token_exchange_rejects_bad_secret(restore_dependency_overrides: None) -> None:
    app.dependency_overrides[hive_token_exchange_config] = lambda: HiveTokenExchangeConfig(
        True,
        "worker",
        "x" * 32,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/token",
            auth=("worker", "y" * 32),
            json={"subject": "noop"},
        )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_token_exchange_embeds_scope_claim(restore_dependency_overrides: None) -> None:
    app.dependency_overrides[hive_token_exchange_config] = lambda: HiveTokenExchangeConfig(
        True,
        "worker",
        "x" * 32,
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/auth/token",
            auth=("worker", "x" * 32),
            json={"subject": "bee-ci-runner", "scope": "recipes:write"},
        )
    assert response.status_code == 200
    token = response.json()["access_token"]
    payload = jose_jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    assert payload.get("scope") == "recipes:write"
