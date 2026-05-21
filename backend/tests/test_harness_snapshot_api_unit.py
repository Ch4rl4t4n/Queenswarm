"""API coverage for harness snapshot and intelligence scan routes."""

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
def harness_snapshot_auth_fixture() -> Generator[None, None, None]:
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
async def test_harness_snapshot_route(
    monkeypatch: pytest.MonkeyPatch,
    harness_snapshot_auth_fixture: None,
) -> None:
    """Snapshot endpoint returns rules, skills, and monitoring payload."""

    async def _fake_snapshot(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "rule_layers": [{"id": "cursorrules", "path": ".cursorrules", "scope": "root", "bytes": "1200"}],
            "skills": {"count": 2, "items": [{"slug": "self-review-loop", "title": "Self Review", "priority": 10, "roles": []}]},
            "mcp_tools": {"count": 0, "items": []},
            "recent_agentic_patterns": [],
            "feature_flags": {"supervisor_pattern_router_enabled": True},
            "tech_health_score": 0.85,
            "monitoring": {
                "slack_webhook_configured": False,
                "alertmanager_receiver": "blackhole",
                "pattern_alert_rules": ["PatternSuccessRateLow"],
                "grafana_dashboard_uid": "queenswarm-agentic-patterns",
                "smoke_script": "scripts/alertmanager-smoke.sh",
            },
            "docs": {},
        }

    monkeypatch.setattr(harness_router, "build_harness_snapshot", _fake_snapshot)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/harness/snapshot")

    assert resp.status_code == 200
    body = resp.json()
    assert body["skills"]["count"] == 2
    assert body["tech_health_score"] == 0.85


@pytest.mark.asyncio
async def test_harness_intelligence_scan_route(
    monkeypatch: pytest.MonkeyPatch,
    harness_snapshot_auth_fixture: None,
) -> None:
    """Intelligence scan returns read-only proposals."""

    def _fake_scan() -> dict[str, object]:
        return {"scanned_at": "2026-05-21T00:00:00+00:00", "proposal_count": 1, "proposals": [{"kind": "skill_keywords", "target": "x", "priority": "medium", "rationale": "test"}]}

    monkeypatch.setattr(harness_router, "run_intelligence_scan", _fake_scan)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/harness/intelligence-scan", json={})

    assert resp.status_code == 200
    assert resp.json()["proposal_count"] == 1
