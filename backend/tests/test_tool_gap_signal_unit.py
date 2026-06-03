"""Unit tests for MCP tool gap signal classification."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.tool_gap_signal import (
    classify_tool_gap,
    record_tool_gap,
    suggest_phase3_template_id,
)


def test_classify_connector_missing() -> None:
    gap = classify_tool_gap(
        result="dynamic_invoke_error: connector `github_rest` inactive or unknown",
        connector_slug="github_rest",
        tool_name="invoke",
        manager_slug="researcher",
    )
    assert gap is not None
    assert gap["kind"] == "connector_missing"
    assert gap["connector_slug"] == "github_rest"


def test_classify_manager_allowlist_block() -> None:
    gap = classify_tool_gap(
        result="mcp_invoke blocked for `notion_workspace` (not manager-allowlisted).",
        connector_slug="notion_workspace",
        tool_name="search",
        manager_slug="coder",
    )
    assert gap is not None
    assert gap["kind"] == "manager_allowlist"


def test_classify_ignores_transient_rate_limit() -> None:
    gap = classify_tool_gap(
        result="dynamic_invoke_error: rate_limited(Postgres-backed sliding window)",
        connector_slug="slack_workspace",
        tool_name="invoke",
        manager_slug="",
    )
    assert gap is None


def test_suggest_phase3_template_for_slug() -> None:
    assert suggest_phase3_template_id("github_rest") == "github_rest"


@pytest.mark.asyncio
async def test_record_tool_gap_persists_deduped(monkeypatch) -> None:
    tenant_id = uuid.uuid4()
    stored: dict[str, object] = {"gaps": []}

    async def fake_get_json(_key: str) -> dict[str, object]:
        return {"gaps": list(stored["gaps"])}

    async def fake_set_json(_key: str, payload: dict[str, object], *, ttl: int) -> None:
        stored["gaps"] = list(payload.get("gaps") or [])

    monkeypatch.setattr(
        "app.application.services.tool_gap_signal.settings",
        type("S", (), {"tool_gap_signal_enabled": True})(),
    )
    monkeypatch.setattr("app.application.services.tool_gap_signal.get_json", fake_get_json)
    monkeypatch.setattr("app.application.services.tool_gap_signal.set_json", fake_set_json)

    await record_tool_gap(
        tenant_id=tenant_id,
        connector_slug="github_rest",
        tool_name="invoke",
        manager_slug="researcher",
        result="dynamic_invoke_error: connector `github_rest` inactive or unknown",
    )
    await record_tool_gap(
        tenant_id=tenant_id,
        connector_slug="github_rest",
        tool_name="invoke",
        manager_slug="researcher",
        result="dynamic_invoke_error: connector `github_rest` inactive or unknown",
    )

    gaps = stored["gaps"]
    assert len(gaps) == 1
    assert int(gaps[0]["occurrences"]) == 2  # type: ignore[index]
