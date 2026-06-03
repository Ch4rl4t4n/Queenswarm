"""Skill Factory unit tests."""

from __future__ import annotations

from app.application.services.skill_factory_research import _score_opportunity
from app.application.services.skill_factory_service import build_factory_session_goal, slugify_skill_name
from app.application.services.skill_market_intel import _demand_keyword_hits, _normalize_hits


def test_slugify_skill_name() -> None:
    assert slugify_skill_name("Newsletter Growth Loop!") == "newsletter-growth-loop"
    assert slugify_skill_name("   ") == "skill-factory-output"


def test_score_opportunity_composite_in_range() -> None:
    demand, competition, buildability, composite, rationale = _score_opportunity(
        niche="newsletter growth automation",
        hive_hits=3,
        existing_count=1,
    )
    assert 0.0 <= demand <= 1.0
    assert 0.0 <= competition <= 1.0
    assert 0.0 <= buildability <= 1.0
    assert 0.0 <= composite <= 1.0
    assert "HiveMind" in rationale


def test_build_factory_session_goal_includes_niche() -> None:
    from types import SimpleNamespace

    opp = SimpleNamespace(
        niche="SEO blog pipeline",
        title="Skill pack: SEO",
        rationale="High demand signal",
    )
    goal = build_factory_session_goal(opportunity=opp, price_cents=1900)
    assert "SEO blog pipeline" in goal
    assert "€19.00" in goal


def test_skill_market_intel_demand_keywords() -> None:
    assert _demand_keyword_hits("cursor skill pack for newsletter automation") >= 2


def test_skill_market_intel_deduplicates_hits() -> None:
    rows = _normalize_hits(
        [
            {"id": "a", "document": "cursor skill template"},
            {"id": "a", "document": "cursor skill template duplicate"},
            {"document": "unique n8n workflow"},
        ],
    )
    assert len(rows) == 2
