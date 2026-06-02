"""Unit tests for sliding 2FA re-verification window."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from app.presentation.api.routers import dashboard_session as mod


def test_totp_login_challenge_required_when_within_window_then_false() -> None:
    user = SimpleNamespace(
        totp_secret="secret",
        totp_verified_at=datetime.now(tz=UTC),
        notification_prefs={"totp_last_auth_at": datetime.now(tz=UTC).isoformat()},
    )
    assert mod._totp_login_challenge_required(user, max_hours=4) is False  # type: ignore[arg-type]


def test_totp_login_challenge_required_when_expired_then_true() -> None:
    stale = datetime.now(tz=UTC) - timedelta(hours=5)
    user = SimpleNamespace(
        totp_secret="secret",
        totp_verified_at=datetime.now(tz=UTC),
        notification_prefs={"totp_last_auth_at": stale.isoformat()},
    )
    assert mod._totp_login_challenge_required(user, max_hours=4) is True  # type: ignore[arg-type]


def test_totp_login_challenge_required_when_window_disabled_then_false() -> None:
    user = SimpleNamespace(
        totp_secret="secret",
        totp_verified_at=datetime.now(tz=UTC),
        notification_prefs={},
    )
    assert mod._totp_login_challenge_required(user, max_hours=0) is False  # type: ignore[arg-type]


def test_2fa_session_reverify_required_uses_custom_max_hours(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.core.config import settings

    monkeypatch.setattr(settings, "enable_2fa", True)
    user = SimpleNamespace(totp_secret="secret", totp_verified_at=datetime.now(tz=UTC))
    auth_at = int((datetime.now(tz=UTC) - timedelta(hours=5)).timestamp())
    assert mod._2fa_session_reverify_required(user, auth_at, max_hours=4) is True  # type: ignore[arg-type]
    assert mod._2fa_session_reverify_required(user, auth_at, max_hours=24) is False  # type: ignore[arg-type]
