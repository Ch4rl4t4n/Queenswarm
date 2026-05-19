"""Premium skill marketplace policy helpers (no Stripe/DB imports)."""

from __future__ import annotations

from app.core.config import settings
from app.infrastructure.persistence.models.recipe import Recipe

PREMIUM_TAG = "premium"


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
    if "premium-9" in tags:
        return 900
    return int(settings.skill_export_premium_price_eur_cents)


__all__ = ["PREMIUM_TAG", "is_premium_recipe", "resolve_skill_price_cents"]
