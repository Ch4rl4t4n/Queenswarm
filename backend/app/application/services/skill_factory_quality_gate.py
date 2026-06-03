"""Skill Factory quality gate — critic approval + sellable SKILL.md validation."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

import structlog

logger = structlog.get_logger(__name__)

_CRITIC_APPROVE_RE = re.compile(
    r"(?:critic\s+)?(?:verdict|decision|status)\s*:\s*approve|"
    r"verification\s+verdict\s*:\s*approved|"
    r"\bapprove\b.*(?:skill|pack|workflow)|"
    r"skill-factory-ready",
    re.IGNORECASE,
)
_CRITIC_REJECT_RE = re.compile(
    r"(?:critic\s+)?(?:verdict|decision|status)\s*:\s*reject|"
    r"verification\s+verdict\s*:\s*rejected|"
    r"\breject(?:ed|ion)\b",
    re.IGNORECASE,
)
_FRONTMATTER_NAME_RE = re.compile(r"^---\s*\nname:\s*.+\n", re.MULTILINE | re.IGNORECASE)
_FRONTMATTER_DESC_RE = re.compile(r"^description:\s*.+", re.MULTILINE | re.IGNORECASE)
_HEADING_RE = re.compile(r"^#\s+.+\S", re.MULTILINE)
_WORKFLOW_STEP_RE = re.compile(r"^\d+\.\s+.+\S", re.MULTILINE)


@dataclass
class FactoryQualityResult:
    """Outcome of factory session output validation."""

    passed: bool
    critic_approved: bool
    skill_valid: bool
    issues: list[str] = field(default_factory=list)
    skill_markdown: str = ""

    def to_payload(self) -> dict[str, Any]:
        """Serialize for forge suggestion payload."""

        return {
            "quality_gate_passed": self.passed,
            "critic_approved": self.critic_approved,
            "skill_valid": self.skill_valid,
            "issues": list(self.issues),
        }


def critic_approved_factory(critic_output: str) -> bool:
    """Return True when critic explicitly approved the skill pack."""

    text = critic_output.strip()
    if not text:
        return False
    if _CRITIC_REJECT_RE.search(text) and not _CRITIC_APPROVE_RE.search(text):
        return False
    return bool(_CRITIC_APPROVE_RE.search(text))


def validate_skill_markdown(skill_md: str) -> tuple[bool, list[str]]:
    """Validate SKILL.md meets agentskills.io + sellable workflow bar."""

    text = skill_md.strip()
    issues: list[str] = []
    if len(text) < 120:
        issues.append("too_short")
    if not _FRONTMATTER_NAME_RE.search(text):
        issues.append("missing_name_frontmatter")
    if not _FRONTMATTER_DESC_RE.search(text):
        issues.append("missing_description")
    if not _HEADING_RE.search(text):
        issues.append("missing_heading")
    workflow_steps = len(_WORKFLOW_STEP_RE.findall(text))
    if workflow_steps < 3:
        issues.append("needs_3_plus_workflow_steps")
    lower = text.lower()
    if "when to use" not in lower and "guardrail" not in lower:
        issues.append("missing_guardrails_or_when_to_use")
    return len(issues) == 0, issues


def evaluate_factory_outputs(
    *,
    skill_markdown: str,
    critic_output: str,
    coder_output: str,
) -> FactoryQualityResult:
    """Run full quality gate on extracted factory session outputs."""

    critic_ok = critic_approved_factory(critic_output)
    skill_ok, skill_issues = validate_skill_markdown(skill_markdown)
    issues: list[str] = []
    if not critic_ok:
        issues.append("critic_not_approved")
    issues.extend(skill_issues)
    passed = critic_ok and skill_ok and len(skill_markdown.strip()) >= 120

    if not passed:
        logger.info(
            "skill_factory.quality_gate_failed",
            agent_id="skill_factory",
            critic_approved=critic_ok,
            skill_valid=skill_ok,
            issues=issues,
            coder_len=len(coder_output.strip()),
        )

    return FactoryQualityResult(
        passed=passed,
        critic_approved=critic_ok,
        skill_valid=skill_ok,
        issues=issues,
        skill_markdown=skill_markdown.strip(),
    )


__all__ = [
    "FactoryQualityResult",
    "critic_approved_factory",
    "evaluate_factory_outputs",
    "validate_skill_markdown",
]
