"""Learning Engine HTTP surface (Maynard-Cross rewards, imitation, recipes, reflection)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError

from app.presentation.api.deps import DashboardSession, DbSession, RecipeMutationSubject
from app.core.config import settings
from app.domain.learning.imitation_engine import record_imitation_event, select_top_k_exemplars
from app.domain.learning.reflection_loop import persist_task_reflection, run_post_task_reflection
from app.domain.learning.reward_tracker import (
    allocate_pollen_pool,
    grant_weighted_pollen,
    maynard_cross_weights,
    merge_confidence_with_performance,
)
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.enums import AgentRole
from app.domain.recipes.library import autosave_verified_workflow, semantic_search_catalog
from app.common.schemas.learning import (
    ExemplarBrief,
    ImitationCopyRequest,
    PollenAllocateRequest,
    PollenAllocateResponse,
    RecipeAutosaveRequest,
    ReflectionCreate,
    TaskReflectionRequest,
)
from app.common.schemas.skill_marketplace import VerifiedPollenLeaderboardRow
from app.common.schemas.bee_gamification import BeeBadgeCatalogItem, BeeBadgeProfile
from app.application.services.bee_gamification import (
    bee_gamification_enabled,
    build_bee_badge_profiles,
    list_badge_catalog,
)
from app.common.schemas.pending_review import (
    PendingReviewItemRow,
    PendingReviewResolveRequest,
    PendingReviewStats,
)
from app.application.services.verified_pollen_leaderboard import fetch_verified_pollen_leaderboard
from app.application.services.pending_review_service import (
    fetch_pending_review_stats,
    list_pending_review_items,
    resolve_pending_review_item,
)
from app.infrastructure.persistence.models.enums import PendingReviewStatus
from app.common.schemas.recipes_write import RecipeCreateBody
from app.application.services.recipe_write import RecipeWriteConflictError, RecipeWritePayloadTooLargeError

router = APIRouter(tags=["Learning"])


def _ensure_leaderboard_enabled() -> None:
    if not settings.leaderboard_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Leaderboard module is disabled.",
        )


def _ensure_bee_gamification_enabled() -> None:
    if not bee_gamification_enabled():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bee gamification is disabled.",
        )


def _ensure_recipes_enabled() -> None:
    if not settings.recipes_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Recipes module is disabled.",
        )


@router.post(
    "/rewards/allocate",
    response_model=PollenAllocateResponse,
    summary="Allocate a pollen pool with Maynard-Cross weighting",
)
async def allocate_rewards(
    body: PollenAllocateRequest,
    db: DbSession,
    _session: DashboardSession,
) -> PollenAllocateResponse:
    """Partition hive pollen using signals and optional performance fusion."""

    try:
        conf_map = {s.agent_id: float(s.signal) for s in body.signals}
        agent_rows: dict[uuid.UUID, Agent] = {}
        for aid in conf_map:
            row = await db.get(Agent, aid)
            if row is not None:
                agent_rows[aid] = row

        if body.blend_performance and agent_rows:
            weights = merge_confidence_with_performance(agent_rows, conf_map)
        else:
            weights = maynard_cross_weights(conf_map)

        allocations = allocate_pollen_pool(body.pool, weights)
        credited = await grant_weighted_pollen(
            db,
            allocations=allocations,
            task_id=body.task_id,
            reason=body.reason,
        )
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected pollen allocation.",
        )

    serial = {str(k): round(v, 6) for k, v in allocations.items()}
    return PollenAllocateResponse(credited_agents=credited, allocations=serial)


@router.get(
    "/imitation/exemplars",
    response_model=list[ExemplarBrief],
    summary="Top-K imitation neighbors for a role",
)
async def list_exemplars(
    db: DbSession,
    _session: DashboardSession,
    role: AgentRole = Query(description="Bee specialization to rank."),
    copier_agent_id: uuid.UUID | None = Query(
        default=None,
        description="Exclude this bee from consideration (usually the copier).",
    ),
    swarm_id: uuid.UUID | None = Query(
        default=None,
        description="Restrict to a single sub-swarm colony.",
    ),
) -> list[ExemplarBrief]:
    """Return high-signal exemplars for imitation."""

    _ensure_leaderboard_enabled()
    try:
        rows = await select_top_k_exemplars(
            db,
            role=role,
            exclude_agent_id=copier_agent_id,
            swarm_id=swarm_id,
            top_k=None,
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected exemplar query.",
        )

    return [
        ExemplarBrief(
            agent_id=r.id,
            name=r.name,
            role=r.role,
            performance_score=float(r.performance_score),
            pollen_points=float(r.pollen_points),
        )
        for r in rows
    ]


@router.get(
    "/leaderboard/verified-pollen",
    response_model=list[VerifiedPollenLeaderboardRow],
    summary="Redis ZSET leaderboard for simulation-verified pollen",
)
async def list_verified_pollen_leaderboard(
    db: DbSession,
    _session: DashboardSession,
    limit: int = Query(default=20, ge=1, le=100),
    swarm_id: uuid.UUID | None = Query(default=None, description="Optional sub-swarm filter."),
) -> list[VerifiedPollenLeaderboardRow]:
    """Return top bees ranked by verified pollen (simulation-gated rewards only)."""

    _ensure_leaderboard_enabled()
    if not settings.verified_pollen_leaderboard_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Verified pollen leaderboard is disabled.",
        )
    try:
        rows = await fetch_verified_pollen_leaderboard(db, limit=limit, swarm_id=swarm_id)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected leaderboard hydrate.",
        )
    return [VerifiedPollenLeaderboardRow.model_validate(row) for row in rows]


@router.get(
    "/bee-badges/catalog",
    response_model=list[BeeBadgeCatalogItem],
    summary="Earnable bee badge catalog",
)
async def bee_badge_catalog(_session: DashboardSession) -> list[BeeBadgeCatalogItem]:
    """Return static badge definitions for tooltips and onboarding."""

    _ensure_bee_gamification_enabled()
    return [BeeBadgeCatalogItem.model_validate(row) for row in list_badge_catalog()]


@router.get(
    "/bee-badges",
    response_model=list[BeeBadgeProfile],
    summary="Bee profiles with verified-workflow badges",
)
async def list_bee_badge_profiles(
    db: DbSession,
    _session: DashboardSession,
    limit: int = Query(default=16, ge=1, le=48),
) -> list[BeeBadgeProfile]:
    """Rank bees by earned badges and verified pollen."""

    _ensure_bee_gamification_enabled()
    try:
        rows = await build_bee_badge_profiles(db, limit=limit)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected bee badge query.",
        )
    return [BeeBadgeProfile.model_validate(row) for row in rows]


@router.post(
    "/imitation/copy",
    status_code=status.HTTP_201_CREATED,
    summary="Record a directed imitation event",
)
async def create_imitation_edge(
    body: ImitationCopyRequest,
    db: DbSession,
    _session: DashboardSession,
) -> dict[str, str]:
    """Persist copier → exemplar edges for analytics."""

    try:
        await record_imitation_event(
            db,
            copier_agent_id=body.copier_agent_id,
            exemplar_agent_id=body.exemplar_agent_id,
            recipe_id=body.recipe_id,
        )
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected imitation edge insert.",
        )
    return {"status": "recorded"}


@router.post(
    "/reflection",
    status_code=status.HTTP_201_CREATED,
    summary="Persist a learning reflection",
)
async def create_reflection(
    body: ReflectionCreate,
    db: DbSession,
    _session: DashboardSession,
) -> dict[str, str]:
    """Manual LearningLog entry (operators or service bees)."""

    try:
        await persist_task_reflection(
            db,
            agent_id=body.agent_id,
            task_id=body.task_id,
            insight=body.insight,
            pollen_earned=body.pollen_earned,
        )
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected learning log insert.",
        )
    return {"status": "logged"}


@router.post(
    "/reflection/task",
    status_code=status.HTTP_201_CREATED,
    summary="Structured post-task reflection (rapid loop)",
)
async def reflect_after_task(
    body: TaskReflectionRequest,
    db: DbSession,
    _session: DashboardSession,
) -> dict[str, str]:
    """Emit a structured insight after LangGraph / swarm task execution."""

    try:
        await run_post_task_reflection(
            db,
            agent_id=body.agent_id,
            task_id=body.task_id,
            task_payload=body.payload,
            outcome=body.outcome,
            verified=body.verified,
            confidence=body.confidence,
        )
        await db.commit()
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected structured reflection insert.",
        )
    return {"status": "logged"}


@router.get(
    "/recipes/search",
    summary="Semantic Recipe Library search (Learning facade)",
)
async def learning_recipe_search(
    db: DbSession,
    _session: DashboardSession,
    q: str = Query(min_length=1),
    limit: int = Query(default=10, ge=1, le=50),
):
    """Proxy to Chroma + Postgres hydration for imitation dashboards."""

    _ensure_recipes_enabled()
    try:
        return await semantic_search_catalog(
            db,
            query=q,
            limit=limit,
            task_id=str(_session.get("sub", "dashboard_operator")),
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected semantic recipe search.",
        )


@router.post(
    "/recipes/autosave",
    status_code=status.HTTP_201_CREATED,
    summary="Promote verified workflow JSON into Recipe Library",
)
async def autosave_recipe(
    body: RecipeAutosaveRequest,
    db: DbSession,
    subject: RecipeMutationSubject,
) -> dict[str, str]:
    """Create catalog row + optional Chroma mirror when mutations are enabled."""

    _ensure_recipes_enabled()
    payload = RecipeCreateBody(
        name=body.name,
        description=body.description,
        topic_tags=body.topic_tags,
        workflow_template=body.workflow_template,
        created_by_agent_id=body.created_by_agent_id,
        mark_verified=body.mark_verified,
    )
    try:
        recipe = await autosave_verified_workflow(
            db,
            payload,
            swarm_id="",
            task_id=subject,
            created_by_agent_id=body.created_by_agent_id,
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
            detail="Persistence rejected recipe autosave.",
        )

    return {"recipe_id": str(recipe.id), "name": recipe.name}


def _ensure_pending_review_enabled() -> None:
    if not settings.pending_review_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Pending review queue is disabled.",
        )


@router.get(
    "/pending-review/stats",
    response_model=PendingReviewStats,
    summary="Aggregate pending-review queue counts",
)
async def pending_review_stats(
    db: DbSession,
    _session: DashboardSession,
) -> PendingReviewStats:
    """Return badge counts for operator dashboards."""

    _ensure_pending_review_enabled()
    try:
        return await fetch_pending_review_stats(db)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected pending-review stats.",
        )


@router.get(
    "/pending-review",
    response_model=list[PendingReviewItemRow],
    summary="List operator pending-review items",
)
async def list_pending_review(
    db: DbSession,
    _session: DashboardSession,
    status_filter: PendingReviewStatus | None = Query(
        default=PendingReviewStatus.PENDING,
        alias="status",
        description="Filter by review status (default: pending).",
    ),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[PendingReviewItemRow]:
    """Return newest items awaiting human approval."""

    _ensure_pending_review_enabled()
    try:
        rows = await list_pending_review_items(db, status=status_filter, limit=limit)
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected pending-review query.",
        )
    return [PendingReviewItemRow.model_validate(row) for row in rows]


@router.post(
    "/pending-review/{item_id}/resolve",
    response_model=PendingReviewItemRow,
    summary="Approve or reject a pending-review item",
)
async def resolve_pending_review(
    item_id: uuid.UUID,
    body: PendingReviewResolveRequest,
    db: DbSession,
    session: DashboardSession,
) -> PendingReviewItemRow:
    """Operator decision — releases or blocks low-confidence outcomes."""

    _ensure_pending_review_enabled()
    try:
        row = await resolve_pending_review_item(
            db,
            item_id=item_id,
            action=body.action,
            operator_subject=str(session.get("sub", "dashboard_operator")),
            note=body.note,
        )
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pending review item not found.")
        await db.commit()
        await db.refresh(row)
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Persistence rejected pending-review resolution.",
        )
    return PendingReviewItemRow.model_validate(row)


__all__ = ["router"]
