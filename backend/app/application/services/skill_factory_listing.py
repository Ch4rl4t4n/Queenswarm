"""Gumroad-ready LISTING.md builder for Skill Factory tenant exports."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM

_FRONTMATTER_DESC_RE = re.compile(r"^description:\s*(.+)$", re.MULTILINE | re.IGNORECASE)
_HEADING_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


@dataclass
class FactoryListingContext:
    """Inputs for a sellable Gumroad/GitHub listing bundle."""

    niche: str = ""
    price_cents: int = 1900
    rationale: str = ""
    one_line_hook: str = ""
    video_preview_url: str | None = None
    listing_hook_source: str | None = None
    buyer_persona: str = ""


def _price_display(cents: int) -> str:
    return f"€{(cents / 100):.2f}"


def _tier_suggestions(cents: int) -> str:
    anchor = cents / 100
    starter = max(9.0, round(anchor * 0.5, 0))
    team = max(anchor, round(anchor * 1.5, 0))
    return f"€{starter:.0f} starter / €{anchor:.0f} pro / €{team:.0f} team"


def _extract_hook_from_skill_md(markdown: str, *, title: str) -> str:
    """Pull hook from SKILL frontmatter or first heading."""

    match = _FRONTMATTER_DESC_RE.search(markdown)
    if match:
        return match.group(1).strip().strip('"')[:240]
    heading = _HEADING_RE.search(markdown)
    if heading:
        return heading.group(1).strip()[:240]
    return f"Verified AI agent skill — {title}"[:240]


def _listing_preview_from_opportunity(opportunity: SkillOpportunityORM | None) -> tuple[str, str | None, str | None]:
    """Read Monid/listing preview refs stored on opportunity at approve time."""

    if opportunity is None:
        return "", None, None
    refs = list(opportunity.source_refs or [])
    hook = ""
    video_url: str | None = None
    source: str | None = None
    for item in refs:
        if not isinstance(item, dict):
            continue
        kind = str(item.get("kind") or "")
        if kind == "listing_preview":
            hook = str(item.get("hook") or item.get("excerpt") or "").strip()
            video_url = str(item.get("video_preview_url") or "").strip() or None
            source = str(item.get("source") or "monid")
        elif kind == "external_monid_discover" and not hook:
            hook = str(item.get("excerpt") or "")[:200]
    return hook, video_url, source


def listing_context_from_skill_and_opportunity(
    skill: TenantSkillORM,
    opportunity: SkillOpportunityORM | None,
    *,
    monid_hook: str | None = None,
    video_preview_url: str | None = None,
) -> FactoryListingContext:
    """Compose listing context from tenant skill + linked opportunity."""

    price_cents = int(opportunity.suggested_price_eur_cents) if opportunity else 1900
    niche = str(opportunity.niche if opportunity else "")
    rationale = str(opportunity.rationale if opportunity else skill.description or "")
    stored_hook, stored_video, source = _listing_preview_from_opportunity(opportunity)
    hook = (monid_hook or stored_hook or _extract_hook_from_skill_md(skill.markdown_body, title=skill.title)).strip()
    persona = niche or "Indie hackers and small teams shipping with Cursor / Claude agent skills"
    if rationale and len(rationale) > 40:
        persona = f"{persona}. Signal: {rationale[:280]}"

    return FactoryListingContext(
        niche=niche,
        price_cents=price_cents,
        rationale=rationale,
        one_line_hook=hook[:240],
        video_preview_url=video_preview_url or stored_video,
        listing_hook_source=source,
        buyer_persona=persona[:400],
    )


def build_factory_listing_md(
    *,
    skill: TenantSkillORM,
    slug: str,
    ctx: FactoryListingContext,
) -> str:
    """Gumroad-ready LISTING.md with hook, persona, tiers, video note, checklist."""

    desc = (skill.description or ctx.one_line_hook or "Verified agent skill from Skill Factory.").strip()
    price = _price_display(ctx.price_cents)
    tiers = _tier_suggestions(ctx.price_cents)
    tags = ", ".join(str(t) for t in (skill.keywords or [])[:8]) or "agent-skill, skill-factory, cursor"
    video_block = (
        f"Optional preview URL: {ctx.video_preview_url}\n\n"
        "Use for Gumroad preview video or TikTok teaser. Generate via Monid/Venice if not set."
        if ctx.video_preview_url
        else "Generate a 15–30s teaser (Monid/Venice) showing the workflow outcome — attach on Gumroad as preview video."
    )
    hook_source = f" (source: {ctx.listing_hook_source})" if ctx.listing_hook_source else ""

    return "\n".join(
        [
            f"# Listing — {skill.title}",
            "",
            "## One-line hook (Gumroad subtitle)",
            "",
            ctx.one_line_hook or desc[:240],
            hook_source,
            "",
            "## Price anchor",
            "",
            f"**{price}** — suggested tiers: {tiers}",
            "",
            "## Buyer persona",
            "",
            ctx.buyer_persona,
            "",
            "## Short description",
            "",
            desc[:500],
            "",
            "## Long description (paste into Gumroad body)",
            "",
            desc,
            "",
            "Built in **Queenswarm Skill Factory** — PRODUCT_MISSION workflow, critic APPROVE gate, simulation-first guardrails.",
            "",
            "### What you get",
            "",
            "- Cursor / Claude Code compatible `SKILL.md` (agentskills.io frontmatter)",
            "- `README.md` install guide + `tasks.prompt.md` runbook",
            "- `HIVE.md` context + verification metadata",
            "- This `LISTING.md` — copy-paste Gumroad listing",
            "",
            "### Install",
            "",
            "```bash",
            f"npx skills@latest add queenswarm/{slug}",
            "```",
            "",
            f"**Niche:** {ctx.niche or 'general productivity'}",
            "",
            f"Tags: {tags}",
            "",
            "## Video / social preview",
            "",
            video_block,
            "",
            "## Cover image prompt",
            "",
            f'Neon-dark hexagonal hive card, pollen amber glow, title "{skill.title[:48]}", '
            "cyberpunk bee motif, Gumroad thumbnail 1280×720, high contrast",
            "",
            "## Gumroad setup checklist",
            "",
            "- [ ] Create product at [gumroad.com/products/new](https://gumroad.com/products/new)",
            "- [ ] Title ← **One-line hook** section above",
            "- [ ] Price ← **Price anchor** (start at pro tier)",
            "- [ ] Description ← **Long description** section",
            "- [ ] Upload cover image (use prompt above)",
            "- [ ] Attach preview video if available",
            "- [ ] Deliverable: upload GitHub pack ZIP or link to repo folder",
            "- [ ] Publish → share link on X / LinkedIn / newsletter",
            "",
            "## FAQ",
            "",
            "**Who is this for?** " + (ctx.buyer_persona[:200] or "Teams using AI coding agents."),
            "",
            "**Do I need Queenswarm to use it?** No — copy `SKILL.md` into `.cursor/skills/` or use npx skills add.",
            "",
            "**Is it verified?** Yes — factory session passed quality gate before export.",
            "",
        ],
    )


__all__ = [
    "FactoryListingContext",
    "build_factory_listing_md",
    "listing_context_from_skill_and_opportunity",
]
