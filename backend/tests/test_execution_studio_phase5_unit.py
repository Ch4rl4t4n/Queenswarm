"""Phase 5 — media registry, browser fallback, super router snapshot."""

from __future__ import annotations

from app.application.services.execution_studio import (
    _template_id_for_slug,
    build_browser_fallback_lane,
    build_media_tool_registry,
    build_super_router_snapshot,
)


def test_template_id_for_slug_uses_suggested_slug() -> None:
    """Phase3 templates map by suggested_slug, not legacy slug field."""

    assert _template_id_for_slug("gmail_workspace") == "gmail_google_workspace"
    assert _template_id_for_slug("unknown_slug") is None


def test_build_media_tool_registry_lists_venice_monid() -> None:
    """Media registry includes Venice and Monid templates."""

    payload = build_media_tool_registry(connections=[])
    slugs = {item["slug"] for item in payload["items"]}
    assert "venice_mcp" in slugs
    assert "monid_mcp" in slugs
    assert payload["pack_id"] == "media"


def test_build_browser_fallback_lane_has_api() -> None:
    """Browser fallback exposes harness sessions API."""

    lane = build_browser_fallback_lane()
    assert lane["role"] == "browser_operator"
    assert "browser-harness" in lane["sessions_api"]


def test_build_super_router_snapshot_empty_tenant() -> None:
    """Empty tenant returns zero routers."""

    snap = build_super_router_snapshot(None)
    assert snap["count"] == 0
    assert snap["items"] == []
