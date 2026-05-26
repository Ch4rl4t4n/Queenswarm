"""Phase 12 — auto-clear pending, weekly rollup, cleared-aware pending snapshot."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.application.services.execution_studio_pending import collect_pending_live_actions
from app.application.services.execution_studio_telemetry_rollup import format_weekly_rollup_message


def test_pending_cleared_removes_live_actions() -> None:
    """Newer approval_cleared row removes pending browser/external actions."""

    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        operator_settings={
            "execution_studio": {
                "recent_activity": [
                    {
                        "event_type": "approval_cleared",
                        "message": "Operator confirmed live browser",
                        "payload": {"lane": "browser", "pending_cleared": True},
                        "at": "2026-05-21T13:00:00+00:00",
                    },
                    {
                        "event_type": "browser_step",
                        "message": "Browser live step pending operator approval",
                        "payload": {"pending_approval": True, "mode": "live"},
                        "at": "2026-05-21T12:00:00+00:00",
                    },
                    {
                        "event_type": "approval_cleared",
                        "message": "Operator confirmed live external",
                        "payload": {
                            "lane": "external",
                            "pending_cleared": True,
                            "connector_slug": "slack_workspace",
                            "tool_name": "post_message",
                        },
                        "at": "2026-05-21T13:01:00+00:00",
                    },
                    {
                        "event_type": "tool_execute",
                        "message": "External live pending approval: slack_workspace/post_message",
                        "payload": {
                            "pending_approval": True,
                            "connector_slug": "slack_workspace",
                            "tool_name": "post_message",
                        },
                        "at": "2026-05-21T12:01:00+00:00",
                    },
                ],
            },
        },
    )
    assert collect_pending_live_actions(tenant, limit=40) == []


def test_format_weekly_rollup_message() -> None:
    """Weekly rollup message includes top connector stats."""

    message = format_weekly_rollup_message(
        tenant_name="Acme Hive",
        telemetry={
            "tool_executes": 12,
            "browser_steps": 3,
            "proposals_created": 2,
            "cost_tier_blocks": 1,
            "window_limit": 40,
            "connector_chart": [
                {"slug": "notion_workspace", "runs": 8, "blocks": 1},
                {"slug": "slack_workspace", "runs": 4, "blocks": 0},
            ],
        },
    )
    assert "Acme Hive" in message
    assert "notion_workspace" in message
    assert "Cost blocks: 1" in message


@pytest.mark.asyncio
async def test_browser_live_confirm_clears_pending(monkeypatch: pytest.MonkeyPatch) -> None:
    """Operator-confirmed browser live step emits approval_cleared activity."""

    cleared: list[str] = []

    async def _fake_clear(session: object, tenant: object, **kwargs: object) -> None:
        cleared.append(str(kwargs.get("lane")))

    async def _fake_persist(*_a: object, **_k: object) -> None:
        return None

    monkeypatch.setattr(
        "app.application.services.execution_studio_activity.persist_pending_live_cleared",
        _fake_clear,
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_browser.persist_execution_activity",
        _fake_persist,
    )

    class _BrowserRow:
        id = uuid.uuid4()
        current_url = "https://queenswarm.love"
        actions_used = 1

    class _BrowserManager:
        @staticmethod
        async def create_session(*_a: object, **_k: object) -> _BrowserRow:
            return _BrowserRow()

        @staticmethod
        async def execute_action(*_a: object, **_k: object) -> dict:
            return {"snapshot_text": "ok"}

    monkeypatch.setattr(
        "app.application.services.execution_studio_browser.BrowserManager",
        _BrowserManager,
    )

    from app.application.services.execution_studio_browser import execute_browser_fallback_step

    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={})
    out = await execute_browser_fallback_step(
        None,  # type: ignore[arg-type]
        tenant=tenant,  # type: ignore[arg-type]
        dashboard_user_id=uuid.uuid4(),
        goal="Verify https://queenswarm.love",
        mode="live",
        operator_confirmed=True,
    )
    assert out.get("ok") is True
    assert cleared == ["browser"]
