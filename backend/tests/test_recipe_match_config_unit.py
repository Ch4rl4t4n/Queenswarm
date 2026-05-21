"""Tests for recipe match config exposure."""

from __future__ import annotations

import pytest

from app.application.services.recipe_match_config import build_recipe_match_config


def test_build_recipe_match_config_defaults_include_threshold(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.application.services.recipe_match_config.settings.recipe_library_match_threshold",
        0.85,
        raising=False,
    )
    payload = build_recipe_match_config()
    assert payload.match_threshold == 0.85
    assert payload.hybrid_scoring_enabled is True
