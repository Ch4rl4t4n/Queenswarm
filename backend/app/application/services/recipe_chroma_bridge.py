"""Bridge Chroma cosine recall to Postgres Recipe rows for imitation dashboards."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.chroma_client import RECIPE_LIBRARY_COLLECTION, semantic_search
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.recipe import Recipe
from app.infrastructure.persistence.models.reward import ImitationEvent
from app.common.schemas.recipes_catalog import RecipeCatalogItem
from app.common.schemas.recipes_search import RecipeSemanticHit

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


def _recipe_success_rate(recipe: Recipe | None) -> float:
    """Map recipe ledger counters into ``[0, 1]`` graph signal."""

    if recipe is None:
        return 0.0
    success = max(0, int(recipe.success_count))
    fails = max(0, int(recipe.fail_count))
    total = success + fails
    if total <= 0:
        return 0.5 if recipe.verified_at is not None else 0.0
    return max(0.0, min(1.0, success / total))


async def _imitation_counts_by_recipe(
    session: AsyncSession,
    recipe_ids: list[uuid.UUID],
) -> dict[uuid.UUID, int]:
    """Count Postgres imitation edges per recipe for graph boost."""

    if not recipe_ids:
        return {}
    stmt = (
        select(ImitationEvent.recipe_id, func.count())
        .where(ImitationEvent.recipe_id.in_(recipe_ids))
        .group_by(ImitationEvent.recipe_id)
    )
    rows = await session.execute(stmt)
    out: dict[uuid.UUID, int] = {}
    for recipe_id, count in rows.all():
        if recipe_id is not None:
            out[recipe_id] = int(count)
    return out


def _normalize_imitation_signal(counts: dict[uuid.UUID, int], recipe_id: uuid.UUID | None) -> float:
    """Normalize imitation counts into ``[0, 1]``."""

    if recipe_id is None or not counts:
        return 0.0
    raw = counts.get(recipe_id, 0)
    if raw <= 0:
        return 0.0
    peak = max(counts.values()) or 1
    return max(0.0, min(1.0, raw / peak))


def _merge_graph_signals(*signals: float) -> float:
    """Return strongest graph hint in ``[0, 1]``."""

    if not signals:
        return 0.0
    return max(0.0, min(1.0, max(signals)))


async def _neo4j_imitation_counts(recipe_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """Best-effort Neo4j imitation edge counts keyed by recipe UUID."""

    if not settings.recipe_hybrid_neo4j_enabled or not recipe_ids:
        return {}
    try:
        from app.core.neo4j_client import count_imitation_edges_by_recipes

        raw = await count_imitation_edges_by_recipes([str(rid) for rid in recipe_ids])
    except Exception as exc:  # noqa: BLE001 — graph tier is optional for search
        logger.debug(
            "recipe_chroma.neo4j_imitation_skip",
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return {}
    out: dict[uuid.UUID, int] = {}
    for key, count in raw.items():
        try:
            out[uuid.UUID(str(key))] = int(count)
        except ValueError:
            continue
    return out


def _hybrid_similarity(
    *,
    vector_similarity: float,
    graph_signal: float,
) -> float:
    """Blend vector cosine with graph performance/imitation signal."""

    if not settings.recipe_hybrid_scoring_enabled:
        return vector_similarity
    vector_w = float(settings.recipe_hybrid_vector_weight)
    graph_w = float(settings.recipe_hybrid_graph_weight)
    total_w = vector_w + graph_w
    if total_w <= 0:
        return vector_similarity
    blended = (vector_w * vector_similarity + graph_w * graph_signal) / total_w
    return max(0.0, min(1.0, blended))


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
    recipe_orm_cache: dict[uuid.UUID, Recipe] = {}
    for row in raw_hits:
        distance = row.get("distance")
        vector_similarity = _distance_to_similarity(distance)
        if vector_similarity is None:
            continue
        if vector_similarity < settings.recipe_chroma_min_similarity:
            continue
        metadata = dict(row.get("metadata") or {})
        doc = row.get("document") or ""
        preview = str(doc)[:_PREVIEW_CHARS]
        pid = _try_parse_recipe_uuid(metadata)
        postgres_item: RecipeCatalogItem | None = None
        recipe_orm: Recipe | None = None
        if pid is not None:
            recipe_orm = recipe_orm_cache.get(pid)
            if recipe_orm is None:
                stmt = select(Recipe).where(Recipe.id == pid)
                exec_result = await session.execute(stmt)
                recipe_orm = exec_result.scalar_one_or_none()
                if recipe_orm is not None:
                    recipe_orm_cache[pid] = recipe_orm
            if recipe_orm is not None:
                postgres_item = RecipeCatalogItem.model_validate(recipe_orm)
        chroma_doc_id = str(row.get("id") or "")
        out.append(
            RecipeSemanticHit(
                chroma_document_id=chroma_doc_id,
                similarity=float(vector_similarity),
                vector_similarity=float(vector_similarity),
                graph_score=0.0,
                distance=_as_float_maybe(distance),
                document_preview=preview,
                metadata=metadata,
                postgres_recipe_id=pid,
                postgres_row=postgres_item,
            ),
        )

    if settings.recipe_hybrid_scoring_enabled and out:
        recipe_ids = [hit.postgres_recipe_id for hit in out if hit.postgres_recipe_id is not None]
        imitation_counts = await _imitation_counts_by_recipe(session, [rid for rid in recipe_ids if rid])
        neo4j_counts = await _neo4j_imitation_counts([rid for rid in recipe_ids if rid])
        rescored: list[RecipeSemanticHit] = []
        for hit in out:
            recipe_orm = recipe_orm_cache.get(hit.postgres_recipe_id) if hit.postgres_recipe_id else None
            success_signal = _recipe_success_rate(recipe_orm)
            pg_imitation = _normalize_imitation_signal(imitation_counts, hit.postgres_recipe_id)
            neo4j_imitation = _normalize_imitation_signal(neo4j_counts, hit.postgres_recipe_id)
            graph_signal = _merge_graph_signals(success_signal, pg_imitation, neo4j_imitation)
            hybrid = _hybrid_similarity(
                vector_similarity=float(hit.vector_similarity or hit.similarity),
                graph_signal=graph_signal,
            )
            rescored.append(
                hit.model_copy(
                    update={
                        "similarity": hybrid,
                        "graph_score": graph_signal,
                    },
                ),
            )
        out = sorted(rescored, key=lambda row: row.similarity, reverse=True)

    ctx.info(
        "recipe_chroma.hits_materialized",
        hit_count=len(out),
        chroma_candidates=len(raw_hits),
        limit_requested=limit,
    )
    return out


__all__ = ["search_recipes_semantic"]
