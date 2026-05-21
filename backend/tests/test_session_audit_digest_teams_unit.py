"""Unit tests for Microsoft Teams supervisor audit digest delivery."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.application.services.supervisor.session_audit_digest import send_supervisor_audit_digest_teams


@pytest.mark.asyncio
async def test_send_supervisor_audit_digest_teams_when_disabled_then_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Teams digest helper skips when feature flag is off."""

    from app.core.config import settings

    monkeypatch.setattr(settings, "supervisor_audit_digest_teams_enabled", False)
    ok = await send_supervisor_audit_digest_teams(
        tenant_name="Acme",
        window_hours=24,
        rows=[],
        generated_at=datetime.now(tz=UTC),
    )
    assert ok is False


@pytest.mark.asyncio
async def test_notify_teams_posts_message_card(monkeypatch: pytest.MonkeyPatch) -> None:
    """Teams notifier posts MessageCard JSON to webhook URL."""

    from app.core.config import settings
    from app.core.notifications import notify_teams

    posted: dict[str, object] = {}

    class _FakeResponse:
        status_code = 200

    class _FakeClient:
        async def __aenter__(self) -> _FakeClient:
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def post(self, url: str, json: dict[str, object]) -> _FakeResponse:
            posted["url"] = url
            posted["json"] = json
            return _FakeResponse()

    webhook = "https://contoso.webhook.office.com/webhook/abc/def"
    monkeypatch.setattr(settings, "teams_webhook_url", webhook)
    monkeypatch.setattr("app.core.notifications.httpx.AsyncClient", lambda **_kwargs: _FakeClient())

    ok = await notify_teams("hello digest", title="Supervisor audit")
    assert ok is True
    assert posted["url"] == webhook
    payload = posted["json"]
    assert isinstance(payload, dict)
    assert payload.get("@type") == "MessageCard"
    assert payload.get("text") == "hello digest"
