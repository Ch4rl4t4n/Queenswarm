"""Unit tests for Skill Factory Gumroad listing builder."""

from __future__ import annotations

from types import SimpleNamespace

from app.application.services.skill_factory_listing import (
    build_factory_listing_md,
    listing_context_from_skill_and_opportunity,
)


def test_build_factory_listing_md_includes_gumroad_checklist() -> None:
    skill = SimpleNamespace(
        title="Newsletter Growth Pack",
        description="Automate newsletter loops with guardrails.",
        keywords=["newsletter", "skill-factory"],
        markdown_body="---\ndescription: Hook line here\n---\n\n# Newsletter Growth",
    )
    ctx = listing_context_from_skill_and_opportunity(
        skill,  # type: ignore[arg-type]
        SimpleNamespace(
            niche="newsletter growth",
            rationale="High demand",
            suggested_price_eur_cents=1900,
            source_refs=[],
        ),
    )
    md = build_factory_listing_md(skill=skill, slug="newsletter-growth", ctx=ctx)  # type: ignore[arg-type]
    assert "Gumroad setup checklist" in md
    assert "€19.00" in md
    assert "One-line hook" in md


def test_listing_context_uses_monid_preview_ref() -> None:
    skill = SimpleNamespace(
        title="Test Skill",
        description="Desc",
        keywords=[],
        markdown_body="# Test",
    )
    opp = SimpleNamespace(
        niche="cursor skills",
        rationale="Intel",
        suggested_price_eur_cents=2900,
        source_refs=[
            {
                "kind": "listing_preview",
                "hook": "Monid hook for Gumroad",
                "source": "monid",
                "video_preview_url": "https://cdn.example.com/teaser.mp4",
            },
        ],
    )
    ctx = listing_context_from_skill_and_opportunity(skill, opp)  # type: ignore[arg-type]
    assert ctx.one_line_hook == "Monid hook for Gumroad"
    assert ctx.video_preview_url == "https://cdn.example.com/teaser.mp4"
    assert ctx.price_cents == 2900
