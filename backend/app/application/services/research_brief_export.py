"""Research Brief Export Factory — B2B deliverable bundles from verified briefs."""

from __future__ import annotations

import json
import re
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.application.services.research_bee import ResearchBriefOut

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def research_brief_slug(title: str) -> str:
    """Filesystem-safe slug from brief title."""

    raw = _SLUG_RE.sub("-", title.strip().lower()).strip("-")
    return (raw[:80] or "research-brief")


class ResearchBriefExportFile(BaseModel):
    """One file in a research brief export bundle."""

    model_config = ConfigDict(extra="forbid")

    path: str
    content: str


class ResearchBriefExportMeta(BaseModel):
    """Metadata for one research brief export."""

    model_config = ConfigDict(extra="ignore")

    brief_id: str
    slug: str
    title: str
    source_type: str
    word_count: int
    topic_tags: list[str] = Field(default_factory=list)
    suggested_price_eur_cents: int = 2900
    generated_at: datetime | None = None


class ResearchBriefExportResponse(BaseModel):
    """Full export payload returned by API."""

    model_config = ConfigDict(extra="ignore")

    meta: ResearchBriefExportMeta
    files: list[ResearchBriefExportFile] = Field(default_factory=list)


def _suggested_price_cents(brief: ResearchBriefOut) -> int:
    """Heuristic B2B price from brief depth."""

    if brief.word_count >= 4000:
        return 4900
    if brief.word_count >= 1500:
        return 2900
    return 1900


def build_research_brief_listing_md(*, brief: ResearchBriefOut, slug: str, price_cents: int) -> str:
    """Gumroad-ready LISTING.md for a research brief pack."""

    price_eur = price_cents / 100
    hook = brief.summary[:240] if brief.summary else f"Verified research brief — {brief.title}"
    tags = ", ".join(brief.topic_tags[:12]) or "research, intelligence, B2B"
    return "\n".join(
        [
            f"# {brief.title}",
            "",
            f"> {hook}",
            "",
            "## Product",
            f"- **Slug:** `{slug}`",
            f"- **Source:** {brief.source_label}",
            f"- **Word count:** {brief.word_count}",
            f"- **Price anchor:** €{price_eur:.2f}",
            "",
            "## Buyer persona",
            "Consultants, founders, and agency operators who need cite-ready intelligence packs.",
            "",
            "## What's inside",
            "- Executive summary (1-page)",
            "- Full structured BRIEF.md",
            "- Key points + notable quotes",
            "- Topic tags for HiveMind / Notion import",
            "",
            "## Gumroad listing copy",
            "",
            "### Title",
            f"{brief.title[:200]} — Research Brief Pack",
            "",
            "### Short description",
            hook[:500],
            "",
            "### Tags",
            tags,
            "",
            "### Pricing suggestion",
            f"Launch at €{price_eur:.2f} — team license at 2× for agencies.",
            "",
        ],
    )


def build_research_brief_export_bundle(brief: ResearchBriefOut) -> ResearchBriefExportResponse:
    """Assemble B2B export bundle from one verified research brief."""

    slug = research_brief_slug(brief.title)
    folder = slug
    price_cents = _suggested_price_cents(brief)
    listing_md = build_research_brief_listing_md(brief=brief, slug=slug, price_cents=price_cents)

    executive = "\n".join(
        [
            f"# Executive Summary — {brief.title}",
            "",
            brief.summary,
            "",
            "## Key takeaways",
            *[f"- {point}" for point in brief.key_points[:6]],
            "",
            f"**Source:** {brief.source_label}",
            f"**Tags:** {', '.join(brief.topic_tags[:8]) or 'n/a'}",
        ],
    )

    meta_json = json.dumps(
        {
            "slug": slug,
            "source_type": brief.source_type,
            "word_count": brief.word_count,
            "topic_tags": list(brief.topic_tags or []),
            "price_eur_cents": price_cents,
            "ingest_route": brief.ingest_route,
        },
        indent=2,
        sort_keys=True,
    )

    readme = "\n".join(
        [
            f"# {brief.title}",
            "",
            "B2B research brief export from Queenswarm Research Bee.",
            "",
            "## Files",
            "- `BRIEF.md` — full structured brief",
            "- `EXECUTIVE_SUMMARY.md` — 1-page client deliverable",
            "- `LISTING.md` — Gumroad paste-ready listing",
            "- `meta.json` — pricing and source metadata",
            "",
        ],
    )

    files = [
        ResearchBriefExportFile(path=f"{folder}/BRIEF.md", content=brief.markdown + "\n"),
        ResearchBriefExportFile(path=f"{folder}/EXECUTIVE_SUMMARY.md", content=executive),
        ResearchBriefExportFile(path=f"{folder}/LISTING.md", content=listing_md),
        ResearchBriefExportFile(path=f"{folder}/meta.json", content=meta_json + "\n"),
        ResearchBriefExportFile(path=f"{folder}/README.md", content=readme),
    ]

    meta = ResearchBriefExportMeta(
        brief_id=str(uuid.uuid4()),
        slug=slug,
        title=brief.title,
        source_type=brief.source_type,
        word_count=brief.word_count,
        topic_tags=list(brief.topic_tags or []),
        suggested_price_eur_cents=price_cents,
        generated_at=brief.generated_at,
    )
    return ResearchBriefExportResponse(meta=meta, files=files)


def export_response_to_dict(response: ResearchBriefExportResponse) -> dict[str, Any]:
    """Serialize export response for JSON API."""

    return {
        "meta": response.meta.model_dump(mode="json"),
        "files": [item.model_dump() for item in response.files],
    }


__all__ = [
    "ResearchBriefExportFile",
    "ResearchBriefExportMeta",
    "ResearchBriefExportResponse",
    "build_research_brief_export_bundle",
    "export_response_to_dict",
    "research_brief_slug",
]
