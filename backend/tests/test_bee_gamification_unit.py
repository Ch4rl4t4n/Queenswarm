"""Tests for bee gamification badge rules."""

from __future__ import annotations

from app.application.services.bee_gamification import compute_agent_badges, list_badge_catalog


def test_compute_agent_badges_gold_tier() -> None:
    badges = compute_agent_badges(
        agent_role="evaluator",
        verified_pollen=120.0,
        total_pollen=200.0,
        performance_score=0.92,
        verified_task_count=8,
    )
    ids = {b["id"] for b in badges}
    assert "pollen_gold" in ids
    assert "rapid_loop" in ids
    assert "imitation_star" in ids


def test_compute_agent_badges_rookie_only() -> None:
    badges = compute_agent_badges(
        agent_role="scraper",
        verified_pollen=1.0,
        total_pollen=1.0,
        performance_score=0.5,
        verified_task_count=1,
    )
    assert [b["id"] for b in badges] == ["verified_rookie"]


def test_list_badge_catalog_non_empty() -> None:
    catalog = list_badge_catalog()
    assert len(catalog) >= 6
    assert catalog[0]["emoji"]
