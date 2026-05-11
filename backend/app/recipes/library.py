"""Recipe Library facade — semantic search + verified autosave hooks (Phase E)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.recipe import Recipe
from app.schemas.recipes_search import RecipeSemanticHit
from app.schemas.recipes_write import RecipeCreateBody
from app.services.recipe_chroma_bridge import search_recipes_semantic
from app.services.recipe_write import create_recipe_entry

logger = get_logger(__name__)


async def semantic_search_catalog(
    session: AsyncSession,
    *,
    query: str,
    limit: int,
    task_id: str,
) -> list[RecipeSemanticHit]:
    """Rank Recipe Library embeddings with optional Postgres hydration."""

    return await search_recipes_semantic(
        session,
        query=query,
        limit=limit,
        task_id=task_id,
    )


async def autosave_verified_workflow(
    session: AsyncSession,
    body: RecipeCreateBody,
    *,
    swarm_id: str,
    task_id: str,
    created_by_agent_id: uuid.UUID | None,
) -> Recipe:
    """Promote a verified template into the catalog with Chroma mirroring (when enabled)."""

    data = body.model_dump()
    if created_by_agent_id is not None:
        data["created_by_agent_id"] = created_by_agent_id
    payload = RecipeCreateBody.model_validate(data)

    recipe = await create_recipe_entry(
        session,
        payload,
        swarm_id=swarm_id,
        task_id=task_id,
    )
    logger.info(
        "recipe_library.autosave",
        recipe_id=str(recipe.id),
        recipe_name=recipe.name,
        task_id=task_id,
    )
    return recipe


__all__ = ["autosave_verified_workflow", "semantic_search_catalog"]
