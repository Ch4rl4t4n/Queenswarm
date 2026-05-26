"""Recipe warmup — preload top-N verified recipes into Chroma cache.

Goal: when the operator (or Queen) submits a goal at 09:00, the Recipe Library
semantic search returns the right recipe instantly without a cold Chroma pull.
This task is run nightly (e.g. 04:00 UTC) by Celery beat.

This is intentionally **non-destructive and cheap**:
- Picks top-N verified recipes ordered by ``success_count`` (high-quality first).
- Issues a ``search_recipes_semantic`` query using the recipe's own name as the
  query string. This both warms Chroma's in-memory cache for that vector and
  validates that the embedding still resolves to its own catalog row.
- Touches ``last_used_at`` so cached recipes win recency tie-breakers next day.
- Does **not** execute the recipe's steps (no LLM cost, no live writes).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.recipe_chroma_bridge import search_recipes_semantic
from app.core.logging import get_logger
from app.infrastructure.persistence.models.recipe import Recipe

logger = get_logger(__name__)

DEFAULT_TOP_N = 20
WARMUP_QUERY_LIMIT = 5  # how many hits to fetch per warmup query


async def warmup_top_recipes(
    db: AsyncSession,
    *,
    top_n: int = DEFAULT_TOP_N,
) -> dict[str, Any]:
    """Touch + Chroma-query the top-N verified recipes; return summary stats."""

    stmt = (
        select(Recipe)
        .where(Recipe.is_deprecated.is_(False))
        .where(Recipe.verified_at.isnot(None))
        .order_by(Recipe.success_count.desc(), Recipe.avg_pollen_earned.desc())
        .limit(max(1, min(top_n, 100)))
    )
    recipes = list((await db.execute(stmt)).scalars())

    warmed = 0
    chroma_hits_total = 0
    chroma_misses = 0
    now = datetime.now(tz=UTC)

    for recipe in recipes:
        query = (recipe.name or "").strip()
        if not query:
            continue
        try:
            hits = await search_recipes_semantic(
                db,
                query=query,
                limit=WARMUP_QUERY_LIMIT,
            )
        except Exception as exc:  # noqa: BLE001 — best-effort warmup
            logger.warning(
                "recipe_warmup.search_failed",
                agent_id="recipe_warmup",
                swarm_id="",
                task_id=str(recipe.id),
                recipe_name=recipe.name,
                error=str(exc),
            )
            chroma_misses += 1
            continue
        if hits:
            chroma_hits_total += len(hits)
            warmed += 1
        else:
            chroma_misses += 1
        # Touch last_used_at so warmed recipes win recency boost in next search.
        recipe.last_used_at = now

    logger.info(
        "recipe_warmup.completed",
        agent_id="recipe_warmup",
        swarm_id="all",
        task_id="",
        recipes_considered=len(recipes),
        warmed=warmed,
        chroma_misses=chroma_misses,
        chroma_hits_total=chroma_hits_total,
    )
    return {
        "considered": len(recipes),
        "warmed": warmed,
        "chroma_misses": chroma_misses,
        "chroma_hits_total": chroma_hits_total,
        "run_at": now.isoformat(),
    }


__all__ = ["DEFAULT_TOP_N", "warmup_top_recipes"]
