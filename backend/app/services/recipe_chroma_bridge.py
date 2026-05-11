"""Bridge Chroma cosine recall to Postgres Recipe rows for imitation dashboards."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chroma_client import RECIPE_LIBRARY_COLLECTION, semantic_search
from app.core.config import settings
from app.core.logging import get_logger
from app.models.recipe import Recipe
from app.schemas.recipes_catalog import RecipeCatalogItem
from app.schemas.recipes_search import RecipeSemanticHit

logger = get_logger(__name__)

_PREVIEW_CHARS = 2000


def _try_parse_recipe_uuid(metadata: dict[str, Any]) -> uuid.UUID | None:
    """Best-effort UUID extraction from heterogeneous Chroma metadata keys."""

    for key in ("postgres_recipe_id", "recipe_id", "postgres_id"):
        raw = metadata.get(key)
        if raw is None:
            continue
        try:
            return uuid.UUID(str(raw))
        except (ValueError, TypeError):
            continue
    return None


def _distance_to_similarity(distance_raw: Any) -> float | None:
    """Map Chroma cosine distance raw value to similarity in ``[0, 1]``."""

    if distance_raw is None:
        return None
    try:
        distance_val = float(distance_raw)
    except (TypeError, ValueError):
        return None
    return max(0.0, min(1.0, 1.0 - distance_val))


def _as_float_maybe(raw: Any) -> float | None:
    """Coerce telemetry into ``float`` when Chroma forwards numpy scalars."""

    if raw is None:
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


async def search_recipes_semantic(
    session: AsyncSession,
    *,
    query: str,
    limit: int,
    swarm_id: str | None = None,
    task_id: str | None = None,
) -> list[RecipeSemanticHit]:
    """Retrieve ranked recipe embeddings and optionally hydrate catalog rows."""

    cap = settings.recipe_chroma_search_limit_cap
    capped = max(1, min(limit, cap))
    trimmed = query.strip()
    if not trimmed:
        return []

    ctx = logger.bind(swarm_id=swarm_id or "", task_id=task_id or "")
    try:
        raw_hits = await semantic_search(trimmed, RECIPE_LIBRARY_COLLECTION, n_results=capped)
    except Exception as exc:
        ctx.warning(
            "recipe_chroma.semantic_search_failed",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return []

    out: list[RecipeSemanticHit] = []
    for row in raw_hits:
        distance = row.get("distance")
        similarity = _distance_to_similarity(distance)
        if similarity is None:
            continue
        if similarity < settings.recipe_chroma_min_similarity:
            continue
        metadata = dict(row.get("metadata") or {})
        doc = row.get("document") or ""
        preview = str(doc)[:_PREVIEW_CHARS]
        pid = _try_parse_recipe_uuid(metadata)
        postgres_item: RecipeCatalogItem | None = None
        if pid is not None:
            stmt = select(Recipe).where(Recipe.id == pid)
            exec_result = await session.execute(stmt)
            orm_row = exec_result.scalar_one_or_none()
            if orm_row is not None:
                postgres_item = RecipeCatalogItem.model_validate(orm_row)
        chroma_doc_id = str(row.get("id") or "")
        out.append(
            RecipeSemanticHit(
                chroma_document_id=chroma_doc_id,
                similarity=float(similarity),
                distance=_as_float_maybe(distance),
                document_preview=preview,
                metadata=metadata,
                postgres_recipe_id=pid,
                postgres_row=postgres_item,
            ),
        )

    ctx.info(
        "recipe_chroma.hits_materialized",
        hit_count=len(out),
        chroma_candidates=len(raw_hits),
        limit_requested=limit,
    )
    return out


__all__ = ["search_recipes_semantic"]
