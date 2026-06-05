"""Library sieve — operator verdict for keep vs fix vs retire."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.application.services.skill_factory_sellable import SkillSellableAssessment

LibraryVerdict = Literal["launch", "worth_retry", "deprioritize", "retire"]


class LibrarySieveVerdict(BaseModel):
    """One-line operator decision for a library skill."""

    model_config = ConfigDict(extra="ignore")

    verdict: LibraryVerdict
    reason: str
    action: str


def compute_library_sieve_verdict(
    assessment: SkillSellableAssessment,
    *,
    attempt_count: int = 0,
    disposition: str | None = None,
) -> LibrarySieveVerdict:
    """Recommend whether to launch, retry, deprioritize, or retire a library skill."""

    if disposition == "retired":
        return LibrarySieveVerdict(
            verdict="retire",
            reason="Niche retired — excluded from research and rebuild.",
            action="Un-retire only if market signal changed.",
        )
    if disposition == "deprioritized":
        return LibrarySieveVerdict(
            verdict="deprioritize",
            reason="Operator deprioritized — factory research scores this lower.",
            action="Smart rebuild if you still believe in the niche.",
        )

    score = assessment.score
    issues = list(assessment.issues)
    score_pct = f"{round(score * 100)}%"

    if assessment.recommended_for_launch or (
        assessment.tier == "sellable" and score >= 0.72
    ):
        return LibrarySieveVerdict(
            verdict="launch",
            reason=f"Sellable harness ({score_pct}) — critic + structure OK.",
            action="Export harness pack → Gumroad Launch queue.",
        )

    if assessment.tier == "draft" and score >= 0.65:
        top = ", ".join(issues[:2]) if issues else "minor fixes"
        return LibrarySieveVerdict(
            verdict="worth_retry",
            reason=f"Near launch ({score_pct}) — fix: {top}.",
            action="Smart rebuild or Run eval to confirm before export.",
        )

    if attempt_count >= 2 and score < 0.45:
        return LibrarySieveVerdict(
            verdict="retire",
            reason=f"{attempt_count} rebuild attempts, score {score_pct} — factory cost likely wasted.",
            action="Retire niche — focus seeds on higher-demand niches.",
        )

    if score < 0.35 and ("generic_factory_slug" in issues or "fallback_skill_frontmatter" in issues):
        return LibrarySieveVerdict(
            verdict="retire",
            reason=f"Generic/fallback draft ({score_pct}) — weak buyer signal.",
            action="Retire unless you have proven Gumroad demand for this niche.",
        )

    if assessment.tier == "rejected":
        if score >= 0.42:
            top = ", ".join(issues[:3]) if issues else "quality gate"
            return LibrarySieveVerdict(
                verdict="worth_retry",
                reason=f"Rejected but fixable ({score_pct}): {top}.",
                action="Smart rebuild — learnings injected into factory goal.",
            )
        return LibrarySieveVerdict(
            verdict="deprioritize",
            reason=f"Low score ({score_pct}) after factory run — weak harness.",
            action="Deprioritize or Retire — don't keep in active queue.",
        )

    return LibrarySieveVerdict(
        verdict="worth_retry",
        reason=f"Draft tier ({score_pct}) — not launch-ready yet.",
        action="Run eval inline, then Smart rebuild if FAIL.",
    )


__all__ = ["LibrarySieveVerdict", "LibraryVerdict", "compute_library_sieve_verdict"]
