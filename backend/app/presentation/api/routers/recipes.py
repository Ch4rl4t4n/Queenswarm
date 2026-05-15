"""Recipe Library catalog (JWT guarded)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, Request, Response, status
from sqlalchemy.exc import SQLAlchemyError

from app.presentation.api.deps import DbSession, JwtSubject, RecipeMutationSubject
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.recipe import Recipe
from app.common.schemas.recipes_catalog import RecipeCatalogItem
from app.common.schemas.recipes_search import RecipeSemanticHit
from app.common.schemas.recipes_write import RecipeCreateBody, RecipePatchBody
from app.application.services.recipe_catalog import list_recipe_catalog_rows
from app.application.services.recipe_chroma_bridge import search_recipes_semantic
from app.application.services.recipe_write import (
    RecipeWriteConflictError,
    RecipeWriteEmptyPatchError,
    RecipeWriteNotFoundError,
    RecipeWritePayloadTooLargeError,
    RecipeWriteReferencedError,
    create_recipe_entry,
    delete_recipe_entry,
    update_recipe_entry,
)

logger = get_logger(__name__)

router = APIRouter(tags=["Recipes"])


def _ensure_recipes_enabled() -> None:
    if not settings.recipes_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recipes module is disabled.",
        )


def _ensure_leaderboard_enabled() -> None:
    if not settings.leaderboard_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Leaderboard module is disabled.",
        )


@router.get(
    "/search",
    response_model=list[RecipeSemanticHit],
    summary="Semantic Recipe Library recall (Chroma)",
    name="recipe_semantic_search",
)
async def semantic_recipe_search(
    db: DbSession,
    _subject: JwtSubject,
    q: str = Query(
        min_length=1,
        description="Natural-language cue matched against Recipe Library embeddings.",
    ),
    limit: int = Query(default=10, ge=1, le=50),
):
    """Rank verified workflow embeddings via cosine similarity (optional Postgres join)."""

    _ensure_recipes_enabled()
    try:
        return await search_recipes_semantic(db, query=q, limit=limit, task_id=_subject)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected semantic recipe hydrate.",
        )


@router.post(
    "",
    response_model=RecipeCatalogItem,
    status_code=status.HTTP_201_CREATED,
    summary="Create Recipe Library row",
)
async def create_recipe(
    body: RecipeCreateBody,
    db: DbSession,
    subject: RecipeMutationSubject,
    request: Request,
) -> RecipeCatalogItem:
    """Promote a workflow template into the imitation catalog (optional Chroma mirror)."""

    _ensure_recipes_enabled()
    try:
        row = await create_recipe_entry(
            db,
            body,
            swarm_id="",
            task_id=subject,
        )
        await db.commit()
    except RecipeWriteConflictError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Recipe name already exists: {exc.args[0]!r}.",
        )
    except RecipeWritePayloadTooLargeError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"workflow_template JSON exceeds {exc.max_bytes} bytes "
                f"(encoded size {exc.size_bytes})."
            ),
        )
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected recipe insert.",
        )

    logger.info(
        "recipe_catalog.created",
        recipe_id=str(row.id),
        recipe_name=row.name,
        operator_subject=subject,
        client_host=request.client.host if request.client else None,
    )

    return RecipeCatalogItem.model_validate(row)


@router.get(
    "",
    response_model=list[RecipeCatalogItem],
    summary="List Recipe Library leaderboard rows",
)
async def list_recipes(
    db: DbSession,
    _subject: JwtSubject,
    q: str | None = Query(default=None, description="Filter by name/description (ilike)."),
    verified_only: bool = Query(
        default=False,
        description="Limit to verified recipes (`verified_at` not null).",
    ),
    include_deprecated: bool = Query(
        default=False,
        description="Include deprecated rows (normally hidden).",
    ),
    limit: int = Query(default=50, ge=1, le=200),
):
    """Return catalog metadata for imitation dashboards (no embedding payloads)."""

    _ensure_recipes_enabled()
    _ensure_leaderboard_enabled()
    try:
        rows = await list_recipe_catalog_rows(
            db,
            verified_only=verified_only,
            include_deprecated=include_deprecated,
            needle=q,
            limit=limit,
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected recipe catalog query.",
        )
    return rows


@router.get(
    "/{recipe_id}",
    response_model=RecipeCatalogItem,
    summary="Get Recipe Library row",
)
async def get_recipe(
    recipe_id: uuid.UUID,
    db: DbSession,
    _subject: JwtSubject,
) -> RecipeCatalogItem:
    """Return a single leaderboard row."""

    _ensure_recipes_enabled()
    try:
        row = await db.get(Recipe, recipe_id)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected recipe lookup.",
        )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found.",
        )

    return RecipeCatalogItem.model_validate(row)


@router.patch(
    "/{recipe_id}",
    response_model=RecipeCatalogItem,
    summary="Update Recipe Library row",
)
async def patch_recipe(
    recipe_id: uuid.UUID,
    body: RecipePatchBody,
    db: DbSession,
    subject: RecipeMutationSubject,
    request: Request,
) -> RecipeCatalogItem:
    """Patch metadata or template fields and refresh embeddings when enabled."""

    _ensure_recipes_enabled()
    try:
        row = await update_recipe_entry(
            db,
            recipe_id,
            body,
            swarm_id="",
            task_id=subject,
        )
        await db.commit()
    except RecipeWriteNotFoundError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found.",
        )
    except RecipeWriteConflictError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Recipe name already exists: {exc.args[0]!r}.",
        )
    except RecipeWriteEmptyPatchError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide at least one mutable field.",
        )
    except RecipeWritePayloadTooLargeError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"workflow_template JSON exceeds {exc.max_bytes} bytes "
                f"(encoded size {exc.size_bytes})."
            ),
        )
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected recipe update.",
        )

    logger.info(
        "recipe_catalog.updated",
        recipe_id=str(row.id),
        recipe_name=row.name,
        operator_subject=subject,
        client_host=request.client.host if request.client else None,
    )

    return RecipeCatalogItem.model_validate(row)


@router.delete(
    "/{recipe_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete Recipe Library row",
)
async def delete_recipe(
    recipe_id: uuid.UUID,
    db: DbSession,
    subject: RecipeMutationSubject,
    request: Request,
) -> Response:
    """Hard-delete when no workflows/tasks reference the recipe (prefer deprecate otherwise)."""

    _ensure_recipes_enabled()
    try:
        rid, name = await delete_recipe_entry(
            db,
            recipe_id,
            swarm_id="",
            task_id=subject,
        )
        await db.commit()
    except RecipeWriteNotFoundError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found.",
        )
    except RecipeWriteReferencedError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot delete recipe: {exc.reference_count} dependent row(s) in "
                "workflows or tasks. Set is_deprecated=true or clear FK references first."
            ),
        )
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected recipe delete.",
        )

    logger.info(
        "recipe_catalog.deleted",
        recipe_id=str(rid),
        recipe_name=name,
        operator_subject=subject,
        client_host=request.client.host if request.client else None,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
