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


def test_listing_context_falls_back_when_hook_is_pipe_only() -> None:
    skill = SimpleNamespace(
        title="Crypto Sentiment Alerts",
        description="Real-time crypto sentiment monitoring skill pack.",
        keywords=[],
        markdown_body="# Crypto Sentiment Alerts\n",
    )
    opp = SimpleNamespace(
        niche="crypto sentiment",
        rationale="High demand",
        suggested_price_eur_cents=1900,
        source_refs=[{"kind": "listing_preview", "hook": "|", "source": "monid"}],
    )
    ctx = listing_context_from_skill_and_opportunity(skill, opp)  # type: ignore[arg-type]
    assert ctx.one_line_hook == "Real-time crypto sentiment monitoring skill pack."
    assert "|" not in ctx.one_line_hook


def test_listing_context_uses_multiline_frontmatter_description() -> None:
    skill = SimpleNamespace(
        title="Crypto Sentiment Alerts",
        description="Skill Factory session completed — approve to publish into Library.",
        keywords=["crypto"],
        markdown_body=(
            "---\n"
            "name: crypto-sentiment-alerts\n"
            "description: |\n"
            "  Real-time sentiment alerts for top 10 cryptos.\n"
            "  Detects bullish/bearish flips and sends Discord alerts.\n"
            "---\n\n"
            "# Crypto Sentiment Alerts\n"
        ),
    )
    ctx = listing_context_from_skill_and_opportunity(
        skill,  # type: ignore[arg-type]
        SimpleNamespace(
            niche="crypto sentiment",
            rationale="High demand",
            suggested_price_eur_cents=1900,
            source_refs=[],
        ),
    )
    assert "Real-time sentiment alerts" in ctx.one_line_hook
    assert "Skill Factory session completed" not in ctx.one_line_hook


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
