"""Phase 18 — per-channel webhook test, push session sync helpers."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application.services.execution_studio_notifications import ping_studio_notification_webhooks


@pytest.mark.asyncio
async def test_ping_studio_webhooks_single_channel_teams(monkeypatch: pytest.MonkeyPatch) -> None:
    """Channel filter pings only the requested webhook."""

    slack_called = False
    teams_called = False

    async def _fake_slack(*_a: object, **_k: object) -> bool:
        nonlocal slack_called
        slack_called = True
        return True

    async def _fake_teams(*_a: object, **_k: object) -> bool:
        nonlocal teams_called
        teams_called = True
        return True

    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_slack",
        _fake_slack,
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_discord",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_teams",
        _fake_teams,
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications._resolve_webhook",
        lambda _tenant, *, channel: "https://example.com/hook" if channel == "teams" else None,
    )
    monkeypatch.setattr("app.application.services.execution_studio_notifications.settings.execution_studio_enabled", True)

    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={})
    out = await ping_studio_notification_webhooks(tenant=tenant, channels=["teams"])  # type: ignore[arg-type]
    assert out["teams"] is True
    assert teams_called is True
    assert slack_called is False


@pytest.mark.asyncio
async def test_ping_studio_webhooks_invalid_channels(monkeypatch: pytest.MonkeyPatch) -> None:
    """Empty channel filter returns invalid_channels detail."""

    monkeypatch.setattr("app.application.services.execution_studio_notifications.settings.execution_studio_enabled", True)
    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={})
    out = await ping_studio_notification_webhooks(tenant=tenant, channels=["email"])  # type: ignore[arg-type]
    assert out["detail"] == "invalid_channels"
