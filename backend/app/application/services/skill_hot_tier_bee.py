"""SkillHotTierBee — Karpathy-style on-demand skill loading (verified recipes only)."""

from __future__ import annotations

import re
import uuid

import structlog
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.persistence.models.recipe import Recipe

logger = structlog.get_logger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]{4,}", re.IGNORECASE)
_STOP = frozenset(
    {
        "about",
        "after",
        "also",
        "been",
        "from",
        "have",
        "into",
        "project",
        "queenswarm",
        "session",
        "supervisor",
        "that",
        "this",
        "with",
        "your",
    },
)


def _goal_tokens(goal: str) -> set[str]:
    return {tok.lower() for tok in _TOKEN_RE.findall(goal) if tok.lower() not in _STOP}


def _recipe_tokens(recipe: Recipe) -> set[str]:
    parts = [recipe.name or "", recipe.description or ""]
    tags = recipe.topic_tags if isinstance(recipe.topic_tags, list) else []
    parts.extend(str(tag) for tag in tags)
    return {tok.lower() for tok in _TOKEN_RE.findall(" ".join(parts)) if tok.lower() not in _STOP}


def _score_recipe(goal_tokens: set[str], recipe: Recipe) -> float:
    if not goal_tokens:
        return 0.0
    recipe_tokens = _recipe_tokens(recipe)
    if not recipe_tokens:
        return 0.0
    overlap = len(goal_tokens & recipe_tokens)
    if overlap == 0:
        return 0.0
    return overlap / max(len(goal_tokens), 1)


async def fetch_verified_recipes(session: AsyncSession, *, limit: int = 24) -> list[Recipe]:
    """Load recent verified recipes for hot-tier matching."""

    cap = max(4, min(limit, 48))
    result = await session.execute(
        select(Recipe)
        .where(Recipe.verified_at.isnot(None))
        .order_by(desc(Recipe.success_count), desc(Recipe.updated_at))
        .limit(cap),
    )
    return list(result.scalars().all())


async def render_skill_hot_tier_block(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    goal: str,
) -> str:
    """Return markdown block with top matching verified recipes — never full library dump."""

    if not settings.skill_hot_tier_enabled:
        return ""
    goal_clean = goal.strip()
    if len(goal_clean) < 12:
        return ""

    goal_tokens = _goal_tokens(goal_clean)
    if not goal_tokens:
        return ""

    recipes = await fetch_verified_recipes(session, limit=int(settings.skill_hot_tier_pool_size))
    ranked: list[tuple[float, Recipe]] = []
    for recipe in recipes:
        score = _score_recipe(goal_tokens, recipe)
        if score >= float(settings.skill_hot_tier_min_score):
            ranked.append((score, recipe))
    ranked.sort(key=lambda row: (-row[0], row[1].name or ""))
    top = [recipe for _, recipe in ranked[: int(settings.skill_hot_tier_max_recipes)]]
    if not top:
        return ""

    lines = [
        "=== SKILL HOT TIER (Karpathy — load on demand) ===",
        f"Matched {len(top)} verified recipe(s) for this session goal.",
        "",
    ]
    for recipe in top:
        summary = (recipe.description or "").strip()
        if len(summary) > 220:
            summary = f"{summary[:217]}…"
        lines.append(f"### {recipe.name}")
        if summary:
            lines.append(summary)
        if recipe.topic_tags:
            lines.append(f"_Tags: {', '.join(str(t) for t in recipe.topic_tags[:6])}_")
        lines.append("")

    lines.append("=== END SKILL HOT TIER ===")
    block = "\n".join(lines).strip()
    logger.info(
        "skill_hot_tier.rendered",
        agent_id="skill_hot_tier_bee",
        swarm_id=str(tenant_id),
        task_id="",
        recipe_count=len(top),
    )
    return block


__all__ = ["render_skill_hot_tier_block"]
