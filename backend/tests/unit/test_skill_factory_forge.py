"""Unit tests for Skill Factory forge extraction improvements."""

from __future__ import annotations

from app.application.services.skill_factory_forge import (
    extract_skill_markdown_from_outputs,
    is_fallback_factory_skill_markdown,
)


def test_is_fallback_factory_skill_markdown_detects_generic_name() -> None:
    md = "---\nname: skill-factory-output\ndescription: x\n---\n\n# Draft\n"
    assert is_fallback_factory_skill_markdown(md) is True


def test_extract_builds_structured_skill_from_session_when_no_fence() -> None:
    coder = "\n".join(
        [
            "Research shows demand for SEO pipelines.",
            "1. Gather SERP intel with guardrails",
            "2. Draft content simulate-first",
            "3. Critic APPROVE before publish",
        ],
    )
    md = extract_skill_markdown_from_outputs(
        coder_output=coder,
        critic_output="Critic verdict: APPROVE",
        goal="SEO pipeline",
        opportunity_title="SEO Content Pipeline",
        niche="seo-content",
    )
    assert "name: seo-content-pipeline" in md.lower() or "seo" in md.lower()
    assert is_fallback_factory_skill_markdown(md) is False
    assert "When to use" in md


def test_extract_prefers_fenced_skill_over_fallback() -> None:
    fenced = (
        "```markdown\n---\nname: niche-pack\ndescription: Real pack\n---\n\n"
        "# Niche\n\nWhen to use: weekly.\n\n1. A\n2. B\n3. C\n```"
    )
    md = extract_skill_markdown_from_outputs(
        coder_output=fenced,
        critic_output="Critic verdict: APPROVE",
        goal="test",
    )
    assert "name: niche-pack" in md
    assert is_fallback_factory_skill_markdown(md) is False
