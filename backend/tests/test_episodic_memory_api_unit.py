"""API coverage for episodic memory routes."""

from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import (
    require_dashboard_session,
    require_dashboard_user_with_tenant_role,
    require_subject,
)
from app.presentation.api.routers import episodic_memory as episodic_router


@pytest.fixture
def episodic_auth_fixture() -> Generator[None, None, None]:
    """Tenant-scoped dashboard principal."""

    actor = uuid.uuid4()
    tenant = uuid.uuid4()
    app.dependency_overrides[require_subject] = lambda: f"dash:{actor}"
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": f"dash:{actor}"}
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "tenant_id": tenant,
        "tenant_role": "owner",
        "permissions": [],
    }
    try:
        yield
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_episodic_memory_summary_route(
    monkeypatch: pytest.MonkeyPatch,
    episodic_auth_fixture: None,
) -> None:
    """Summary endpoint returns per-source counters."""

    async def _fake_summary(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "retention_days": 90,
            "counts": {
                "session_events": 2,
                "dream_insights": 1,
                "dump_sleep_batches": 0,
                "session_summaries": 1,
            },
            "total_items": 4,
            "latest_at": "2026-05-21T08:00:00+00:00",
        }

    monkeypatch.setattr(episodic_router, "build_episodic_summary", _fake_summary)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/memory/episodic/summary")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_items"] == 4
    assert body["counts"]["session_events"] == 2


@pytest.mark.asyncio
async def test_episodic_memory_timeline_route(
    monkeypatch: pytest.MonkeyPatch,
    episodic_auth_fixture: None,
) -> None:
    """Timeline endpoint returns merged episodic feed."""

    async def _fake_timeline(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "retention_days": 90,
            "item_count": 1,
            "items": [
                {
                    "id": "evt-1",
                    "kind": "session_event",
                    "occurred_at": "2026-05-21T08:00:00+00:00",
                    "title": "Session started",
                    "summary": "Supervisor session created.",
                    "session_id": str(uuid.uuid4()),
                    "metadata": {},
                },
            ],
        }

    monkeypatch.setattr(episodic_router, "build_episodic_timeline", _fake_timeline)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/memory/episodic/timeline?limit=10")

    assert resp.status_code == 200
    body = resp.json()
    assert body["item_count"] == 1
    assert body["items"][0]["kind"] == "session_event"
