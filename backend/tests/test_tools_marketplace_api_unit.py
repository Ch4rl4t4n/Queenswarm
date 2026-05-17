"""Unit API coverage for tools marketplace and dynamic registry routes."""

from __future__ import annotations

import uuid
from collections.abc import Generator
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import (
    require_dashboard_session,
    require_dashboard_user_with_tenant_role,
    require_subject,
)
from app.presentation.api.routers import tools_marketplace


@pytest.fixture
def tools_auth_fixture() -> Generator[None, None, None]:
    """Inject deterministic dashboard JWT subject for tools routes."""

    actor = uuid.uuid4()
    app.dependency_overrides[require_subject] = lambda: f"dash:{actor}"
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": f"dash:{actor}"}
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "tenant_role": "owner",
        "permissions": ["connectors:view", "connectors:edit"],
    }
    try:
        yield
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_tools_registry_and_marketplace_catalog_routes(
    monkeypatch: pytest.MonkeyPatch,
    tools_auth_fixture: None,
) -> None:
    """Registry and marketplace catalog endpoints return projected payloads."""

    async def _fake_registry(*_args: object, **_kwargs: object) -> list[dict[str, object]]:
        return [
            {
                "connector_slug": "notion",
                "tool_name": "search",
                "description": "Search Notion docs",
                "score": 0.9,
            },
        ]

    async def _fake_catalog(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "phase3_templates": [{"id": "notion_api", "title": "Notion API", "installed": False}],
            "plugins_builtin": [],
            "plugins_user": [],
        }

    monkeypatch.setattr(tools_marketplace, "tool_registry_snapshot", _fake_registry)
    monkeypatch.setattr(tools_marketplace, "marketplace_catalog", _fake_catalog)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reg = await client.get("/api/v1/tools/registry?manager_slug=research_intelligence")
        cat = await client.get("/api/v1/tools/marketplace/catalog")

    assert reg.status_code == 200
    assert reg.json()["items"][0]["connector_slug"] == "notion"
    assert cat.status_code == 200
    assert cat.json()["phase3_templates"][0]["id"] == "notion_api"


@pytest.mark.asyncio
async def test_tools_marketplace_install_route(monkeypatch: pytest.MonkeyPatch, tools_auth_fixture: None) -> None:
    """Install endpoint returns created connector projection."""

    async def _fake_install(*_args: object, **_kwargs: object) -> tuple[str, object]:
        connector = SimpleNamespace(slug="notion", model_dump=lambda **_kw: {"slug": "notion"})
        return "installed", connector

    class _DummySvc:
        async def fetch_by_slug(self, *_args: object, **_kwargs: object) -> object:
            return None

    monkeypatch.setattr(tools_marketplace, "install_marketplace_entry", _fake_install)
    monkeypatch.setattr(tools_marketplace, "DynamicConnectorService", _DummySvc)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/tools/marketplace/install",
            json={"source": "phase3_template", "entry_id": "notion_api"},
        )

    assert resp.status_code == 200
    assert resp.json()["status"] == "installed"
    assert resp.json()["connector"]["slug"] == "notion"
