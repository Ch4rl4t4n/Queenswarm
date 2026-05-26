"""Phase 17 — tab-hidden toasts, 410 push cleanup, webhook test, sub-agent failures."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from pywebpush import WebPushException

from app.application.services.execution_studio_notifications import ping_studio_notification_webhooks
from app.application.services.execution_studio_push import (
    _webpush_subscription_gone,
    send_execution_studio_web_push,
    upsert_push_subscription,
)


def test_webpush_subscription_gone_detects_410_and_404() -> None:
    """Gone push endpoints map to subscription cleanup."""

    response_410 = MagicMock(status_code=410)
    response_404 = MagicMock(status_code=404)
    response_500 = MagicMock(status_code=500)
    assert _webpush_subscription_gone(WebPushException("gone", response=response_410)) is True
    assert _webpush_subscription_gone(WebPushException("missing", response=response_404)) is True
    assert _webpush_subscription_gone(WebPushException("retry", response=response_500)) is False
    assert _webpush_subscription_gone(WebPushException("no response")) is False


@pytest.mark.asyncio
async def test_send_web_push_removes_gone_subscription(monkeypatch: pytest.MonkeyPatch) -> None:
    """410 Web Push response prunes stale subscription from tenant settings."""

    monkeypatch.setattr("app.application.services.execution_studio_push.web_push_configured", lambda: True)
    monkeypatch.setattr(
        "app.application.services.execution_studio_push.settings.execution_studio_vapid_private_key",
        "test-private-key",
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_push.settings.execution_studio_vapid_contact_email",
        "ops@queenswarm.love",
    )

    user_id = uuid.uuid4()
    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        operator_settings=upsert_push_subscription(
            None,
            user_id=user_id,
            subscription={"endpoint": "https://push.example/sub/1", "keys": {"p256dh": "x", "auth": "y"}},
        ),
    )

    def _fake_webpush(**_kwargs: object) -> MagicMock:
        raise WebPushException("gone", response=MagicMock(status_code=410))

    monkeypatch.setattr("app.application.services.execution_studio_push.webpush", _fake_webpush)

    out = await send_execution_studio_web_push(
        tenant=tenant,  # type: ignore[arg-type]
        title="Pending",
        body="Confirm live",
        url="/integrations?tab=studio",
    )
    assert out == {"sent": 0, "failed": 1, "removed": 1}
    push = tenant.operator_settings["execution_studio"]["push"]
    assert push["subscriptions"] == []


@pytest.mark.asyncio
async def test_studio_webhook_test_pings_teams(monkeypatch: pytest.MonkeyPatch) -> None:
    """Execution Studio webhook test uses tenant Teams URL."""

    teams_calls: list[str | None] = []

    async def _fake_teams(_message: str, *, webhook_url: str | None = None, **_k: object) -> bool:
        teams_calls.append(webhook_url)
        return True

    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_teams",
        _fake_teams,
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_slack",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_discord",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications._resolve_webhook",
        lambda _tenant, *, channel: (
            "https://contoso.webhook.office.com/webhook/abc"
            if channel == "teams"
            else None
        ),
    )
    monkeypatch.setattr("app.application.services.execution_studio_notifications.settings.execution_studio_enabled", True)

    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={})
    out = await ping_studio_notification_webhooks(tenant=tenant)  # type: ignore[arg-type]
    assert out["teams"] is True
    assert teams_calls == ["https://contoso.webhook.office.com/webhook/abc"]


@pytest.mark.asyncio
async def test_studio_webhook_test_no_urls_returns_detail(monkeypatch: pytest.MonkeyPatch) -> None:
    """Webhook test reports when no channel accepts the ping."""

    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_teams",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_slack",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications.notify_discord",
        AsyncMock(return_value=False),
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_notifications._resolve_webhook",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr("app.application.services.execution_studio_notifications.settings.execution_studio_enabled", True)

    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={})
    out = await ping_studio_notification_webhooks(tenant=tenant)  # type: ignore[arg-type]
    assert out["detail"] == "no_webhooks_accepted"
