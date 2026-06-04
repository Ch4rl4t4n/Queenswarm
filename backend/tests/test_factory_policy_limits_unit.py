"""Unit tests for shared factory weekly build cap."""

from __future__ import annotations

from app.application.services.factory_policy_limits import (
    FACTORY_MAX_BUILDS_PER_WEEK_CAP,
    FACTORY_MAX_BUILDS_PER_WEEK_DEFAULT,
    clamp_max_builds_per_week,
)


def test_clamp_max_builds_per_week_defaults_invalid() -> None:
    assert clamp_max_builds_per_week(None) == FACTORY_MAX_BUILDS_PER_WEEK_DEFAULT
    assert clamp_max_builds_per_week("bad") == FACTORY_MAX_BUILDS_PER_WEEK_DEFAULT


def test_clamp_max_builds_per_week_bounds() -> None:
    assert clamp_max_builds_per_week(0) == 1
    assert clamp_max_builds_per_week(50) == 50
    assert clamp_max_builds_per_week(999) == FACTORY_MAX_BUILDS_PER_WEEK_CAP
    assert clamp_max_builds_per_week("25") == 25
