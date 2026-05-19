"""Unit coverage for recipe hybrid scoring helpers."""

from __future__ import annotations

import pytest

from app.application.services.recipe_chroma_bridge import (
    _hybrid_similarity,
    _merge_graph_signals,
    _recipe_success_rate,
)


def test_hybrid_similarity_blends_vector_and_graph(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.application.services.recipe_chroma_bridge.settings.recipe_hybrid_scoring_enabled",
        True,
    )
    monkeypatch.setattr(
        "app.application.services.recipe_chroma_bridge.settings.recipe_hybrid_vector_weight",
        0.85,
    )
    monkeypatch.setattr(
        "app.application.services.recipe_chroma_bridge.settings.recipe_hybrid_graph_weight",
        0.15,
    )

    score = _hybrid_similarity(vector_similarity=0.8, graph_signal=1.0)
    assert score == pytest.approx(0.83, rel=1e-3)


def test_recipe_success_rate_from_counts() -> None:
    from app.infrastructure.persistence.models.recipe import Recipe

    recipe = Recipe(
        name="demo",
        workflow_template={"steps": []},
        success_count=8,
        fail_count=2,
    )
    assert _recipe_success_rate(recipe) == pytest.approx(0.8)


def test_merge_graph_signals_picks_max() -> None:
    assert _merge_graph_signals(0.2, 0.9, 0.4) == pytest.approx(0.9)
