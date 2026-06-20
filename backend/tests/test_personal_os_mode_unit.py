"""Unit tests for Personal OS deployment preset."""

from __future__ import annotations

import pytest

from app.application.services.billing import TIER_FREE
from app.application.services.personal_os_mode import (
    PERSONAL_OS_CORE_FEATURES,
    PERSONAL_OS_HIDDEN_FEATURES,
    apply_personal_os_overrides,
    personal_os_mission_home_revenue_widgets_enabled,
    personal_os_mission_home_advanced_strips_enabled,
    personal_os_revenue_approvals_enabled,
    personal_os_skill_factory_commercial_enabled,
)
from app.application.services.platform_features import resolve_platform_features
from app.core.config import settings


def test_apply_personal_os_hides_revenue_and_beta() -> None:
    resolved = {key: True for key in PERSONAL_OS_HIDDEN_FEATURES | PERSONAL_OS_CORE_FEATURES}
    merged = apply_personal_os_overrides(resolved, is_admin=True)
    for key in PERSONAL_OS_HIDDEN_FEATURES:
        assert merged[key] is False
    for key in PERSONAL_OS_CORE_FEATURES:
        assert merged[key] is True
    assert merged["accounts_admin"] is False
    assert merged["command_center_admin"] is True


def test_personal_os_mission_home_revenue_widgets_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "personal_os_mode_enabled", True)
    assert personal_os_mission_home_revenue_widgets_enabled() is False
    assert personal_os_revenue_approvals_enabled() is False
    assert personal_os_mission_home_advanced_strips_enabled() is False


def test_personal_os_revenue_approvals_enabled_when_not_personal_os(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "personal_os_mode_enabled", False)
    assert personal_os_revenue_approvals_enabled() is True


def test_personal_os_skill_factory_commercial_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "personal_os_mode_enabled", True)
    assert personal_os_skill_factory_commercial_enabled() is False


def test_resolve_platform_features_applies_personal_os_preset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "solo_mode_enabled", True)
    monkeypatch.setattr(settings, "personal_os_mode_enabled", True)
    features = resolve_platform_features(
        platform_mode="internal",
        is_admin=True,
        subscription_tier=TIER_FREE,
    )
    assert features["billing_settings"] is False
    assert features["content_pack_factory"] is False
    assert features["skills_export_factory"] is False
    assert features["agents"] is True
    assert features["skill_factory"] is True
    assert features["foragers"] is True
