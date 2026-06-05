"""Tests for library purge — remove reviewed skills without launch value."""

from __future__ import annotations

from app.application.services.skill_factory_library_purge import is_library_purge_eligible
from app.application.services.skill_library_sieve import compute_library_sieve_verdict
from app.application.services.skill_factory_sellable import SkillSellableAssessment


def test_is_library_purge_eligible_retire_verdict() -> None:
    assert is_library_purge_eligible(
        library_verdict="retire",
        factory_disposition=None,
        recommended_for_launch=False,
    )


def test_is_library_purge_eligible_deprioritize_verdict() -> None:
    assert is_library_purge_eligible(
        library_verdict="deprioritize",
        factory_disposition=None,
        recommended_for_launch=False,
    )


def test_is_library_purge_eligible_blocks_launch_ready() -> None:
    assert not is_library_purge_eligible(
        library_verdict="deprioritize",
        factory_disposition=None,
        recommended_for_launch=True,
    )


def test_is_library_purge_eligible_blocks_worth_retry_verdict() -> None:
    assert not is_library_purge_eligible(
        library_verdict="worth_retry",
        factory_disposition=None,
        recommended_for_launch=False,
    )


def test_sieve_rejected_low_score_is_deprioritize_purge_eligible() -> None:
    assessment = SkillSellableAssessment(
        tier="rejected",
        score=0.38,
        issues=["factory_draft_description"],
    )
    sieve = compute_library_sieve_verdict(assessment, attempt_count=0)
    assert sieve.verdict == "deprioritize"
    assert is_library_purge_eligible(
        library_verdict=sieve.verdict,
        factory_disposition=None,
        recommended_for_launch=assessment.recommended_for_launch,
    )


def test_sieve_many_attempts_low_score_is_retire_purge_eligible() -> None:
    assessment = SkillSellableAssessment(
        tier="rejected",
        score=0.37,
        issues=["fallback_skill_frontmatter", "factory_draft_description"],
    )
    sieve = compute_library_sieve_verdict(assessment, attempt_count=2)
    assert sieve.verdict == "retire"
    assert is_library_purge_eligible(
        library_verdict=sieve.verdict,
        factory_disposition=None,
        recommended_for_launch=False,
    )
