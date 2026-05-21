"""Unit tests for per-tenant supervisor audit digest configuration."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from app.application.services.supervisor.session_audit_digest_config import (
    classify_tenant_digest_health,
    effective_digest_enabled,
    effective_digest_schedule_hour_utc,
    effective_digest_window_hours,
    is_tenant_digest_due,
    merge_tenant_audit_digest_patch,
    normalize_extra_recipients,
    serialize_audit_digest_config_view,
)


def _tenant(**overrides: object) -> SimpleNamespace:
    base = {"operator_settings": {}, "name": "Acme"}
    base.update(overrides)
    return SimpleNamespace(**base)


def test_normalize_extra_recipients_dedupes_and_validates() -> None:
    """Invalid emails are dropped and duplicates removed."""

    assert normalize_extra_recipients(["Ops@Acme.com", "ops@acme.com", "bad", "x@y.z"]) == [
        "ops@acme.com",
        "x@y.z",
    ]


def test_effective_digest_window_hours_uses_tenant_override() -> None:
    """Tenant window override wins over global default."""

    tenant = _tenant(operator_settings={"supervisor_audit_digest": {"window_hours": 48}})
    assert effective_digest_window_hours(tenant) == 48  # type: ignore[arg-type]


def test_effective_digest_schedule_hour_utc_defaults_to_seven() -> None:
    """Missing tenant schedule falls back to 07:00 UTC."""

    tenant = _tenant()
    assert effective_digest_schedule_hour_utc(tenant) == 7  # type: ignore[arg-type]


def test_is_tenant_digest_due_respects_hour_and_last_sent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Digest fires once per UTC day at configured hour."""

    from app.core.config import settings

    monkeypatch.setattr(settings, "supervisor_audit_digest_enabled", True)
    tenant = _tenant(
        operator_settings={
            "supervisor_audit_digest": {
                "enabled": True,
                "schedule_hour_utc": 7,
                "last_sent_at": "2026-05-19T07:05:00+00:00",
            },
        },
    )
    due_now = datetime(2026, 5, 19, 7, 30, tzinfo=UTC)
    assert is_tenant_digest_due(tenant=tenant, now=due_now) is False  # type: ignore[arg-type]

    next_day = datetime(2026, 5, 20, 7, 0, tzinfo=UTC)
    assert is_tenant_digest_due(tenant=tenant, now=next_day) is True  # type: ignore[arg-type]

    wrong_hour = datetime(2026, 5, 20, 8, 0, tzinfo=UTC)
    assert is_tenant_digest_due(tenant=tenant, now=wrong_hour) is False  # type: ignore[arg-type]


def test_merge_tenant_audit_digest_patch_persists_extra_recipients() -> None:
    """Patch merges nested operator_settings bucket."""

    tenant = _tenant()
    updated = merge_tenant_audit_digest_patch(
        tenant,  # type: ignore[arg-type]
        enabled=True,
        window_hours=12,
        schedule_hour_utc=9,
        extra_recipients=["ops@acme.com"],
        slack_webhook_url="https://hooks.slack.com/services/x",
    )
    bucket = updated["supervisor_audit_digest"]
    assert bucket["enabled"] is True
    assert bucket["window_hours"] == 12
    assert bucket["extra_recipients"] == ["ops@acme.com"]


def test_serialize_audit_digest_config_view_masks_webhook() -> None:
    """API view masks webhook secrets."""

    tenant = _tenant(
        operator_settings={
            "supervisor_audit_digest": {
                "slack_webhook_url": "https://hooks.slack.com/services/ABCDEFGHIJKLMNOP",
            },
        },
    )
    view = serialize_audit_digest_config_view(tenant)  # type: ignore[arg-type]
    assert view["slack_webhook_configured"] is True
    assert view["slack_webhook_preview"] is not None
    assert "ABCDEFGHIJKLMNOP" not in view["slack_webhook_preview"]


def test_effective_digest_enabled_when_tenant_disabled() -> None:
    """Tenant can disable scheduled digests even when global is on."""

    tenant = _tenant(operator_settings={"supervisor_audit_digest": {"enabled": False}})
    assert effective_digest_enabled(tenant=tenant, global_enabled=True) is False  # type: ignore[arg-type]


def test_classify_tenant_digest_health_when_disabled() -> None:
    """Disabled digests map to disabled health."""

    tenant = _tenant(operator_settings={"supervisor_audit_digest": {"enabled": False}})
    assert (
        classify_tenant_digest_health(
            tenant=tenant,  # type: ignore[arg-type]
            digest_enabled=False,
        )
        == "disabled"
    )


def test_classify_tenant_digest_health_when_never_sent() -> None:
    """Enabled digest without last_sent_at is never_sent."""

    tenant = _tenant(operator_settings={"supervisor_audit_digest": {"enabled": True}})
    assert (
        classify_tenant_digest_health(
            tenant=tenant,  # type: ignore[arg-type]
            digest_enabled=True,
        )
        == "never_sent"
    )


def test_classify_tenant_digest_health_when_recently_sent() -> None:
    """Recent delivery within window is healthy."""

    tenant = _tenant(
        operator_settings={
            "supervisor_audit_digest": {
                "enabled": True,
                "last_sent_at": "2026-05-19T07:05:00+00:00",
            },
        },
    )
    now = datetime(2026, 5, 19, 12, 0, tzinfo=UTC)
    assert (
        classify_tenant_digest_health(
            tenant=tenant,  # type: ignore[arg-type]
            digest_enabled=True,
            now=now,
        )
        == "healthy"
    )


def test_classify_tenant_digest_health_when_stale() -> None:
    """Old last_sent_at beyond grace window is stale."""

    tenant = _tenant(
        operator_settings={
            "supervisor_audit_digest": {
                "enabled": True,
                "window_hours": 24,
                "last_sent_at": "2026-05-10T07:05:00+00:00",
            },
        },
    )
    now = datetime(2026, 5, 19, 12, 0, tzinfo=UTC)
    assert (
        classify_tenant_digest_health(
            tenant=tenant,  # type: ignore[arg-type]
            digest_enabled=True,
            now=now,
        )
        == "stale"
    )
