"""Phase 14 — WS operator pending strip, notifications settings, email patch."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application.services.execution_studio import (
    merge_studio_notifications_patch,
    studio_notifications,
)
from app.application.services.hive_live_pulse import build_hive_live_pulse_payload


def test_merge_studio_notifications_patch_normalizes_emails() -> None:
    """Notification patch dedupes and lowercases digest recipients."""

    merged = merge_studio_notifications_patch(
        {},
        {"email_recipients": ["OPS@Example.com", "ops@example.com", "lead@example.com"]},
    )
    bucket = merged["execution_studio"]["notifications"]
    assert set(bucket["email_recipients"]) == {"lead@example.com", "ops@example.com"}


def test_studio_notifications_defaults_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tenants without settings expose empty email list and webhook defaults."""

    monkeypatch.setattr(
        "app.application.services.execution_studio.get_settings",
        lambda: SimpleNamespace(
            execution_studio_weekly_rollup_enabled=False,
            execution_studio_vapid_public_key="",
            execution_studio_vapid_private_key="",
        ),
    )
    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={})
    assert studio_notifications(tenant) == {
        "email_recipients": [],
        "slack_webhook_url": "",
        "discord_webhook_url": "",
        "teams_webhook_url": "",
        "telegram_bot_token": "",
        "telegram_chat_id": "",
        "last_weekly_rollup_at": None,
        "weekly_rollup_enabled": False,
        "webhook_test_status": {},
        "webhook_test_history": [],
        "web_push_configured": False,
    }


@pytest.mark.asyncio
async def test_hive_live_pulse_includes_operator_pending_strip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Authenticated tenant WS payload carries compact pending counts."""

    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={})

    async def _fake_pending(*_a: object, **_k: object) -> dict[str, int | list]:
        return {
            "count": 2,
            "browser_pending": 1,
            "external_pending": 1,
            "codebase_pending": 0,
            "live_actions": [],
        }

    class _ReviewStats:
        pending_count = 3

    monkeypatch.setattr(
        "app.application.services.execution_studio_pending.build_pending_approvals_snapshot",
        _fake_pending,
    )
    monkeypatch.setattr(
        "app.application.services.pending_review_service.fetch_pending_review_stats",
        AsyncMock(return_value=_ReviewStats()),
    )
    monkeypatch.setattr(
        "app.application.services.hive_live_pulse.build_cockpit_system_lite",
        AsyncMock(return_value=SimpleNamespace(model_dump=lambda **_k: {"agents_total": 1})),
    )
    monkeypatch.setattr(
        "app.application.services.hive_live_pulse.build_task_queue_payload",
        AsyncMock(return_value={"items": []}),
    )
    monkeypatch.setattr(
        "app.application.services.hive_live_pulse._collect_agent_deltas",
        AsyncMock(return_value=[]),
    )
    monkeypatch.setattr(
        "app.application.services.hive_live_pulse._collect_recent_tasks",
        AsyncMock(return_value=[]),
    )

    class _Session:
        async def scalar(self, *_a: object, **_k: object) -> int | float:
            return 0

    payload = await build_hive_live_pulse_payload(_Session(), tenant=tenant)  # type: ignore[arg-type]
    strip = payload.get("operator_pending_strip")
    assert strip is not None
    assert strip["count"] == 2
    assert strip["browser_pending"] == 1
    assert strip["review_pending"] == 3
