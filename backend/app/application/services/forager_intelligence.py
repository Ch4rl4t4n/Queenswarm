"""Forager Intelligence Loop — propose skill/MCP/doc refresh candidates."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.repo_root import resolve_repo_root
from app.application.services.supervisor.skills import SkillLibrary
from app.infrastructure.connectors.phase3.catalog import iter_phase3_templates


def run_intelligence_scan() -> dict[str, Any]:
    """Scan skills + Phase3 MCP templates + harness docs; return proposals (no mutations).

    Returns:
        Proposal list for operator review or future forager automation.
    """
    repo_root = resolve_repo_root()
    lib = SkillLibrary()
    proposals: list[dict[str, Any]] = []

    # Skills without keywords may benefit from reference-mode upgrade (Langfuse insight)
    for slug in lib.list_available_slugs():
        skill = lib.load(slug)
        if skill is None:
            continue
        if not skill.keywords:
            proposals.append(
                {
                    "kind": "skill_keywords",
                    "target": slug,
                    "priority": "medium",
                    "rationale": "Add keywords for SkillLibrary goal matching and reference-mode routing.",
                },
            )

    # Phase3 templates not yet represented as dedicated skills
    template_ids = {item.template_id for item in iter_phase3_templates()}
    skill_slugs = set(lib.list_available_slugs())
    for template_id in sorted(template_ids):
        slug_hint = template_id.replace("_", "-")
        if slug_hint not in skill_slugs and template_id not in skill_slugs:
            proposals.append(
                {
                    "kind": "mcp_preset_skill",
                    "target": template_id,
                    "priority": "low",
                    "rationale": "Consider one-click marketplace preset doc in skills/patterns/.",
                },
            )

    harness_docs = [
        repo_root / "docs" / "QUEENSWARM_DESIGN_PATTERNS.md",
        repo_root / "docs" / "HARNESS_SELF_MAINTAINING_ANALYSIS.md",
        repo_root / "docs" / "ROUNDTABLESPACE_MAY2026_INSIGHTS.md",
    ]
    for path in harness_docs:
        if not path.is_file():
            proposals.append(
                {
                    "kind": "missing_harness_doc",
                    "target": str(path.relative_to(repo_root)),
                    "priority": "high",
                    "rationale": "Harness doc missing from repo — restore for AI Layer consistency.",
                },
            )

    patterns_readme = repo_root / "backend" / "app" / "skills" / "patterns" / "README.md"
    if not patterns_readme.is_file():
        proposals.append(
            {
                "kind": "patterns_index",
                "target": "backend/app/skills/patterns/README.md",
                "priority": "medium",
                "rationale": "Pattern skill index helps Pattern Router discoverability.",
            },
        )

    return {
        "scanned_at": datetime.now(tz=UTC).isoformat(),
        "proposal_count": len(proposals),
        "proposals": proposals[:40],
    }


__all__ = ["run_intelligence_scan"]
