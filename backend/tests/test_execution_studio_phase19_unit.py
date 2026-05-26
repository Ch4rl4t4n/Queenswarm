"""Phase 19 — digest email test, channel webhook status helpers."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application.services.execution_studio_notifications import (
    ping_studio_digest_email,
    ping_studio_notification_webhooks,
)


@pytest.mark.asyncio
async def test_ping_studio_digest_email_sent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Digest email test sends to configured recipients."""

    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications._resolve_email_recipients",
        lambda _tenant: ["ops@example.com"],
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_execution_studio_email",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr("app.application.services.execution_studio_notifications.settings.execution_studio_enabled", True)
    monkeypatch.setattr("app.application.services.execution_studio_notifications.settings.smtp_user", "ops@example.com")
    monkeypatch.setattr("app.application.services.execution_studio_notifications.settings.smtp_pass", "secret")

    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={})
    out = await ping_studio_digest_email(tenant=tenant)  # type: ignore[arg-type]
    assert out["sent"] is True
    assert out["recipient_count"] == 1


@pytest.mark.asyncio
async def test_ping_studio_digest_email_no_recipients(monkeypatch: pytest.MonkeyPatch) -> None:
    """Digest email test reports when no recipients configured."""

    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications._resolve_email_recipients",
        lambda _tenant: [],
    )
    monkeypatch.setattr("app.application.services.execution_studio_notifications.settings.execution_studio_enabled", True)

    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={})
    out = await ping_studio_digest_email(tenant=tenant)  # type: ignore[arg-type]
    assert out["detail"] == "no_recipients"
    assert out["sent"] is False


@pytest.mark.asyncio
async def test_ping_studio_webhooks_single_slack_only(monkeypatch: pytest.MonkeyPatch) -> None:
    """Slack-only channel filter does not ping Discord or Teams."""

    calls: list[str] = []

    async def _fake_slack(*_a: object, **_k: object) -> bool:
        calls.append("slack")
        return True

    async def _fake_discord(*_a: object, **_k: object) -> bool:
        calls.append("discord")
        return True

    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_slack",
        _fake_slack,
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_discord",
        _fake_discord,
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_teams",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications._resolve_webhook",
        lambda _tenant, *, channel: "https://example.com/hook",
    )
    monkeypatch.setattr("app.application.services.execution_studio_notifications.settings.execution_studio_enabled", True)

    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={})
    out = await ping_studio_notification_webhooks(tenant=tenant, channels=["slack"])  # type: ignore[arg-type]
    assert out["slack"] is True
    assert calls == ["slack"]
