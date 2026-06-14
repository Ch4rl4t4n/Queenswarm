"""Unit tests for AOS1 harness project profiles."""

from __future__ import annotations

from types import SimpleNamespace

from app.application.services.harness_project_profiles import (
    compose_harness_profiles_state,
    get_active_harness_profile,
    persist_active_harness_profile,
)


def test_persist_active_profile() -> None:
    tenant = SimpleNamespace(operator_settings={})
    persist_active_harness_profile(tenant, "factory")
    assert tenant.operator_settings["harness_profiles"]["active_profile_id"] == "factory"
    active = get_active_harness_profile(tenant)
    assert active.profile_id == "factory"
    state = compose_harness_profiles_state(tenant)
    assert state.active_profile_id == "factory"
    assert len(state.profiles) >= 5


def test_investments_profile_defaults() -> None:
    tenant = SimpleNamespace(operator_settings={"harness_profiles": {"active_profile_id": "investments"}})
    active = get_active_harness_profile(tenant)
    assert active.profile_id == "investments"
    assert active.cbo_lane == "research"
    assert "grill-me" in active.skill_slugs
