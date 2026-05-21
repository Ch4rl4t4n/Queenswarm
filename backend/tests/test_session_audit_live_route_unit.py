"""Route registration tests for supervisor audit live websocket."""

from __future__ import annotations

from app.main import app


def test_supervisor_audit_live_websocket_route_registered() -> None:
    """Audit live websocket is mounted under /api/v1/agents."""

    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/api/v1/agents/sessions/{session_id}/audit-live" in paths
