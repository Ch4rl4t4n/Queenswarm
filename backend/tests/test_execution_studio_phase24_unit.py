"""Phase 24 — per-channel preview send, test history, banner helpers."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application.services.execution_studio_notifications import (
    list_webhook_test_history,
    record_notification_test_status,
    send_studio_weekly_rollup_preview,
)


@pytest.mark.asyncio
async def test_send_studio_weekly_rollup_preview_single_channel(monkeypatch: pytest.MonkeyPatch) -> None:
    """Preview send accepts explicit channel list (e.g. slack only)."""

    tenant = SimpleNamespace(id=uuid.uuid4(), name="Acme Hive", operator_settings={})
    monkeypatch.setattr(
        "app.application.services.execution_studio_telemetry_rollup.build_weekly_execution_studio_rollup_preview",
        lambda *, tenant: {
            "message": "Weekly rollup",
            "email_body": "Weekly rollup",
            "telemetry": {},
            "last_sent_at": None,
        },
    )
    slack_mock = AsyncMock(return_value=True)
    monkeypatch.setattr("app.application.services.execution_studio_notifications.notify_slack", slack_mock)
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_discord",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_teams",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_execution_studio_email",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr("app.application.services.execution_studio_notifications.settings.execution_studio_enabled", True)

    out = await send_studio_weekly_rollup_preview(
        tenant=tenant,  # type: ignore[arg-type]
        channels=["slack"],
    )
    assert out["ok"] is True
    assert out["selected"] == ["slack"]
    slack_mock.assert_awaited_once()


def test_record_notification_test_status_appends_history() -> None:
    """Each test records a row in webhook_test_history ring buffer."""

    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        operator_settings={"execution_studio": {"notifications": {}}},
    )
    record_notification_test_status(
        tenant,  # type: ignore[arg-type]
        channel="discord",
        value="https://discord.com/api/webhooks/1",
        status="ok",
    )
    history = list_webhook_test_history(tenant, limit=5)  # type: ignore[arg-type]
    assert history[0]["channel"] == "discord"
    assert history[0]["status"] == "ok"
