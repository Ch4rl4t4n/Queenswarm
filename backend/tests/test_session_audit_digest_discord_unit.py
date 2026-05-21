"""Unit tests for Discord supervisor audit digest delivery."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.application.services.supervisor.session_audit_digest import send_supervisor_audit_digest_discord


@pytest.mark.asyncio
async def test_send_supervisor_audit_digest_discord_when_disabled_then_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Discord digest helper skips when feature flag is off."""

    from app.core.config import settings

    monkeypatch.setattr(settings, "supervisor_audit_digest_discord_enabled", False)
    ok = await send_supervisor_audit_digest_discord(
        tenant_name="Acme",
        window_hours=24,
        rows=[],
        generated_at=datetime.now(tz=UTC),
    )
    assert ok is False


@pytest.mark.asyncio
async def test_notify_discord_posts_webhook(monkeypatch: pytest.MonkeyPatch) -> None:
    """Discord notifier posts JSON content to webhook URL."""

    from app.core.config import settings
    from app.core.notifications import notify_discord

    posted: dict[str, object] = {}

    class _FakeResponse:
        status_code = 204

    class _FakeClient:
        async def __aenter__(self) -> _FakeClient:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, url: str, json: dict[str, object]) -> _FakeResponse:
            posted["url"] = url
            posted["json"] = json
            return _FakeResponse()

    monkeypatch.setattr(settings, "discord_webhook_url", "https://discord.com/api/webhooks/1/token")
    monkeypatch.setattr("app.core.notifications.httpx.AsyncClient", lambda **_kwargs: _FakeClient())

    ok = await notify_discord("hello digest")
    assert ok is True
    assert posted["url"] == "https://discord.com/api/webhooks/1/token"
    assert posted["json"] == {"content": "hello digest"}
