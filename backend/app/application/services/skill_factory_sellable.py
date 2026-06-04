"""Classify tenant skills for external sales (Gumroad / GitHub launch queue)."""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.application.services.skill_factory_quality_gate import validate_skill_markdown
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM

_GENERIC_SLUGS = frozenset({"skill-factory-draft", "skill-factory-output"})
_FALLBACK_NAME_MARKERS = ("name: skill-factory-output", "name: skill-factory-draft")
_DRAFT_DESCRIPTION_MARKERS = (
    "quality warnings",
    "review critic verdict",
    "draft from skill factory session",
)
_SUFFIX_DUP_RE = re.compile(r"-\d+$")


class SkillSellableAssessment(BaseModel):
    """Launch-readiness view for one tenant skill."""

    model_config = ConfigDict(extra="ignore")

    tier: str  # sellable | draft | rejected
    score: float = Field(ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)
    recommended_for_launch: bool = False
    quality_gate_passed: bool | None = None
    critic_approved: bool | None = None


def _slug_base(slug: str) -> str:
    """Strip numeric suffix from deduped factory slugs."""

    return _SUFFIX_DUP_RE.sub("", slug.strip().lower())


def assess_tenant_skill_sellable(
    skill: TenantSkillORM,
    *,
    forge_quality: dict[str, Any] | None = None,
) -> SkillSellableAssessment:
    """Score skill for Gumroad launch without requiring forge row in memory."""

    slug = skill.slug.strip().lower()
    base = _slug_base(slug)
    issues: list[str] = []
    description = (skill.description or "").strip().lower()
    body_lower = (skill.markdown_body or "").lower()

    if base in _GENERIC_SLUGS:
        issues.append("generic_factory_slug")
    if any(marker in body_lower for marker in _FALLBACK_NAME_MARKERS):
        issues.append("fallback_skill_frontmatter")
    if any(marker in description for marker in _DRAFT_DESCRIPTION_MARKERS):
        issues.append("factory_draft_description")
    if slug != base:
        issues.append("duplicate_niche_suffix")

    quality_gate_passed: bool | None = None
    critic_approved: bool | None = None
    if forge_quality:
        if "quality_gate_passed" in forge_quality:
            quality_gate_passed = bool(forge_quality.get("quality_gate_passed"))
            if quality_gate_passed is False:
                issues.append("forge_quality_gate_failed")
        if "critic_approved" in forge_quality:
            critic_approved = bool(forge_quality.get("critic_approved"))
            if critic_approved is False:
                issues.append("critic_not_approved")

    skill_ok, skill_issues = validate_skill_markdown(skill.markdown_body or "")
    if not skill_ok:
        issues.extend(skill_issues)

    if skill.verified_at is None:
        issues.append("not_verified")

    # Score: start at 1.0, penalize issues
    score = 1.0
    score -= 0.35 if "generic_factory_slug" in issues else 0.0
    score -= 0.30 if "fallback_skill_frontmatter" in issues else 0.0
    score -= 0.25 if "factory_draft_description" in issues else 0.0
    score -= 0.20 if "forge_quality_gate_failed" in issues else 0.0
    score -= 0.15 if "critic_not_approved" in issues else 0.0
    score -= 0.08 * len(
        [
            i
            for i in issues
            if i
            not in {
                "duplicate_niche_suffix",
                "generic_factory_slug",
                "fallback_skill_frontmatter",
                "factory_draft_description",
                "forge_quality_gate_failed",
                "critic_not_approved",
            }
        ]
    )
    score = max(0.0, min(1.0, score))

    if score >= 0.72 and skill_ok and base not in _GENERIC_SLUGS and "fallback_skill_frontmatter" not in issues:
        tier = "sellable"
    elif score >= 0.4:
        tier = "draft"
    else:
        tier = "rejected"

    recommended = (
        tier == "sellable"
        and score >= 0.75
        and quality_gate_passed is not False
        and critic_approved is not False
    )

    return SkillSellableAssessment(
        tier=tier,
        score=round(score, 3),
        issues=issues,
        recommended_for_launch=recommended,
        quality_gate_passed=quality_gate_passed,
        critic_approved=critic_approved,
    )


def launch_queue_sort_key(item: dict[str, Any]) -> tuple[float, str]:
    """Sort launch queue rows by score desc then title."""

    return (-float(item.get("sellable_score") or 0.0), str(item.get("title") or ""))


def forge_quality_from_payload(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Extract quality gate fields from verified_skill_forge proposal payload."""

    if not payload:
        return None
    out: dict[str, Any] = {}
    for key in ("quality_gate_passed", "critic_approved", "skill_valid", "issues"):
        if key in payload:
            out[key] = payload[key]
    return out or None


__all__ = [
    "SkillSellableAssessment",
    "assess_tenant_skill_sellable",
    "forge_quality_from_payload",
    "launch_queue_sort_key",
]
