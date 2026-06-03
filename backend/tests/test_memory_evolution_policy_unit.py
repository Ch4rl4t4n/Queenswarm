"""Unit tests for memory evolution tenant policy."""

from __future__ import annotations

from types import SimpleNamespace

from app.application.services.memory_evolution_policy import (
    memory_evolution_policy,
    merge_memory_evolution_policy_patch,
    tenant_memory_evolution_auto_approve_enabled,
)


def test_memory_evolution_policy_defaults() -> None:
    """Policy should default to manual mode."""

    assert memory_evolution_policy(None) == {
        "auto_approve_enabled": False,
        "include_high_importance": False,
    }


def test_merge_memory_evolution_policy_patch() -> None:
    """Patch should merge into operator_settings bucket."""

    merged = merge_memory_evolution_policy_patch(
        {},
        {"auto_approve_enabled": True, "include_high_importance": True},
    )
    assert merged["memory_evolution"]["auto_approve_enabled"] is True
    assert merged["memory_evolution"]["include_high_importance"] is True


def test_tenant_memory_evolution_auto_approve_enabled() -> None:
    """Tenant flag should read from operator_settings."""

    tenant = SimpleNamespace(
        operator_settings={"memory_evolution": {"auto_approve_enabled": True}},
    )
    assert tenant_memory_evolution_auto_approve_enabled(tenant) is True
