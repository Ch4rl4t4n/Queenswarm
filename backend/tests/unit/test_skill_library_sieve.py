"""Library sieve verdict unit tests."""

from __future__ import annotations

from app.application.services.skill_factory_sellable import SkillSellableAssessment
from app.application.services.skill_library_sieve import compute_library_sieve_verdict


def test_sieve_launch_for_sellable() -> None:
    assessment = SkillSellableAssessment(
        tier="sellable",
        score=0.82,
        issues=[],
        recommended_for_launch=True,
    )
    out = compute_library_sieve_verdict(assessment)
    assert out.verdict == "launch"


def test_sieve_retire_after_two_attempts_low_score() -> None:
    assessment = SkillSellableAssessment(
        tier="rejected",
        score=0.37,
        issues=["critic_not_approved", "needs_3_plus_workflow_steps"],
    )
    out = compute_library_sieve_verdict(assessment, attempt_count=2)
    assert out.verdict == "retire"


def test_sieve_worth_retry_fixable_rejected() -> None:
    assessment = SkillSellableAssessment(
        tier="rejected",
        score=0.48,
        issues=["critic_not_approved"],
    )
    out = compute_library_sieve_verdict(assessment, attempt_count=1)
    assert out.verdict == "worth_retry"
