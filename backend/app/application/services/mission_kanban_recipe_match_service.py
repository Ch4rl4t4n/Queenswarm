"""FP1 — Recipe cosine matching for Mission Kanban triage dispatch."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.recipe_chroma_bridge import search_recipes_semantic
from app.application.services.recipe_match_config import RecipeMatchConfigResponse, build_recipe_match_config
from app.common.schemas.recipes_search import RecipeSemanticHit
from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger(__name__)


class MissionKanbanRecipeMatchOut(BaseModel):
    """Semantic recipe hits for a triage prompt before dispatch."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    query: str = ""
    hits: list[RecipeSemanticHit] = Field(default_factory=list)
    match_config: RecipeMatchConfigResponse = Field(default_factory=build_recipe_match_config)
    operator_hint: str = "Pick a verified recipe to bind workflow decomposition on dispatch."


async def compose_mission_kanban_recipe_match(
    session: AsyncSession,
    *,
    query: str,
    limit: int = 5,
) -> MissionKanbanRecipeMatchOut:
    """Return cosine-ranked verified recipes for a triage prompt."""

    trimmed = query.strip()
    config = build_recipe_match_config()
    if not settings.mission_kanban_recipe_match_enabled:
        return MissionKanbanRecipeMatchOut(enabled=False, query=trimmed, match_config=config)
    if len(trimmed) < 8:
        return MissionKanbanRecipeMatchOut(
            enabled=True,
            query=trimmed,
            match_config=config,
            operator_hint="Enter at least 8 characters to search the Recipe Library.",
        )

    cap = max(1, min(limit, 12))
    hits = await search_recipes_semantic(
        session,
        query=trimmed,
        limit=cap,
        task_id="mission_kanban_recipe_match",
    )
    _logger.info(
        "mission_kanban.recipe_match",
        agent_id="operator_hub",
        hit_count=len(hits),
        query_chars=len(trimmed),
    )
    return MissionKanbanRecipeMatchOut(
        enabled=True,
        query=trimmed,
        hits=hits,
        match_config=config,
    )


def recipe_match_from_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Serialize recipe match metadata stored on a dispatched triage row."""

    raw_id = payload.get("matching_recipe_id")
    raw_name = payload.get("matching_recipe_name")
    if not raw_id and not raw_name:
        return None
    similarity_raw = payload.get("matching_recipe_similarity")
    similarity = float(similarity_raw) if isinstance(similarity_raw, (int, float)) else 0.92
    return {
        "name": str(raw_name or "Recipe"),
        "similarity": max(0.0, min(1.0, similarity)),
        "postgres_recipe_id": str(raw_id) if raw_id else None,
    }


__all__ = [
    "MissionKanbanRecipeMatchOut",
    "compose_mission_kanban_recipe_match",
    "recipe_match_from_payload",
]
