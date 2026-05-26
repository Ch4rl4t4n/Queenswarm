"""Phase 23 — channel-group preview send, activity log, filtered delivery."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application.services.execution_studio_activity import list_execution_activity
from app.application.services.execution_studio_notifications import send_studio_weekly_rollup_preview


@pytest.mark.asyncio
async def test_send_studio_weekly_rollup_preview_email_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """Preview send can target email channel group only."""

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
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_teams",
        AsyncMock(return_value=True),
    )
    email_mock = AsyncMock(return_value=True)
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_execution_studio_email",
        email_mock,
    )
    monkeypatch.setattr("app.application.services.execution_studio_notifications.settings.execution_studio_enabled", True)

    session = AsyncMock()
    session.commit = AsyncMock()
    out = await send_studio_weekly_rollup_preview(
        tenant=tenant,  # type: ignore[arg-type]
        channel_group="email",
        session=session,  # type: ignore[arg-type]
    )
    assert out["ok"] is True
    assert out["channel_group"] == "email"
    assert out["channels"]["email"] is True
    email_mock.assert_awaited_once()
    session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_send_studio_weekly_rollup_preview_logs_activity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Manual preview send appends digest_preview_send activity row."""

    tenant = SimpleNamespace(id=uuid.uuid4(), name="Acme Hive", operator_settings={"execution_studio": {}})
    monkeypatch.setattr(
        "app.application.services.execution_studio_telemetry_rollup.build_weekly_execution_studio_rollup_preview",
        lambda *, tenant: {
            "message": "Weekly rollup",
            "email_body": "Weekly rollup",
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
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr("app.application.services.execution_studio_notifications.settings.execution_studio_enabled", True)

    session = AsyncMock()
    session.commit = AsyncMock()
    out = await send_studio_weekly_rollup_preview(
        tenant=tenant,  # type: ignore[arg-type]
        channel_group="webhooks",
        session=session,  # type: ignore[arg-type]
    )
    assert out["ok"] is True
    activity = list_execution_activity(tenant, limit=5)  # type: ignore[arg-type]
    assert activity[0]["event_type"] == "digest_preview_send"
    assert "slack" in activity[0]["message"]
