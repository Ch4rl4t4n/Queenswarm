"""API coverage for unified savings dashboard route."""

from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.presentation.api.deps import (
    dashboard_admin_wall,
    require_dashboard_session,
    require_dashboard_user_with_tenant_role,
)
from app.presentation.api.routers import dashboard as dashboard_router


@pytest.fixture
def unified_savings_auth_fixture() -> Generator[None, None, None]:
    """Inject tenant-scoped dashboard principal."""

    actor = uuid.uuid4()
    tenant = uuid.uuid4()
    app.dependency_overrides[dashboard_admin_wall] = lambda: True
    app.dependency_overrides[require_dashboard_session] = lambda: {"sub": f"dash:{actor}"}
    app.dependency_overrides[require_dashboard_user_with_tenant_role] = lambda: {
        "tenant_id": tenant,
        "tenant_role": "owner",
        "permissions": ["connectors:view"],
    }
    try:
        yield
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_dashboard_unified_savings_route(
    monkeypatch: pytest.MonkeyPatch,
    unified_savings_auth_fixture: None,
) -> None:
    """Unified savings endpoint returns merged headline payload."""

    async def _fake_payload(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "window_days": 30,
            "hourly_rate_usd": 50.0,
            "headline": {"total_value_usd": 120.0, "hours_saved_total": 2.0},
            "time_saved": {"hours_saved_total": 2.0, "breakdown": []},
            "llm_savings": {"saved_usd": 20.0},
            "llm_savings_available": True,
            "disclaimer": "stub",
        }

    monkeypatch.setattr(dashboard_router, "build_unified_savings_payload", _fake_payload)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/dashboard/unified-savings?window_days=30")

    assert resp.status_code == 200
    body = resp.json()
    assert body["headline"]["total_value_usd"] == 120.0
    assert body["llm_savings_available"] is True
