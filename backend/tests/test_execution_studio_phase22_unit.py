"""Phase 22 — digest preview send, test status timestamps, send helper."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application.services.execution_studio_notifications import (
    build_notification_test_status_ui,
    record_notification_test_status,
    send_studio_weekly_rollup_preview,
)


def test_build_notification_test_status_ui_includes_tested_at() -> None:
    """Resolved UI status includes tested_at metadata."""

    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        operator_settings={
            "execution_studio": {
                "notifications": {
                    "slack_webhook_url": "https://hooks.slack.com/services/abc",
                    "webhook_test_status": {
                        "slack": {
                            "fingerprint": "https://hooks.slack.com/services/abc",
                            "status": "ok",
                            "tested_at": "2026-05-20T10:00:00+00:00",
                        },
                    },
                },
            },
        },
    )
    ui = build_notification_test_status_ui(tenant)  # type: ignore[arg-type]
    assert ui["slack"]["status"] == "ok"
    assert ui["slack"]["tested_at"] == "2026-05-20T10:00:00+00:00"


@pytest.mark.asyncio
async def test_send_studio_weekly_rollup_preview_delivers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Preview send posts formatted weekly rollup to operator channels."""

    tenant = SimpleNamespace(id=uuid.uuid4(), name="Acme Hive", operator_settings={})
    monkeypatch.setattr(
        "app.application.services.execution_studio_telemetry_rollup.build_weekly_execution_studio_rollup_preview",
        lambda *, tenant: {
            "message": "Weekly Execution Studio rollup for *Acme Hive*",
            "email_body": "Weekly Execution Studio rollup for Acme Hive",
            "telemetry": {},
            "last_sent_at": None,
        },
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_slack",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_discord",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_teams",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_execution_studio_email",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr("app.application.services.execution_studio_notifications.settings.execution_studio_enabled", True)

    out = await send_studio_weekly_rollup_preview(tenant=tenant)  # type: ignore[arg-type]
    assert out["ok"] is True
    assert out["channels"]["email"] is True


def test_record_notification_test_status_sets_tested_at() -> None:
    """Recording test status persists ISO tested_at timestamp."""

    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={"execution_studio": {"notifications": {}}})
    record_notification_test_status(
        tenant,  # type: ignore[arg-type]
        channel="email",
        value="ops@example.com",
        status="ok",
    )
    bucket = tenant.operator_settings["execution_studio"]["notifications"]["webhook_test_status"]["email"]
    assert bucket["status"] == "ok"
    assert bucket["tested_at"]
