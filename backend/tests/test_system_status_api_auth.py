"""Auth + smoke tests for system status routes."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import dashboard_admin_wall, require_dashboard_session
from app.presentation.api.routers import system_status as system_router


@pytest.fixture
def restore_app_overrides() -> None:
    """Clear dependency overrides after each test."""

    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_system_status_requires_dashboard_auth() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/system/status")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_system_status_accepts_dashboard_admin_with_overrides(restore_app_overrides: None) -> None:
    app.dependency_overrides[dashboard_admin_wall] = lambda: True
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": "dash:operator"}

    async def _fake_readiness() -> tuple[dict[str, object], object]:
        return {"checks": {"redis": {"ok": True}, "postgres": {"ok": True}}}, None

    async def _fake_hive_gauges() -> tuple[int, int, int, int]:
        return 7, 3, 2, 5

    async def _fake_sim_counts() -> tuple[int, int]:
        return 1, 4

    system_router.collect_readiness_uncached = _fake_readiness  # type: ignore[assignment]
    system_router._hive_gauges = _fake_hive_gauges  # type: ignore[assignment]
    system_router._simulation_task_counts = _fake_sim_counts  # type: ignore[assignment]
    system_router._celery_snapshot = lambda: {  # type: ignore[assignment]
        "ok": True,
        "workers_up": 2,
        "active_tasks": 1,
        "reserved_tasks": 0,
    }
    system_router._host_pressure = lambda: (10.0, 20.0, 30.0, False, "")  # type: ignore[assignment]
    system_router._llm_flags = lambda: (True, True, False)  # type: ignore[assignment]
    system_router.llm_concurrency_snapshot = lambda: {  # type: ignore[assignment]
        "llm_limit": 6,
        "llm_in_flight": 1,
        "simulation_limit": 3,
        "simulation_in_flight": 0,
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/v1/system/status", headers={"Authorization": "Bearer test-token"})
    assert res.status_code == 200
    body = res.json()
    assert body["redis_ok"] is True
    assert body["db_ok"] is True
    assert body["agents_total"] == 7
    assert body["simulation_tasks_pending"] == 4
