"""Phase 15 — pending alerts, webhook settings, confirm throttle, supervisor links."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application.services.execution_studio import merge_studio_notifications_patch, studio_notifications
from app.application.services.execution_studio_confirm_guard import (
    ExecutionStudioConfirmThrottledError,
    assert_operator_confirm_allowed,
)
from app.application.services.execution_studio_pending import (
    _pending_alert_from_snapshot,
    collect_pending_live_actions,
)


def test_merge_studio_notifications_webhooks_https_only() -> None:
    """Webhook patch rejects non-HTTPS URLs."""

    merged = merge_studio_notifications_patch(
        {},
        {
            "slack_webhook_url": "http://insecure.example/hook",
            "discord_webhook_url": "https://discord.com/api/webhooks/test",
        },
    )
    notifications = merged["execution_studio"]["notifications"]
    assert notifications["slack_webhook_url"] == ""
    assert notifications["discord_webhook_url"] == "https://discord.com/api/webhooks/test"


def test_pending_alert_includes_supervisor_session() -> None:
    """Pending snapshot exposes alert fingerprint + supervisor session link."""

    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        operator_settings={
            "execution_studio": {
                "recent_activity": [
                    {
                        "event_type": "browser_step",
                        "message": "Browser live step pending operator approval",
                        "payload": {
                            "pending_approval": True,
                            "supervisor_session_id": "aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee",
                        },
                        "at": "2026-05-21T12:00:00+00:00",
                    },
                ],
            },
        },
    )
    actions = collect_pending_live_actions(tenant, limit=40)
    snapshot = {
        "count": 1,
        "browser_pending": 1,
        "external_pending": 0,
        "codebase_pending": 0,
        "live_actions": actions,
    }
    alert = _pending_alert_from_snapshot(snapshot)
    assert alert is not None
    assert alert["supervisor_session_id"] == "aaaaaaaa-bbbb-4ccc-dddd-eeeeeeeeeeee"
    assert "browser" in alert["fingerprint"]


@pytest.mark.asyncio
async def test_confirm_guard_throttles_duplicate(monkeypatch: pytest.MonkeyPatch) -> None:
    """Second confirm within window raises throttle error."""

    calls = {"n": 0}

    async def _fake_reserve(*_a: object, **_k: object) -> bool:
        calls["n"] += 1
        return calls["n"] == 1

    monkeypatch.setattr(
        "app.application.services.execution_studio_confirm_guard.sliding_window_reserve",
        _fake_reserve,
    )
    tenant_id = uuid.uuid4()
    await assert_operator_confirm_allowed(tenant_id=tenant_id, lane="browser")
    with pytest.raises(ExecutionStudioConfirmThrottledError):
        await assert_operator_confirm_allowed(tenant_id=tenant_id, lane="browser")


def test_studio_notifications_exposes_webhooks() -> None:
    """Notification settings round-trip for operator UI."""

    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        operator_settings={
            "execution_studio": {
                "notifications": {
                    "slack_webhook_url": "https://hooks.slack.com/services/test",
                },
            },
        },
    )
    settings = studio_notifications(tenant)
    assert settings["slack_webhook_url"].startswith("https://")
