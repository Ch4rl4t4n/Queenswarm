"""Verified premium recipe seeds for the skills export marketplace."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.workflows.templates import SEED_WORKFLOWS
from app.infrastructure.persistence.models.recipe import Recipe

logger = get_logger(__name__)

PREMIUM_MARKETPLACE_SEEDS: tuple[dict[str, Any], ...] = (
    {
        "name": "Premium — Crypto Sentiment Swarm",
        "description": (
            "Verified 4-step swarm: scrape YouTube crypto sentiment, evaluate claims, "
            "simulate portfolio paths, export trading memo. Simulation-gated export bundle."
        ),
        "seed_key": "CRYPTO_ACKIE",
        "topic_tags": ["premium", "crypto", "trading", "simulation"],
        "success_count": 12,
        "fail_count": 2,
        "avg_pollen_earned": 48.0,
    },
    {
        "name": "Premium — Blog Launch Pipeline",
        "description": (
            "Research clusters → outline → draft → publish checklist. Battle-tested content "
            "workflow exported as Cursor/Claude SKILL.md + HIVE.md."
        ),
        "seed_key": "BLOG_POST",
        "topic_tags": ["premium-29", "content", "blog", "seo"],
        "success_count": 9,
        "fail_count": 1,
        "avg_pollen_earned": 36.0,
    },
    {
        "name": "Premium — Newsletter Growth Loop",
        "description": (
            "Audience scrape, CAN-SPAM compliance pass, subject-line simulation. "
            "One-time unlock for verified newsletter automation recipe."
        ),
        "seed_key": "NEWSLETTER",
        "topic_tags": ["premium-9", "newsletter", "email", "growth"],
        "success_count": 7,
        "fail_count": 0,
        "avg_pollen_earned": 22.0,
    },
)


def _workflow_template(seed_key: str) -> dict[str, Any]:
    """Build workflow JSON from bundled seed definitions."""

    blob = SEED_WORKFLOWS.get(seed_key)
    if blob is None:
        return {"seed_key": seed_key, "steps": []}
    return {"seed_key": seed_key, "steps": blob.get("steps", [])}


FACTORY_RECIPE_SEEDS: tuple[dict[str, Any], ...] = (
    {
        "name": "Product Mission — Revenue Swarm",
        "description": (
            "Ballroom playbook: niche → verified workflow → skill export → publish on GitHub, Gumroad, "
            "and optional premium unlock. Free factory template for operators."
        ),
        "seed_key": "PRODUCT_MISSION",
        "topic_tags": ["factory", "product", "monetize", "publish"],
        "success_count": 15,
        "fail_count": 1,
        "avg_pollen_earned": 55.0,
    },
)


async def load_premium_marketplace_seeds(session: AsyncSession) -> int:
    """Insert verified premium marketplace recipes when missing (idempotent by name).

    Args:
        session: Async SQLAlchemy session — caller commits.

    Returns:
        Count of newly inserted Recipe rows.
    """

    inserted = 0
    verified_at = datetime.now(tz=UTC)
    all_specs = (*PREMIUM_MARKETPLACE_SEEDS, *FACTORY_RECIPE_SEEDS)
    for spec in all_specs:
        name = str(spec["name"])
        existing = await session.scalar(
            select(func.count()).select_from(Recipe).where(Recipe.name == name),
        )
        if existing and int(existing) > 0:
            continue

        seed_key = str(spec["seed_key"])
        recipe = Recipe(
            name=name,
            description=str(spec.get("description") or ""),
            topic_tags=list(spec.get("topic_tags") or ["premium"]),
            workflow_template=_workflow_template(seed_key),
            success_count=int(spec.get("success_count") or 5),
            fail_count=int(spec.get("fail_count") or 0),
            avg_pollen_earned=float(spec.get("avg_pollen_earned") or 20.0),
            embedding_id=None,
            created_by_agent_id=None,
            verified_at=verified_at,
            last_used_at=verified_at,
            is_deprecated=False,
        )
        session.add(recipe)
        inserted += 1
        logger.info(
            "premium_marketplace_seed.inserted",
            recipe_name=name,
            seed_key=seed_key,
        )

    if inserted:
        await session.flush()
    return inserted


__all__ = ["FACTORY_RECIPE_SEEDS", "PREMIUM_MARKETPLACE_SEEDS", "load_premium_marketplace_seeds"]
