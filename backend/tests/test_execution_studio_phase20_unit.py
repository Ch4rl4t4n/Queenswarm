"""Phase 20 — weekly rollup preview, notification metadata, rollup refactor."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.application.services.execution_studio import studio_notifications
from app.application.services.execution_studio_telemetry_rollup import (
    build_weekly_execution_studio_rollup_preview,
    format_weekly_rollup_message,
    send_weekly_execution_studio_rollup,
)


def test_studio_notifications_exposes_last_weekly_rollup_at() -> None:
    """Operator notifications include last weekly rollup timestamp."""

    tenant = SimpleNamespace(
        operator_settings={
            "execution_studio": {
                "notifications": {},
                "last_weekly_rollup_at": "2026-05-20T12:00:00+00:00",
            },
        },
    )
    settings = studio_notifications(tenant)  # type: ignore[arg-type]
    assert settings["last_weekly_rollup_at"] == "2026-05-20T12:00:00+00:00"


def test_build_weekly_execution_studio_rollup_preview() -> None:
    """Preview builder returns formatted bodies without side effects."""

    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        name="Acme Hive",
        operator_settings={
            "execution_studio": {
                "last_weekly_rollup_at": "2026-05-19T08:00:00+00:00",
                "activity_log": [
                    {
                        "event_type": "tool_execute",
                        "connector_slug": "notion_workspace",
                        "at": "2026-05-20T10:00:00+00:00",
                    },
                ],
            },
        },
    )
    preview = build_weekly_execution_studio_rollup_preview(tenant=tenant)  # type: ignore[arg-type]
    assert "Acme Hive" in preview["message"]
    assert preview["email_body"]
    assert preview["last_sent_at"] == "2026-05-19T08:00:00+00:00"
    assert preview["telemetry"]["window_limit"] == 40


@pytest.mark.asyncio
async def test_send_weekly_rollup_uses_preview_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    """Weekly send path reuses preview builder for message bodies."""

    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        name="Acme Hive",
        operator_settings={"execution_studio": {}},
    )
    preview_message = format_weekly_rollup_message(
        tenant_name="Acme Hive",
        telemetry={"tool_executes": 1, "browser_steps": 0, "proposals_created": 0, "cost_tier_blocks": 0, "connector_chart": [], "window_limit": 40},
    )

    monkeypatch.setattr(
        "app.application.services.execution_studio_telemetry_rollup.build_weekly_execution_studio_rollup_preview",
        lambda *, tenant: {
            "message": preview_message,
            "email_body": preview_message.replace("*", ""),
            "telemetry": {"tool_executes": 1},
            "last_sent_at": None,
        },
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_telemetry_rollup.notify_execution_studio_pending_approval",
        AsyncMock(return_value={"slack": True, "discord": False, "teams": False}),
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_telemetry_rollup.notify_execution_studio_email",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr("app.application.services.execution_studio_telemetry_rollup.settings.execution_studio_enabled", True)
    monkeypatch.setattr(
        "app.application.services.execution_studio_telemetry_rollup.settings.execution_studio_weekly_rollup_enabled",
        True,
    )

    session = AsyncMock()
    session.flush = AsyncMock()
    out = await send_weekly_execution_studio_rollup(session, tenant=tenant)  # type: ignore[arg-type]
    assert out["ok"] is True
    assert tenant.operator_settings["execution_studio"]["last_weekly_rollup_at"]
