"""Recipe Library catalog (JWT guarded)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.exc import SQLAlchemyError

from app.presentation.api.deps import DashboardSession, DbSession, RecipeMutationSubject, require_dashboard_user_with_tenant_role
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.recipe import Recipe
from app.common.schemas.recipes_catalog import RecipeCatalogItem
from app.common.schemas.recipes_search import RecipeSemanticHit
from app.common.schemas.recipes_write import RecipeCreateBody, RecipePatchBody
from app.domain.recipes.orchestration_pattern_stacks import list_orchestration_pattern_stacks
from app.application.services.recipe_catalog import list_recipe_catalog_rows
from app.application.services.recipe_pattern_tags import recipe_to_catalog_item
from app.application.services.recipe_chroma_bridge import search_recipes_semantic
from app.application.services.recipe_match_config import RecipeMatchConfigResponse, build_recipe_match_config
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
from app.application.services.skill_access import (
    assert_skill_export_allowed,
    list_tenant_skill_unlocks,
)
from app.application.services.skill_export import build_skills_catalog, export_recipe_skill
from app.application.services.recipe_marketplace_beta import (
    RecipeMarketplaceBetaSnapshotOut,
    compose_recipe_marketplace_beta_snapshot,
)
from app.common.schemas.skill_export import SkillCatalogResponse, SkillExportResponse
from app.common.schemas.skill_marketplace import (
    SkillUnlockStatusResponse,
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
    "/match-config",
    response_model=RecipeMatchConfigResponse,
    summary="Recipe cosine match thresholds for UI",
)
async def recipe_match_config(_session: DashboardSession) -> RecipeMatchConfigResponse:
    """Expose imitation-engine similarity gate (default 0.85) and hybrid weights."""

    _ensure_recipes_enabled()
    return build_recipe_match_config()


@router.get(
    "/marketplace-beta",
    response_model=RecipeMarketplaceBetaSnapshotOut,
    summary="Recipe marketplace beta snapshot",
)
async def recipe_marketplace_beta_snapshot(db: DbSession, _session: DashboardSession) -> RecipeMarketplaceBetaSnapshotOut:
    """UGC marketplace counts + config for recipes hub beta panel."""

    _ensure_recipes_enabled()
    return await compose_recipe_marketplace_beta_snapshot(db)


@router.get(
    "/search",
    response_model=list[RecipeSemanticHit],
    summary="Semantic Recipe Library recall (Chroma)",
    name="recipe_semantic_search",
)
async def semantic_recipe_search(
    db: DbSession,
    _session: DashboardSession,
    q: str = Query(
        min_length=1,
        description="Natural-language cue matched against Recipe Library embeddings.",
    ),
    limit: int = Query(default=10, ge=1, le=50),
):
    """Rank verified workflow embeddings via cosine similarity (optional Postgres join)."""

    _ensure_recipes_enabled()
    try:
        return await search_recipes_semantic(
            db,
            query=q,
            limit=limit,
            task_id=str(_session.get("sub", "dashboard_operator")),
        )
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

    return recipe_to_catalog_item(row)


@router.get(
    "/pattern-stacks",
    summary="Orchestration template pattern stacks",
)
async def recipe_pattern_stacks(_session: DashboardSession) -> list[dict[str, object]]:
    """Return canonical orchestration templates and their agentic pattern stacks."""

    _ensure_recipes_enabled()
    return list_orchestration_pattern_stacks()


@router.get(
    "",
    response_model=list[RecipeCatalogItem],
    summary="List Recipe Library leaderboard rows",
)
async def list_recipes(
    db: DbSession,
    _session: DashboardSession,
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
    return [recipe_to_catalog_item(row) for row in rows]


@router.get(
    "/skills-catalog",
    response_model=SkillCatalogResponse,
    summary="Built-in hive skills + verified recipes for export marketplace",
)
async def list_skills_export_catalog(
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
    limit: int = Query(default=80, ge=1, le=200),
) -> SkillCatalogResponse:
    """Return supervisor built-ins and verified Recipe Library rows eligible for skill export."""

    _ensure_recipes_enabled()
    tenant_id = principal.get("tenant_id")
    try:
        return await build_skills_catalog(
            db,
            recipe_limit=limit,
            tenant_id=tenant_id,
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected skills catalog query.",
        )


@router.get(
    "/skills/unlocks",
    response_model=SkillUnlockStatusResponse,
    summary="Tenant skill purchase unlock state",
)
async def get_skill_unlock_status(
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> SkillUnlockStatusResponse:
    """Return unlocked premium recipe ids."""

    _ensure_recipes_enabled()
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    try:
        unlocked = await list_tenant_skill_unlocks(db, tenant_id=tenant_id)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected skill unlock query.",
        )
    return SkillUnlockStatusResponse(
        checkout_available=False,
        unlocked_recipe_ids=[str(rid) for rid in unlocked],
        premium_price_eur_cents_default=int(settings.skill_export_premium_price_eur_cents),
    )


@router.post(
    "/{recipe_id}/export-skill",
    response_model=SkillExportResponse,
    summary="Export recipe as Cursor/Claude skill bundle (SKILL.md + HIVE.md)",
)
async def export_recipe_as_skill(
    recipe_id: uuid.UUID,
    db: DbSession,
    session: DashboardSession,
    request: Request,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> SkillExportResponse:
    """Build a Matt Pocock-style skill folder from a Recipe Library row."""

    _ensure_recipes_enabled()
    tenant_id = principal.get("tenant_id")
    try:
        row = await db.get(Recipe, recipe_id)
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recipe not found.",
            )
        await assert_skill_export_allowed(db, tenant_id=tenant_id, recipe=row)
        bundle = await export_recipe_skill(db, recipe_id)
    except HTTPException:
        raise
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected recipe export lookup.",
        )

    if bundle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found.",
        )

    logger.info(
        "recipe_catalog.export_skill",
        recipe_id=str(recipe_id),
        slug=bundle.meta.slug,
        verified=bundle.meta.verified,
        operator_subject=str(session.get("sub", "dashboard_operator")),
        client_host=request.client.host if request.client else None,
    )
    return bundle


@router.get(
    "/{recipe_id}",
    response_model=RecipeCatalogItem,
    summary="Get Recipe Library row",
)
async def get_recipe(
    recipe_id: uuid.UUID,
    db: DbSession,
    _session: DashboardSession,
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

    return recipe_to_catalog_item(row)


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

    return recipe_to_catalog_item(row)


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
