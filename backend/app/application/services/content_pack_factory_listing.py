"""Gumroad-ready LISTING.md builder for Content Pack Factory exports."""

from __future__ import annotations

from dataclasses import dataclass

from app.infrastructure.persistence.models.content_pack_opportunity import ContentPackOpportunityORM
from app.infrastructure.persistence.models.tenant_content_pack import TenantContentPackORM


@dataclass
class ContentPackListingContext:
    """Inputs for a sellable Gumroad listing bundle."""

    niche: str = ""
    price_cents: int = 1900
    rationale: str = ""
    one_line_hook: str = ""
    channel: str = "instagram"
    buyer_persona: str = ""


def _price_display(cents: int) -> str:
    return f"€{(cents / 100):.2f}"


def listing_context_from_pack_and_opportunity(
    pack: TenantContentPackORM,
    opportunity: ContentPackOpportunityORM | None,
) -> ContentPackListingContext:
    """Derive listing context from stored pack + optional opportunity."""

    payload = dict(pack.pack_payload or {})
    hook = str(payload.get("title") or pack.title)[:240]
    niche = opportunity.niche if opportunity else ""
    price = int(opportunity.suggested_price_eur_cents) if opportunity else 1900
    rationale = opportunity.rationale if opportunity else pack.description
    return ContentPackListingContext(
        niche=niche,
        price_cents=price,
        rationale=rationale[:1200],
        one_line_hook=hook,
        channel=str(pack.channel or payload.get("channel") or "instagram"),
        buyer_persona=f"Creators and operators selling {niche or pack.title} content packs",
    )


def build_content_pack_listing_md(
    *,
    pack: TenantContentPackORM,
    slug: str,
    ctx: ContentPackListingContext,
) -> str:
    """Render Gumroad/GitHub LISTING.md for one verified content pack."""

    payload = dict(pack.pack_payload or {})
    snippet_count = len(payload.get("snippets") or [])
    lines = [
        f"# {pack.title}",
        "",
        f"> {ctx.one_line_hook or pack.description[:240]}",
        "",
        "## Product",
        f"- **Slug:** `{slug}`",
        f"- **Channel:** {ctx.channel}",
        f"- **Price anchor:** {_price_display(ctx.price_cents)}",
        f"- **Simulate-only:** yes (verified before export)",
        f"- **Snippets included:** {snippet_count}",
        "",
        "## Buyer persona",
        ctx.buyer_persona or "Content operators who need ready-to-sell social packs with guardrails.",
        "",
        "## What's inside",
        "- Verified publish_pack JSON (simulate-first)",
        "- Human-readable PACK.md preview",
        "- Channel-specific hooks, hashtags, and CTA",
        "- 3+ social snippets ready for scheduling tools",
        "",
        "## Niche rationale",
        ctx.rationale[:2000] if ctx.rationale else pack.description[:2000],
        "",
        "## Gumroad listing copy (paste-ready)",
        "",
        "### Title",
        pack.title[:200],
        "",
        "### Short description",
        (ctx.one_line_hook or pack.description)[:500],
        "",
        "### Tags",
        ", ".join(list(pack.keywords or [])[:12]) or "content-pack, social, simulate-first",
        "",
        "### Pricing suggestion",
        f"Launch at {_price_display(ctx.price_cents)} — bundle 30-day calendar upsell at 2× anchor.",
        "",
        "## Quality gate",
        "- Critic verdict APPROVE required before library publish",
        "- publish_pack schema validated (no secrets, simulate_only=true)",
        "- Minimum 3 snippets + CTA + hashtags",
        "",
    ]
    return "\n".join(lines)


__all__ = [
    "ContentPackListingContext",
    "build_content_pack_listing_md",
    "listing_context_from_pack_and_opportunity",
]
