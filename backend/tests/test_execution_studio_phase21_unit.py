"""Phase 21 — server webhook test status, fingerprint matching, merge clears."""

from __future__ import annotations

import uuid
from types import SimpleNamespace

from app.application.services.execution_studio import merge_studio_notifications_patch, studio_notifications
from app.application.services.execution_studio_notifications import (
    build_notification_test_status_ui,
    notification_value_fingerprint,
    record_notification_test_status,
)


def test_notification_value_fingerprint_tail() -> None:
    """Long webhook URLs fingerprint from the tail for stable matching."""

    long_url = f"https://hooks.slack.com/services/{'x' * 80}"
    assert len(notification_value_fingerprint(long_url)) <= 48


def test_record_and_resolve_notification_test_status() -> None:
    """Persisted test status survives when fingerprint matches current webhook."""

    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        operator_settings={
            "execution_studio": {
                "notifications": {
                    "slack_webhook_url": "https://hooks.slack.com/services/abc",
                },
            },
        },
    )
    record_notification_test_status(
        tenant,  # type: ignore[arg-type]
        channel="slack",
        value="https://hooks.slack.com/services/abc",
        status="ok",
    )
    ui = build_notification_test_status_ui(tenant)  # type: ignore[arg-type]
    assert ui["slack"]["status"] == "ok"


def test_merge_notifications_patch_clears_test_status_on_url_change() -> None:
    """Editing webhook URL clears stale cross-device test status."""

    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        operator_settings={
            "execution_studio": {
                "notifications": {
                    "slack_webhook_url": "https://hooks.slack.com/services/old",
                    "webhook_test_status": {
                        "slack": {
                            "fingerprint": notification_value_fingerprint("https://hooks.slack.com/services/old"),
                            "status": "ok",
                            "tested_at": "2026-05-20T12:00:00+00:00",
                        },
                    },
                },
            },
        },
    )
    record_notification_test_status(
        tenant,  # type: ignore[arg-type]
        channel="slack",
        value="https://hooks.slack.com/services/old",
        status="ok",
    )
    merged = merge_studio_notifications_patch(
        tenant.operator_settings,
        {"slack_webhook_url": "https://hooks.slack.com/services/new"},
    )
    tenant.operator_settings = merged
    assert build_notification_test_status_ui(tenant) == {}  # type: ignore[arg-type]


def test_studio_notifications_includes_webhook_test_status() -> None:
    """Overview notifications expose resolved webhook test status map."""

    tenant = SimpleNamespace(
        id=uuid.uuid4(),
        operator_settings={
            "execution_studio": {
                "notifications": {
                    "email_recipients": ["ops@example.com"],
                    "webhook_test_status": {
                        "email": {
                            "fingerprint": notification_value_fingerprint("ops@example.com"),
                            "status": "ok",
                            "tested_at": "2026-05-20T12:00:00+00:00",
                        },
                    },
                },
            },
        },
    )
    settings = studio_notifications(tenant)  # type: ignore[arg-type]
    assert settings["webhook_test_status"]["email"]["status"] == "ok"
