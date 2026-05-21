"""API coverage for harness Pattern Explorer route."""

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
from app.presentation.api.routers import harness as harness_router


@pytest.fixture
def harness_auth_fixture() -> Generator[None, None, None]:
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
async def test_harness_pattern_explorer_route(
    monkeypatch: pytest.MonkeyPatch,
    harness_auth_fixture: None,
) -> None:
    """Pattern Explorer endpoint returns catalog + usage payload."""

    async def _fake_payload(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "router_enabled": True,
            "forced_reflection_enabled": True,
            "window_hours": 24,
            "sessions_in_window": 1,
            "unique_patterns_today": 2,
            "usage_today": [{"id": "planning", "label": "Planning", "count": 1}],
            "catalog": [{"id": "planning", "number": 6, "label": "Planning", "summary": "Orchestration"}],
            "recent_sessions": [],
            "docs_path": "docs/QUEENSWARM_DESIGN_PATTERNS.md",
        }

    monkeypatch.setattr(harness_router, "build_pattern_explorer_payload", _fake_payload)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/harness/pattern-explorer")

    assert resp.status_code == 200
    body = resp.json()
    assert body["unique_patterns_today"] == 2
    assert body["catalog"][0]["id"] == "planning"
