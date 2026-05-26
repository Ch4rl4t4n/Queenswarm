"""Phase 25 — weekly rollup flag, notification snapshot completeness."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.application.services.execution_studio import studio_notifications


def test_studio_notifications_weekly_rollup_enabled_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """Overview exposes whether platform weekly rollup beat is enabled."""

    monkeypatch.setattr(
        "app.application.services.execution_studio.get_settings",
        lambda: SimpleNamespace(
            execution_studio_weekly_rollup_enabled=True,
            execution_studio_vapid_public_key="",
            execution_studio_vapid_private_key="",
        ),
    )
    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={})
    settings = studio_notifications(tenant)  # type: ignore[arg-type]
    assert settings["weekly_rollup_enabled"] is True
    assert settings["webhook_test_history"] == []
