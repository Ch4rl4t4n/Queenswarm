"""Content Pack Factory quality gate — critic approval + publish_pack validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import structlog

from app.application.services.publish_pack import (
    PublishPackArtifact,
    PublishPackValidationError,
    extract_publish_pack_json,
    validate_publish_pack,
)
from app.application.services.skill_factory_quality_gate import critic_approved_factory

logger = structlog.get_logger(__name__)


@dataclass
class ContentPackQualityResult:
    """Outcome of Content Pack Factory session output validation."""

    passed: bool
    critic_approved: bool
    pack_valid: bool
    issues: list[str] = field(default_factory=list)
    pack_payload: dict[str, Any] = field(default_factory=dict)
    listing_markdown: str = ""

    def to_payload(self) -> dict[str, Any]:
        """Serialize for forge suggestion payload."""

        return {
            "quality_gate_passed": self.passed,
            "critic_approved": self.critic_approved,
            "pack_valid": self.pack_valid,
            "issues": list(self.issues),
        }


def validate_content_pack_artifact(payload: dict[str, Any]) -> tuple[bool, list[str], PublishPackArtifact | None]:
    """Validate publish_pack JSON meets sellable bar."""

    issues: list[str] = []
    try:
        pack = validate_publish_pack(payload)
    except PublishPackValidationError as exc:
        return False, [str(exc)[:120]], None

    if not pack.simulate_only:
        issues.append("must_be_simulate_only")
    if len(pack.body.strip()) < 80:
        issues.append("body_too_short")
    if len(pack.snippets) < 3:
        issues.append("needs_3_plus_snippets")
    if not pack.cta.strip():
        issues.append("missing_cta")
    if not pack.hashtags:
        issues.append("missing_hashtags")
    return len(issues) == 0, issues, pack


def evaluate_content_pack_outputs(
    *,
    coder_output: str,
    critic_output: str,
    listing_markdown: str = "",
) -> ContentPackQualityResult:
    """Run full quality gate on extracted factory session outputs."""

    critic_ok = critic_approved_factory(critic_output)
    raw_pack = extract_publish_pack_json(f"{coder_output}\n\n{critic_output}")
    pack_ok = False
    pack_issues: list[str] = []
    validated: PublishPackArtifact | None = None
    pack_dict: dict[str, Any] = {}

    if raw_pack is None:
        pack_issues.append("missing_publish_pack_json")
    else:
        pack_ok, pack_issues, validated = validate_content_pack_artifact(raw_pack)
        if validated is not None:
            pack_dict = validated.model_dump()

    issues: list[str] = []
    if not critic_ok:
        issues.append("critic_not_approved")
    issues.extend(pack_issues)
    passed = critic_ok and pack_ok and bool(pack_dict)

    if not passed:
        logger.info(
            "content_pack_factory.quality_gate_failed",
            agent_id="content_pack_factory",
            critic_approved=critic_ok,
            pack_valid=pack_ok,
            issues=issues,
            coder_len=len(coder_output.strip()),
        )

    return ContentPackQualityResult(
        passed=passed,
        critic_approved=critic_ok,
        pack_valid=pack_ok,
        issues=issues,
        pack_payload=pack_dict,
        listing_markdown=listing_markdown.strip(),
    )


__all__ = [
    "ContentPackQualityResult",
    "evaluate_content_pack_outputs",
    "validate_content_pack_artifact",
]
