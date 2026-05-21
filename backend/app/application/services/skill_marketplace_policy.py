"""Premium skill marketplace policy helpers (no Stripe/DB imports)."""

from __future__ import annotations

from app.core.config import settings
from app.infrastructure.persistence.models.recipe import Recipe

PREMIUM_TAG = "premium"
UGC_TAG = "ugc"

ALLOWED_UGC_PRICE_TIERS_CENTS: tuple[int, ...] = (900, 1900, 2900, 4900)


def platform_cut_bps() -> int:
    """Return configured platform cut in basis points (default 25%)."""

    return int(settings.skill_marketplace_platform_cut_bps)


def platform_cut_display(bps: int | None = None) -> str:
    """Human-readable platform cut percentage."""

    value = bps if bps is not None else platform_cut_bps()
    return f"{value / 100:.0f}%"


def price_tag_for_cents(cents: int) -> str:
    """Map checkout price to recipe topic tag."""

    mapping = {
        900: "premium-9",
        1900: "premium-19",
        2900: "premium-29",
        4900: "premium-49",
    }
    tag = mapping.get(cents)
    if tag is None:
        raise ValueError(f"Unsupported UGC price tier: {cents}")
    return tag


def apply_ugc_premium_tags(recipe: Recipe, *, price_eur_cents: int) -> None:
    """Tag recipe as UGC premium listing after curator approval."""

    tags = [str(t).strip() for t in (recipe.topic_tags or []) if str(t).strip()]
    normalized = {t.lower() for t in tags}
    price_tag = price_tag_for_cents(price_eur_cents)
    for required in (UGC_TAG, PREMIUM_TAG, price_tag):
        if required not in normalized:
            tags.append(required)
    recipe.topic_tags = tags


def is_premium_recipe(recipe: Recipe) -> bool:
    """Return whether export requires purchase on free tier (premium-tagged recipes)."""

    tags = {str(t).strip().lower() for t in (recipe.topic_tags or [])}
    return PREMIUM_TAG in tags or any(tag.startswith("premium-") for tag in tags)


def resolve_skill_price_cents(recipe: Recipe) -> int:
    """Resolve checkout price from recipe topic tags."""

    tags = {str(t).strip().lower() for t in (recipe.topic_tags or [])}
    if "premium-49" in tags:
        return 4900
    if "premium-29" in tags:
        return 2900
    if "premium-19" in tags:
        return 1900
    if "premium-9" in tags:
        return 900
    return int(settings.skill_export_premium_price_eur_cents)


__all__ = [
    "ALLOWED_UGC_PRICE_TIERS_CENTS",
    "PREMIUM_TAG",
    "UGC_TAG",
    "apply_ugc_premium_tags",
    "is_premium_recipe",
    "platform_cut_bps",
    "platform_cut_display",
    "price_tag_for_cents",
    "resolve_skill_price_cents",
]
