"""ASGI tests for connectors OAuth refresh response headers."""

from __future__ import annotations

from collections.abc import AsyncIterator
from types import SimpleNamespace
import uuid
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.infrastructure.connectors.base import ConnectorAuthEnvelope
from app.infrastructure.connectors.secure_vault import CredentialPayload
from app.main import app
from app.presentation.api.deps import get_db, require_dashboard_session, require_dashboard_user_with_tenant_role
from app.presentation.api.routers import connectors as connectors_router


@pytest.fixture
def restore_app_overrides() -> None:
    """Reset FastAPI dependency overrides after each case."""

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": uuid.uuid4(),
        "tenant_role": "owner",
        "permissions": ["*"],
        "membership": SimpleNamespace(role="owner"),
        "session": {"sub": "dash:test"},
    }
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_connectors_oauth_refresh_sets_no_store_headers(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uid = uuid.uuid4()

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {
        "sub": f"dash:{uid}",
        "typ": "dashboard_access",
        "scope": "dash:read",
    }

    monkey_envelope = ConnectorAuthEnvelope(
        kind="oauth2",
        oauth2_access_token="old-token",
        oauth2_refresh_token="refresh-token",
        oauth2_token_endpoint="https://issuer.example.com/token",
        oauth2_client_id="client-id",
        oauth2_client_secret="client-secret",
    )
    refreshed_payload = CredentialPayload(
        kind="oauth2",
        oauth2_access_token="new-token",
        oauth2_refresh_token="refresh-token",
        oauth2_token_endpoint="https://issuer.example.com/token",
        oauth2_client_id="client-id",
        oauth2_client_secret="client-secret",
        api_key=None,
        scopes=(),
    )

    monkeypatch.setattr(connectors_router, "vault_load_envelope", AsyncMock(return_value=monkey_envelope))
    monkeypatch.setattr(
        connectors_router,
        "exchange_refresh_token",
        AsyncMock(
            return_value=(
                refreshed_payload,
                {
                    "access_token": "new-token",
                    "refresh_token": "new-refresh-token",
                    "token_type": "Bearer",
                    "expires_in": 3600,
                    "google_access_token": "provider-access-token",
                    "accessToken": "camel-token",
                    "id-token": "kebab-id-token",
                    "metadata": {
                        "id_token": "jwt-token",
                        "vendorClientSecret": "vendor-secret",
                        "clientSecret": "camel-secret",
                        "nested": {
                            "client_secret": "dont-leak",
                            "region": "eu",
                        },
                    },
                    "rotations": [
                        {"refresh_token": "rotate-1", "status": "ok"},
                        {"id_token": "rotate-id", "status": "ok"},
                    ],
                },
            )
        ),
    )
    monkeypatch.setattr(connectors_router, "vault_upsert_credential", AsyncMock(return_value=None))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/connectors/oauth/token",
            json={"grant_type": "refresh_token", "connector_slug": "gmail"},
            headers={"Authorization": "Bearer dummy"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload.get("ok") is True
    assert payload.get("token_type") == "Bearer"
    assert payload.get("access_token") is None
    assert isinstance(payload.get("raw"), dict)
    assert payload["raw"].get("token_type") == "Bearer"
    assert payload["raw"].get("expires_in") == 3600
    assert "access_token" not in payload["raw"]
    assert "google_access_token" not in payload["raw"]
    assert "accessToken" not in payload["raw"]
    assert "id-token" not in payload["raw"]
    assert "refresh_token" not in payload["raw"]
    assert payload["raw"]["metadata"].get("id_token") is None
    assert payload["raw"]["metadata"].get("vendorClientSecret") is None
    assert payload["raw"]["metadata"].get("clientSecret") is None
    assert payload["raw"]["metadata"]["nested"].get("client_secret") is None
    assert payload["raw"]["metadata"]["nested"].get("region") == "eu"
    assert payload["raw"]["rotations"][0].get("refresh_token") is None
    assert payload["raw"]["rotations"][0].get("status") == "ok"
    assert payload["raw"]["rotations"][1].get("id_token") is None
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("Pragma") == "no-cache"
    assert response.headers.get("Expires") == "0"


@pytest.mark.asyncio
async def test_connectors_oauth_refresh_error_sets_no_store_headers(
    restore_app_overrides: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    uid = uuid.uuid4()

    async def mock_db() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace()

    app.dependency_overrides[get_db] = mock_db
    app.dependency_overrides[require_dashboard_session] = lambda: {
        "sub": f"dash:{uid}",
        "typ": "dashboard_access",
        "scope": "dash:read",
    }
    monkeypatch.setattr(connectors_router, "vault_load_envelope", AsyncMock(return_value=None))

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/connectors/oauth/token",
            json={"grant_type": "refresh_token", "connector_slug": "gmail"},
            headers={"Authorization": "Bearer dummy"},
        )

    assert response.status_code == 404
    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("Pragma") == "no-cache"
    assert response.headers.get("Expires") == "0"
