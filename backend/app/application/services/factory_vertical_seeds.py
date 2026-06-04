"""Monetization vertical niche seeds — SSOT for Skill + Content Pack factories."""

from __future__ import annotations

from typing import Literal

FactoryLane = Literal["skill", "content_pack"]

# Tier A — highest Gumroad/GitHub demand signals (Cursor, n8n, agency ops)
SKILL_FACTORY_VERTICAL_SEEDS: tuple[str, ...] = (
    "Cursor IDE agent skill packs for SaaS teams",
    "n8n automation templates for agencies",
    "SEO content pipeline with simulate-first guardrails",
    "competitor monitoring skill for B2B founders",
    "newsletter growth loop with verified outcomes",
    "Gumroad-ready AI workflow listing packs",
    "lead research + outreach simulate-first",
    "social content calendar with brand guardrails",
    "Claude Code PR review skill for indie dev teams",
    "customer support triage skill with guardrails",
    "real estate listing copy skill pack",
    "dental clinic appointment reminder automation",
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
)

# Curated starter set (8) for one-click operator preset
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
