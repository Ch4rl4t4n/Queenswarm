"""Unit tests for selective HiveMind recall helpers."""

from __future__ import annotations

from app.application.services.platform_features import resolve_platform_features
from app.application.services.selective_recall import (
    effective_prompt_char_budget,
    normalize_recall_mode,
    rank_vector_hits,
    score_vector_similarity,
)


def test_normalize_recall_mode_defaults_to_selective() -> None:
    assert normalize_recall_mode(None) == "selective"
    assert normalize_recall_mode("FULL") == "full"


def test_rank_vector_hits_prunes_low_similarity() -> None:
    hits = [
        {"document": "strong", "distance": 0.1},
        {"document": "weak", "distance": 0.92},
    ]
    kept, pruned = rank_vector_hits(hits, max_hits=4, min_similarity=0.55)
    assert len(kept) == 1
    assert pruned == 1
    assert kept[0]["similarity"] >= 0.55


def test_effective_prompt_char_budget_selective_uses_cap() -> None:
    budget = effective_prompt_char_budget(
        recall_mode="selective",
        tenant_budget=0,
        settings_max_prompt=4000,
        selective_max_chars=2400,
    )
    assert budget == 2400


def test_commercial_pro_enables_selective_recall_feature() -> None:
    features = resolve_platform_features(
        platform_mode="commercial",
        is_admin=False,
        subscription_tier="pro",
    )
    assert features["selective_recall"] is True


def test_score_vector_similarity_from_distance() -> None:
    assert score_vector_similarity(0.2) == 0.8
