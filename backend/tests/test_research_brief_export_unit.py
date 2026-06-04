"""Research Brief Export Factory unit tests."""

from __future__ import annotations

from datetime import UTC, datetime

from app.application.services.research_bee import ResearchBriefOut
from app.application.services.research_brief_export import (
    build_research_brief_export_bundle,
    research_brief_slug,
)


def _sample_brief() -> ResearchBriefOut:
    return ResearchBriefOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        source_type="paste",
        source_label="Operator notes",
        title="Competitor landscape for B2B SaaS",
        summary="Three incumbents dominate with high switching costs.",
        key_points=[
            "Incumbent A holds 40% share in mid-market.",
            "Buyers cite integration fatigue as top churn driver.",
            "Open-source alternatives gaining in dev-led teams.",
        ],
        notable_quotes=["We need simulate-first before any publish."],
        topic_tags=["saas", "competitor", "b2b"],
        word_count=2200,
        markdown="# Competitor landscape\n\nSummary here.",
    )


def test_research_brief_slug() -> None:
    assert research_brief_slug("Hello World!") == "hello-world"


def test_build_research_brief_export_bundle_files() -> None:
    bundle = build_research_brief_export_bundle(_sample_brief())
    paths = {f.path for f in bundle.files}
    assert any(p.endswith("BRIEF.md") for p in paths)
    assert any(p.endswith("LISTING.md") for p in paths)
    assert any(p.endswith("EXECUTIVE_SUMMARY.md") for p in paths)
    assert bundle.meta.suggested_price_eur_cents == 2900
