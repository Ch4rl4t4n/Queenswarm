"""Unit tests for forager spawn approval policy."""

from app.application.services.forager_spawn_policy import (
    forager_spawn_policy,
    merge_forager_spawn_policy_patch,
)


def test_forager_spawn_policy_defaults_off() -> None:
    """Auto-spawn manual approval is default."""

    policy = forager_spawn_policy(None)
    assert policy["auto_spawn_auto_approve_enabled"] is False


def test_merge_forager_spawn_policy_patch() -> None:
    """Tenant operator_settings stores forager auto approve toggle."""

    merged = merge_forager_spawn_policy_patch({}, {"auto_spawn_auto_approve_enabled": True})
    assert merged["foragers"]["auto_spawn_auto_approve_enabled"] is True
