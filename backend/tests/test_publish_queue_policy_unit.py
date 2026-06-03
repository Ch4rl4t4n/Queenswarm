"""Unit tests for publish queue tenant policy."""

from __future__ import annotations

from types import SimpleNamespace

from app.application.services.publish_queue_policy import (
    merge_publish_queue_policy_patch,
    publish_queue_policy,
    tenant_publish_queue_auto_approve_enabled,
)


def test_publish_queue_policy_defaults() -> None:
    """Policy should default to manual mode."""

    assert publish_queue_policy(None) == {"auto_approve_enabled": False}


def test_merge_publish_queue_policy_patch() -> None:
    """Patch should merge into operator_settings bucket."""

    merged = merge_publish_queue_policy_patch({}, {"auto_approve_enabled": True})
    assert merged["publish_queue"]["auto_approve_enabled"] is True


def test_tenant_publish_queue_auto_approve_enabled() -> None:
    """Tenant flag should read from operator_settings."""

    tenant = SimpleNamespace(operator_settings={"publish_queue": {"auto_approve_enabled": True}})
    assert tenant_publish_queue_auto_approve_enabled(tenant) is True
