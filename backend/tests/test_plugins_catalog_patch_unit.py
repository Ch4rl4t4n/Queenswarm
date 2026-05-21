"""ASGI tests for built-in plugin PATCH persistence."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.application.services import plugin_hub as hub
from app.core.config import settings
from app.main import app
from app.presentation.api.deps import require_subject


@pytest.fixture
def restore_app_overrides() -> None:
    """Clear FastAPI dependency overrides after each test."""

    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def isolate_plugin_state(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Use isolated plugin dir for each API test."""

    state_dir = tmp_path / "plugins"
    state_dir.mkdir()
    monkeypatch.setattr(settings, "plugin_user_dir", str(state_dir), raising=False)
    with hub._lock:
        hub._reload_generation = 0


@pytest.mark.asyncio
async def test_plugins_patch_persists_builtin_toggle(restore_app_overrides: None) -> None:
    app.dependency_overrides[require_subject] = lambda: "dash:operator"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        disabled = await client.patch(
            "/api/v1/plugins/simulation-docker",
            headers={"Authorization": "Bearer test-token"},
            json={"enabled": False},
        )
        assert disabled.status_code == 200
        body = disabled.json()
        assert body["ok"] is True
        assert body["plugin"]["enabled"] is False
        assert body["reload_generation"] >= 1

        listing = await client.get("/api/v1/plugins", headers={"Authorization": "Bearer test-token"})
        assert listing.status_code == 200
        rows = listing.json()["builtin"]
        sim = next(row for row in rows if row["id"] == "simulation-docker")
        assert sim["enabled"] is False
        assert sim["status"] == "inactive"


@pytest.mark.asyncio
async def test_plugins_patch_when_unknown_builtin_returns_404(restore_app_overrides: None) -> None:
    app.dependency_overrides[require_subject] = lambda: "dash:operator"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.patch(
            "/api/v1/plugins/unknown-plugin",
            headers={"Authorization": "Bearer test-token"},
            json={"enabled": True},
        )
    assert res.status_code == 404
