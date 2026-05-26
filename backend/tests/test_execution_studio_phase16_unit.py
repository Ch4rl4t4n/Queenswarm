"""Phase 16 — Web Push, Teams webhook, push subscription storage, retry hooks."""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.execution_studio import merge_studio_notifications_patch, studio_notifications
from app.application.services.execution_studio_notifications import notify_execution_studio_pending_approval
from app.application.services.execution_studio_push import (
    clear_push_subscription,
    send_execution_studio_web_push,
    upsert_push_subscription,
    user_has_push_subscription,
    web_push_configured,
)


def test_merge_studio_notifications_teams_webhook_validates_host() -> None:
    """Teams webhook patch accepts known Microsoft hosts only."""

    merged = merge_studio_notifications_patch(
        {},
        {
            "teams_webhook_url": "https://contoso.webhook.office.com/webhook/abc/def",
        },
    )
    notifications = merged["execution_studio"]["notifications"]
    assert notifications["teams_webhook_url"].startswith("https://contoso.webhook.office.com")

    rejected = merge_studio_notifications_patch(
        {},
        {"teams_webhook_url": "https://evil.com/webhook/office.com"},
    )
    assert rejected["execution_studio"]["notifications"]["teams_webhook_url"] == ""


def test_upsert_push_subscription_per_user() -> None:
    """Push subscriptions persist under execution_studio.push bucket."""

    user_id = uuid.uuid4()
    subscription = {"endpoint": "https://push.example/sub/1", "keys": {"p256dh": "x", "auth": "y"}}
    merged = upsert_push_subscription(None, user_id=user_id, subscription=subscription)
    push = merged["execution_studio"]["push"]
    assert len(push["subscriptions"]) == 1
    assert push["subscriptions"][0]["user_id"] == str(user_id)

    other_id = uuid.uuid4()
    merged2 = upsert_push_subscription(merged, user_id=other_id, subscription=subscription)
    assert len(merged2["execution_studio"]["push"]["subscriptions"]) == 2

    replaced = upsert_push_subscription(
        merged2,
        user_id=user_id,
        subscription={"endpoint": "https://push.example/sub/2", "keys": {"p256dh": "a", "auth": "b"}},
    )
    rows = replaced["execution_studio"]["push"]["subscriptions"]
    assert len(rows) == 2
    user_row = next(row for row in rows if row["user_id"] == str(user_id))
    assert user_row["subscription"]["endpoint"] == "https://push.example/sub/2"


def test_clear_push_subscription_removes_user() -> None:
    """Clearing subscription removes only the matching dashboard user."""

    user_id = uuid.uuid4()
    root = upsert_push_subscription(
        None,
        user_id=user_id,
        subscription={"endpoint": "https://push.example/sub/1", "keys": {}},
    )
    cleared = clear_push_subscription(root, user_id=user_id)
    assert cleared["execution_studio"]["push"]["subscriptions"] == []


def test_user_has_push_subscription() -> None:
    """Subscription lookup checks tenant push bucket."""

    user_id = uuid.uuid4()
    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        operator_settings=upsert_push_subscription(
            None,
            user_id=user_id,
            subscription={"endpoint": "https://push.example/sub/1", "keys": {}},
        ),
    )
    assert user_has_push_subscription(tenant, user_id=user_id) is True  # type: ignore[arg-type]
    assert user_has_push_subscription(tenant, user_id=uuid.uuid4()) is False  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_pending_approval_triggers_web_push(monkeypatch: pytest.MonkeyPatch) -> None:
    """Pending approval notification fans out to Web Push helper."""

    push_calls: list[dict[str, str]] = []

    async def _fake_push(**kwargs: object) -> dict[str, int]:
        push_calls.append({k: str(v) for k, v in kwargs.items() if k in {"title", "body", "url"}})
        return {"sent": 1, "failed": 0}

    monkeypatch.setattr(
        "app.application.services.execution_studio_push.send_execution_studio_web_push",
        _fake_push,
    )
    for channel in ("slack", "discord", "teams"):
        monkeypatch.setattr(
            f"app.application.services.execution_studio_notifications.notify_{channel}",
            AsyncMock(return_value=False),
        )

    session_id = uuid.uuid4()
    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={})
    await notify_execution_studio_pending_approval(
        tenant=tenant,  # type: ignore[arg-type]
        title="Browser live step pending",
        message="Confirm live harness step",
        supervisor_session_id=session_id,
    )
    assert len(push_calls) == 1
    assert push_calls[0]["title"] == "Browser live step pending"
    assert session_id.hex in push_calls[0]["url"] or str(session_id) in push_calls[0]["url"]


@pytest.mark.asyncio
async def test_send_execution_studio_web_push_skips_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    """Web Push send is no-op without VAPID keys."""

    monkeypatch.setattr("app.application.services.execution_studio_push.web_push_configured", lambda: False)
    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={})
    out = await send_execution_studio_web_push(
        tenant=tenant,  # type: ignore[arg-type]
        title="Test",
        body="Body",
        url="/integrations?tab=studio",
    )
    assert out == {"sent": 0, "failed": 0, "removed": 0}


@pytest.mark.asyncio
async def test_send_execution_studio_web_push_delivers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Configured Web Push calls pywebpush for each subscription."""

    monkeypatch.setattr("app.application.services.execution_studio_push.web_push_configured", lambda: True)
    monkeypatch.setattr(
        "app.application.services.execution_studio_push.settings.execution_studio_vapid_private_key",
        "test-private-key",
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_push.settings.execution_studio_vapid_contact_email",
        "ops@queenswarm.love",
    )

    sent_payloads: list[str] = []

    def _fake_webpush(*, subscription_info: dict[str, object], data: str, **_k: object) -> MagicMock:
        sent_payloads.append(data)
        assert subscription_info.get("endpoint")
        return MagicMock()

    monkeypatch.setattr("app.application.services.execution_studio_push.webpush", _fake_webpush)

    user_id = uuid.uuid4()
    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        operator_settings=upsert_push_subscription(
            None,
            user_id=user_id,
            subscription={"endpoint": "https://push.example/sub/1", "keys": {"p256dh": "x", "auth": "y"}},
        ),
    )
    out = await send_execution_studio_web_push(
        tenant=tenant,  # type: ignore[arg-type]
        title="Pending approval",
        body="Confirm live step",
        url="/integrations?tab=studio",
    )
    assert out["sent"] == 1
    assert out["failed"] == 0
    assert out["removed"] == 0
    payload = json.loads(sent_payloads[0])
    assert payload["title"] == "Pending approval"
    assert payload["url"] == "/integrations?tab=studio"


def test_studio_notifications_exposes_teams_and_push_flags(monkeypatch: pytest.MonkeyPatch) -> None:
    """Operator notification snapshot includes Teams URL and push configured flag."""

    monkeypatch.setattr(
        "app.application.services.execution_studio.get_settings",
        lambda: SimpleNamespace(
            execution_studio_weekly_rollup_enabled=False,
            execution_studio_vapid_public_key="public-key",
            execution_studio_vapid_private_key="private-key",
        ),
    )
    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        operator_settings={
            "execution_studio": {
                "notifications": {
                    "teams_webhook_url": "https://contoso.webhook.office.com/webhook/abc",
                },
            },
        },
    )
    settings = studio_notifications(tenant)
    assert settings["teams_webhook_url"].startswith("https://contoso.webhook.office.com")
    assert settings["web_push_configured"] is True
