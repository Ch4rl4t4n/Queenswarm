"""ASGI smoke tests for MCP Ops Studio snapshot endpoint."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import require_dashboard_user_with_tenant_role


@pytest.fixture
def restore_overrides() -> None:
    """Reset FastAPI dependency overrides between test cases."""

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_mcp_ops_studio_snapshot_returns_read_only_payload(restore_overrides: None, monkeypatch) -> None:
    """Snapshot endpoint returns catalog/install/health read model."""

    monkeypatch.setattr(
        "app.application.services.mcp_ops_studio_snapshot.settings.mcp_ops_studio_live_snapshot_enabled",
        False,
    )

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": uuid.uuid4(),
        "tenant_role": "owner",
        "permissions": ["*"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/operator/apps-tools/mcp-ops-studio/snapshot",
            headers={"Authorization": "Bearer x"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source"] == "read_only_mock"
    assert isinstance(payload.get("generated_at"), str)
    assert payload["generated_at"]
    assert any(row["provider"] == "GitHub MCP" for row in payload["catalog"])
    assert any(row["provider"] == "Linear MCP" for row in payload["install"])
    assert payload["health"] == []
    assert payload["tool_gaps"] == []


@pytest.mark.asyncio
async def test_mcp_ops_studio_snapshot_requires_tenant_context(restore_overrides: None) -> None:
    """Snapshot endpoint returns 403 when tenant context is missing."""

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "user": SimpleNamespace(id=uuid.uuid4()),
        "tenant_id": None,
        "tenant_role": "owner",
        "permissions": ["*"],
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/operator/apps-tools/mcp-ops-studio/snapshot",
            headers={"Authorization": "Bearer x"},
        )

    assert response.status_code == 403
    assert response.json()["detail"] == "Tenant context missing."
