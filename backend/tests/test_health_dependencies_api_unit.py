"""Health dependency endpoint behavior."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.routers import health as health_router


@pytest.mark.asyncio
async def test_health_dependencies_when_ready_returns_200(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _ready_snapshot(*, force_refresh: bool = False) -> tuple[dict[str, object], bool]:
        return {"status": "ready", "cached": not force_refresh, "checks": {}}, True

    monkeypatch.setattr(health_router, "get_readiness_snapshot", _ready_snapshot)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health/dependencies?refresh=true")
    assert res.status_code == 200
    assert res.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_health_dependencies_when_not_ready_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _not_ready_snapshot(*, force_refresh: bool = False) -> tuple[dict[str, object], bool]:
        return {"status": "not_ready", "cached": not force_refresh, "checks": {"postgres": {"ok": False}}}, False

    monkeypatch.setattr(health_router, "get_readiness_snapshot", _not_ready_snapshot)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/health/dependencies")
    assert res.status_code == 503
    assert res.json()["status"] == "not_ready"
