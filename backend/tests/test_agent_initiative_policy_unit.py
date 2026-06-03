"""Unit tests for tenant agent initiative auto-approve policy."""

from __future__ import annotations

from types import SimpleNamespace

from app.application.services.agent_initiative_policy import (
    agent_initiative_policy,
    merge_agent_initiative_policy_patch,
    tenant_agent_initiative_auto_approve_enabled,
)


def test_agent_initiative_policy_defaults() -> None:
    """Policy defaults to manual mode."""

    assert agent_initiative_policy(None)["auto_approve_enabled"] is False
    assert agent_initiative_policy(None)["include_high_risk"] is False


def test_merge_agent_initiative_policy_patch() -> None:
    """Patch persists under operator_settings.agent_initiative."""

    merged = merge_agent_initiative_policy_patch({}, {"auto_approve_enabled": True, "include_high_risk": True})
    assert merged["agent_initiative"]["auto_approve_enabled"] is True
    assert merged["agent_initiative"]["include_high_risk"] is True


def test_tenant_agent_initiative_auto_approve_enabled() -> None:
    """Helper reads tenant bucket."""

    tenant = SimpleNamespace(operator_settings={"agent_initiative": {"auto_approve_enabled": True}})
    assert tenant_agent_initiative_auto_approve_enabled(tenant) is True
