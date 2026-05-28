"""Unit tests for platform feature resolution."""

from __future__ import annotations

import pytest

from app.application.services.billing import TIER_FREE, TIER_PRO
from app.application.services.platform_features import (
    is_route_allowed,
    normalize_platform_mode,
    resolve_platform_features,
    route_feature_key,
)


def test_normalize_platform_mode_defaults_to_internal() -> None:
    assert normalize_platform_mode(None) == "internal"
    assert normalize_platform_mode("commercial") == "commercial"
    assert normalize_platform_mode("unknown") == "internal"


def test_internal_admin_gets_factory_features() -> None:
    features = resolve_platform_features(
        platform_mode="internal",
        is_admin=True,
        subscription_tier=TIER_FREE,
    )
    assert features["skills_export_factory"] is True
    assert features["product_mission"] is True
    assert features["foragers"] is True
    assert features["billing_settings"] is False


def test_commercial_pro_hides_factory_but_keeps_marketplace() -> None:
    features = resolve_platform_features(
        platform_mode="commercial",
        is_admin=False,
        subscription_tier=TIER_PRO,
    )
    assert features["skills_export_factory"] is False
    assert features["product_mission"] is False
    assert features["skills_marketplace"] is True
    assert features["billing_settings"] is True
    assert features["foragers"] is True


def test_commercial_free_blocks_pro_tier_features() -> None:
    features = resolve_platform_features(
        platform_mode="commercial",
        is_admin=False,
        subscription_tier=TIER_FREE,
    )
    assert features["skills_marketplace"] is False
    assert features["external_projects"] is False
    assert features["ballroom"] is False
    assert features["recipes"] is False
    assert features["foragers"] is False


def test_policy_override_takes_precedence() -> None:
    features = resolve_platform_features(
        platform_mode="internal",
        is_admin=True,
        subscription_tier=TIER_PRO,
        policy_overrides={("foragers", "internal"): True},
    )
    assert features["foragers"] is True


def test_environment_kill_switch() -> None:
    features = resolve_platform_features(
        platform_mode="commercial",
        is_admin=False,
        subscription_tier=TIER_PRO,
        policy_overrides={("dashboard", "environment"): False},
    )
    assert features["dashboard"] is False


def test_build_feature_matrix_shape() -> None:
    from app.application.services.platform_features import build_feature_matrix

    matrix = build_feature_matrix()
    assert len(matrix["profiles"]) >= 4
    assert len(matrix["rows"]) > 0
    assert "cells" in matrix["rows"][0]


def test_preview_features_for_profile_commercial_pro() -> None:
    from app.application.services.platform_features import preview_features_for_profile

    preview = preview_features_for_profile("commercial_pro")
    assert preview["platform_mode"] == "commercial"
    assert preview["subscription_tier"] == TIER_PRO
    assert preview["features"]["skills_marketplace"] is True
    assert preview["features"]["skills_export_factory"] is False
    assert "skills_marketplace" in preview["enabled_features"]


def test_preview_features_rejects_environment_column() -> None:
    from app.application.services.platform_features import preview_features_for_profile

    with pytest.raises(ValueError, match="Environment"):
        preview_features_for_profile("environment")


def test_route_feature_key_and_guard() -> None:
    assert route_feature_key("/foragers") == "foragers"
    assert route_feature_key("/settings/security") == "settings"
    assert route_feature_key("/settings/platform") == "platform_features_admin"

    features = resolve_platform_features(platform_mode="internal", is_admin=True, subscription_tier=TIER_PRO)
    assert is_route_allowed("/foragers", features=features) is True
    assert is_route_allowed("/integrations", features=features) is True
