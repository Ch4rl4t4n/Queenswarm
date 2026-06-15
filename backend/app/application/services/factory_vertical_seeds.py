"""Monetization vertical niche seeds — SSOT for Skill + Content Pack factories."""

from __future__ import annotations

from typing import Literal

from app.application.services.factory_product_presets import (
    MIDDLETON_LOCAL_BIZ_5_WORKERS_SEEDS,
    PIGFORD_SOLO_FOUNDER_SEEDS,
)

FactoryLane = Literal["skill", "content_pack"]

# Tier S — analysis-driven hero bundles (Pigford + Middleton)
SKILL_FACTORY_HERO_SEEDS: tuple[str, ...] = (
    *PIGFORD_SOLO_FOUNDER_SEEDS[:2],
    *MIDDLETON_LOCAL_BIZ_5_WORKERS_SEEDS[:2],
)

# Tier A — highest Gumroad/GitHub demand signals (Cursor, n8n, agency ops)
SKILL_FACTORY_VERTICAL_SEEDS: tuple[str, ...] = (
    *SKILL_FACTORY_HERO_SEEDS,
    *PIGFORD_SOLO_FOUNDER_SEEDS[2:],
    *MIDDLETON_LOCAL_BIZ_5_WORKERS_SEEDS[2:],
    "Cursor IDE agent skill packs for SaaS teams",
    "n8n automation templates for agencies",
    "SEO content pipeline with simulate-first guardrails",
    "competitor monitoring skill for B2B founders",
    "newsletter growth loop with verified outcomes",
    "Gumroad-ready AI workflow listing packs",
    "lead research + outreach simulate-first",
    "social content calendar with brand guardrails",
    "customer support triage skill with guardrails",
    "real estate listing copy skill pack",
    "dental clinic appointment reminder automation",
    # Wave 1–2 — MK6 catalog depth
    "MCP connector starter kit for agent teams",
    "Eval-as-a-service harness for AI skills",
    "Shopify product description skill pack",
    "Amazon listing optimization skill",
    "YouTube SEO title generator skill",
    "Podcast show notes automation skill",
    "Cold email sequence skill for B2B SaaS",
    "Upwork proposal writer skill pack",
    "Notion knowledge base migration skill",
    "Zapier to n8n migration runbook skill",
    "Freelancer invoice chase automation skill",
    "Course launch email sequence skill",
    "Community Discord moderation skill pack",
    "HR onboarding checklist skill for startups",
    "Legal contract summary skill with guardrails",
    "Stripe subscription dunning recovery skill",
    "GitHub issue triage skill for maintainers",
    "Slack standup summarizer skill pack",
    "Google Ads RSA copy skill for local biz",
    "Airtable CRM enrichment skill pack",
)

# Tier A — sellable social/content packs (simulate-first)
CONTENT_PACK_VERTICAL_SEEDS: tuple[str, ...] = (
    "30-day Instagram content calendar for coaches",
    "LinkedIn thought-leadership pack for B2B SaaS",
    "TikTok hook library for e-commerce brands",
    "Newsletter launch sequence for indie hackers",
    "Twitter/X thread pack for crypto analysts",
    "Facebook ad copy variations for local services",
    "Blog + social repurpose pack for SEO agencies",
    "Brand voice content kit for wellness creators",
    "Real estate agent Reels script pack",
    "SaaS product launch announcement pack",
    "Webinar promo snippet pack for consultants",
    "Black Friday email + social combo pack",
    # Wave 1 — MK6 catalog depth (marketing roadmap)
    "Pinterest pin batch for home decor brands",
    "YouTube Shorts script pack for fitness coaches",
    "Email win-back sequence for SaaS churn",
    "Product Hunt launch day social pack",
    "Case study template pack for agencies",
    "Podcast promo clip captions pack",
    "Holiday promo bundle for e-commerce",
    "Local restaurant menu social pack",
    "Nonprofit fundraising email pack",
    "Real estate open house promo pack",
    "SaaS onboarding email drip pack",
    "Webinar follow-up nurture pack",
    "Customer testimonial request templates",
    "Affiliate recruitment outreach pack",
    "Course upsell email combo pack",
    "Membership site launch announcement pack",
    "Eval-as-a-service demo invite copy pack",
    "MCP starter kit marketing one-pager pack",
)

# Curated starter set (8) for one-click operator preset — hero + proven niches
SKILL_FACTORY_STARTER_SEEDS: tuple[str, ...] = SKILL_FACTORY_VERTICAL_SEEDS[:8]
CONTENT_PACK_STARTER_SEEDS: tuple[str, ...] = CONTENT_PACK_VERTICAL_SEEDS[:8]


def vertical_seeds_for_lane(lane: FactoryLane) -> tuple[str, ...]:
    """Return all vertical seeds for one factory lane."""

    if lane == "content_pack":
        return CONTENT_PACK_VERTICAL_SEEDS
    return SKILL_FACTORY_VERTICAL_SEEDS


def starter_seeds_for_lane(lane: FactoryLane) -> tuple[str, ...]:
    """Return recommended starter preset for operator onboarding."""

    if lane == "content_pack":
        return CONTENT_PACK_STARTER_SEEDS
    return SKILL_FACTORY_STARTER_SEEDS


def vertical_seeds_payload() -> dict[str, list[str]]:
    """API payload for factory UIs."""

    return {
        "skill_factory": list(SKILL_FACTORY_VERTICAL_SEEDS),
        "content_pack_factory": list(CONTENT_PACK_VERTICAL_SEEDS),
        "skill_factory_starter": list(SKILL_FACTORY_STARTER_SEEDS),
        "content_pack_starter": list(CONTENT_PACK_STARTER_SEEDS),
    }


__all__ = [
    "CONTENT_PACK_STARTER_SEEDS",
    "CONTENT_PACK_VERTICAL_SEEDS",
    "SKILL_FACTORY_STARTER_SEEDS",
    "SKILL_FACTORY_VERTICAL_SEEDS",
    "starter_seeds_for_lane",
    "vertical_seeds_for_lane",
    "vertical_seeds_payload",
]
