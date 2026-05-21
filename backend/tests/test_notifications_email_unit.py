"""Unit tests for SMTP email notifications."""

from __future__ import annotations

import pytest

from app.core import notifications


@pytest.mark.asyncio
async def test_notify_email_when_smtp_missing_then_returns_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """Email helper skips cleanly when SMTP credentials are absent."""

    monkeypatch.setattr(notifications.settings, "smtp_user", None)
    monkeypatch.setattr(notifications.settings, "smtp_pass", None)
    ok = await notifications.notify_email(subject="Test", body="Body")
    assert ok is False


@pytest.mark.asyncio
async def test_notify_email_when_smtp_configured_then_sends(monkeypatch: pytest.MonkeyPatch) -> None:
    """Email helper delegates to SMTP sync sender when configured."""

    called: dict[str, str] = {}

    def _fake_send(**kwargs):  # noqa: ANN003
        called.update({key: str(value) for key, value in kwargs.items()})

    monkeypatch.setattr(notifications.settings, "smtp_user", "ops@example.com")
    monkeypatch.setattr(notifications.settings, "smtp_pass", "secret")
    monkeypatch.setattr(notifications.settings, "notify_email", "ops@example.com")
    monkeypatch.setattr(notifications, "_smtp_send_sync", _fake_send)

    ok = await notifications.notify_email(subject="Digest", body="Hello")
    assert ok is True
    assert called["recipient"] == "ops@example.com"
    assert called["subject"] == "Digest"
