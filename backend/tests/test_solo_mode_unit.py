"""Unit tests for solo operator mode feature preset."""

from __future__ import annotations

import pytest

from app.application.services.billing import TIER_FREE
from app.application.services.platform_features import resolve_platform_features
from app.application.services.solo_mode import (
    SOLO_CORE_FEATURES,
    SOLO_HIDDEN_FEATURES,
    apply_solo_mode_overrides,
)
from app.core.config import settings


def test_apply_solo_mode_hides_multitenant_b2b() -> None:
    resolved = {key: True for key in SOLO_HIDDEN_FEATURES | SOLO_CORE_FEATURES}
    merged = apply_solo_mode_overrides(resolved, is_admin=True)
    for key in SOLO_HIDDEN_FEATURES:
        assert merged[key] is False
    for key in SOLO_CORE_FEATURES:
        assert merged[key] is True
    assert merged["accounts_admin"] is False
    assert merged["command_center_admin"] is True
    assert merged["platform_features_admin"] is True


def test_apply_solo_mode_optional_respects_environment_override() -> None:
    resolved = {"foragers": True}
    merged = apply_solo_mode_overrides(
        resolved,
        policy_overrides={("foragers", "environment"): True},
        is_admin=True,
    )
    assert merged["foragers"] is True


def test_resolve_platform_features_applies_solo_preset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "solo_mode_enabled", True)
    features = resolve_platform_features(
        platform_mode="internal",
        is_admin=True,
        subscription_tier=TIER_FREE,
    )
    assert features["billing_settings"] is True
    assert features["skills_marketplace"] is True
    assert features["ugc_content_engine"] is True
    assert features["foragers"] is True
    assert features["platform_features_admin"] is True
    assert features["command_center_admin"] is True
