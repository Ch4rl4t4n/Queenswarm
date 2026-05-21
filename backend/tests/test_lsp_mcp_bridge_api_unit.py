"""API coverage for LSP bridge harness routes."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import require_dashboard_user_with_tenant_role, require_subject
from app.presentation.api.routers import harness as harness_router


@pytest.fixture
def lsp_bridge_auth_fixture() -> Generator[None, None, None]:
    """Tenant-scoped dashboard principal."""

    actor = uuid.uuid4()
    tenant = uuid.uuid4()
    app.dependency_overrides[require_subject] = lambda: f"dash:{actor}"
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "tenant_id": tenant,
        "tenant_role": "owner",
        "permissions": [],
        "user": MagicMock(),
    }
    try:
        yield
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_lsp_bridge_resolve_route(
    monkeypatch: pytest.MonkeyPatch,
    lsp_bridge_auth_fixture: None,
) -> None:
    """Resolve endpoint returns symbol matches."""

    def _fake_invoke(_tool: str, _args: dict[str, object]) -> dict[str, object]:
        return {
            "tool": "resolve_symbol",
            "query": "HarnessSnapshot",
            "matches": [{"name": "HarnessSnapshot", "kind": "class", "path": "backend/app/x.py", "line": 1}],
        }

    monkeypatch.setattr(harness_router, "invoke_lsp_tool", _fake_invoke)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/harness/lsp-bridge/resolve",
            json={"query": "HarnessSnapshot"},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["matches"][0]["name"] == "HarnessSnapshot"


@pytest.mark.asyncio
async def test_lsp_bridge_status_route(
    monkeypatch: pytest.MonkeyPatch,
    lsp_bridge_auth_fixture: None,
) -> None:
    """Status endpoint returns deployment metadata."""

    monkeypatch.setattr(
        harness_router,
        "bridge_status",
        lambda: {"enabled": False, "connector_slug": "queenswarm_lsp", "tools": ["resolve_symbol"]},
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/harness/lsp-bridge/status")

    assert resp.status_code == 200
    assert resp.json()["connector_slug"] == "queenswarm_lsp"
