"""Phase 13 — email weekly rollup, recipient resolution, plain-text body."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest

from app.application.services.execution_studio_notifications import (
    _resolve_email_recipients,
    notify_execution_studio_email,
)
from app.application.services.execution_studio_telemetry_rollup import (
    format_weekly_rollup_email_body,
    format_weekly_rollup_message,
    send_weekly_execution_studio_rollup,
)


def test_format_weekly_rollup_email_body_strips_markdown() -> None:
    """Email body uses plain text without Slack bold markers."""

    telemetry = {
        "tool_executes": 4,
        "browser_steps": 1,
        "proposals_created": 0,
        "cost_tier_blocks": 0,
        "window_limit": 40,
        "connector_chart": [],
    }
    slack = format_weekly_rollup_message(tenant_name="Acme Hive", telemetry=telemetry)
    email = format_weekly_rollup_email_body(tenant_name="Acme Hive", telemetry=telemetry)
    assert "*" not in email
    assert "Acme Hive" in email
    assert slack.count("*") >= 2


def test_resolve_email_recipients_merges_studio_and_digest() -> None:
    """Studio bucket + audit digest extra recipients are deduped."""

    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        operator_settings={
            "execution_studio": {
                "notifications": {
                    "email_recipients": ["ops@example.com", "OPS@example.com"],
                },
            },
            "supervisor_audit_digest": {
                "extra_recipients": ["lead@example.com"],
            },
        },
    )
    recipients = _resolve_email_recipients(tenant)  # noqa: SLF001
    assert recipients == ["lead@example.com", "ops@example.com"]


@pytest.mark.asyncio
async def test_weekly_rollup_includes_email_channel(monkeypatch: pytest.MonkeyPatch) -> None:
    """Weekly rollup records email channel when digest SMTP succeeds."""

    async def _fake_webhooks(*_a: object, **_k: object) -> dict[str, bool]:
        return {"slack": False, "discord": False, "teams": False}

    async def _fake_email(*_a: object, **_k: object) -> bool:
        return True

    monkeypatch.setattr(
        "app.application.services.execution_studio_telemetry_rollup.notify_execution_studio_pending_approval",
        _fake_webhooks,
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_telemetry_rollup.notify_execution_studio_email",
        _fake_email,
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_telemetry_rollup.build_activity_telemetry",
        lambda *_a, **_k: {
            "tool_executes": 2,
            "browser_steps": 1,
            "proposals_created": 0,
            "cost_tier_blocks": 0,
            "window_limit": 40,
            "connector_chart": [],
        },
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_telemetry_rollup.settings.execution_studio_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.application.services.execution_studio_telemetry_rollup.settings.execution_studio_weekly_rollup_enabled",
        True,
    )

    tenant = SimpleNamespace(id=uuid.uuid4(), name="Hive One", operator_settings={}, status="active")

    class _Session:
        async def flush(self) -> None:
            return None

    out = await send_weekly_execution_studio_rollup(_Session(), tenant=tenant)  # type: ignore[arg-type]
    assert out["channels"]["email"] is True


@pytest.mark.asyncio
async def test_notify_execution_studio_email_no_recipients() -> None:
    """Missing recipients short-circuits without SMTP call."""

    tenant = SimpleNamespace(id=uuid.uuid4(), operator_settings={})
    ok = await notify_execution_studio_email(tenant=tenant, title="Test", body="Body")
    assert ok is False
