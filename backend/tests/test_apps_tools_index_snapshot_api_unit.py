"""ASGI smoke tests for Apps & Tools index/policy routes."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import require_dashboard_user_with_tenant_role


@pytest.fixture
def restore_overrides() -> None:
    """Reset FastAPI dependency overrides between test cases."""

    yield
    app.dependency_overrides.clear()


def _owner_principal() -> dict[str, object]:
    """Build owner principal override for operator API calls."""

    return {
        "user": type("U", (), {"id": uuid.uuid4()})(),
        "tenant_id": uuid.uuid4(),
        "tenant_role": "owner",
        "permissions": ["*"],
    }


@pytest.mark.asyncio
async def test_module_policy_pack_detail_supports_mcp_ops_studio(restore_overrides: None) -> None:
    """Policy detail route returns MCP Ops Studio policy payload."""

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/operator/module-policy-packs/mcp_ops_studio",
            headers={"Authorization": "Bearer x"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["module_key"] == "mcp_ops_studio"
    assert payload["requires_approval"] is True


@pytest.mark.asyncio
async def test_apps_tools_index_snapshot_exposes_mcp_and_omni_publish_contract_drafts(
    restore_overrides: None,
) -> None:
    """Apps & Tools index route exposes E36 capability draft contracts."""

    app.dependency_overrides[require_dashboard_user_with_tenant_role] = _owner_principal

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/operator/apps-tools-index?include_disabled=true",
            headers={"Authorization": "Bearer x"},
        )

    assert response.status_code == 200
    payload = response.json()
    workspace_keys = {row["module_key"] for row in payload["workspaces"]}
    capability_keys = {row["capability_key"] for row in payload["capabilities"]}

    assert "mcp_ops_studio" in workspace_keys
    assert "apps.mcp.catalog.discover.v1" in capability_keys
    assert "apps.marketing.omni_publish.compose.v1" in capability_keys
