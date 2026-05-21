"""Admin API for platform feature matrix (account profile switches)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from app.application.services.platform_feature_policy import (
    delete_policy_override,
    load_policy_overrides,
    upsert_policy_overrides,
)
from app.application.services.platform_features import (
    FEATURE_LABELS,
    PROFILE_COLUMNS,
    build_feature_matrix,
    catalog_default_for_profile,
    preview_features_for_profile,
)
from app.core.logging import get_logger
from app.presentation.api.deps import DashboardAdmin, DbSession

logger = get_logger(__name__)
router = APIRouter(prefix="/operator/platform-features", tags=["Platform Features"])


class PlatformFeatureCellUpdate(BaseModel):
    """One matrix cell toggle."""

    feature_key: str = Field(..., min_length=1, max_length=64)
    profile_key: str = Field(..., min_length=1, max_length=32)
    enabled: bool | None = Field(
        default=None,
        description="When null, remove override and revert to catalog default.",
    )


class PlatformFeatureMatrixPatch(BaseModel):
    """Bulk matrix updates from admin settings UI."""

    updates: list[PlatformFeatureCellUpdate] = Field(default_factory=list)


@router.get("", summary="Read platform feature matrix for admin settings")
async def get_platform_feature_matrix(_: DashboardAdmin, db: DbSession) -> dict[str, Any]:
    """Return grouped feature rows and profile columns with effective values."""

    overrides = await load_policy_overrides(db)
    return build_feature_matrix(policy_overrides=overrides)


@router.get("/preview", summary="Preview effective features for one profile column")
async def preview_platform_feature_profile(
    _: DashboardAdmin,
    db: DbSession,
    profile_key: str = Query(..., min_length=1, max_length=32),
) -> dict[str, Any]:
    """Simulate resolved feature flags without switching tenant."""

    try:
        overrides = await load_policy_overrides(db)
        return preview_features_for_profile(profile_key, policy_overrides=overrides)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.patch("", summary="Update platform feature matrix cells")
async def patch_platform_feature_matrix(
    body: PlatformFeatureMatrixPatch,
    _: DashboardAdmin,
    db: DbSession,
) -> dict[str, Any]:
    """Persist admin toggles; null enabled removes override."""

    valid_features = set(FEATURE_LABELS)
    valid_profiles = {str(row["key"]) for row in PROFILE_COLUMNS}
    to_upsert: list[dict[str, object]] = []

    try:
        for item in body.updates:
            feature_key = item.feature_key.strip()
            profile_key = item.profile_key.strip()
            if feature_key not in valid_features:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unknown feature_key: {feature_key}",
                )
            if profile_key not in valid_profiles:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unknown profile_key: {profile_key}",
                )
            if item.enabled is None:
                await delete_policy_override(db, feature_key=feature_key, profile_key=profile_key)
            else:
                to_upsert.append(
                    {
                        "feature_key": feature_key,
                        "profile_key": profile_key,
                        "enabled": bool(item.enabled),
                    },
                )
        if to_upsert:
            await upsert_policy_overrides(db, updates=to_upsert)
        await db.commit()
    except HTTPException:
        await db.rollback()
        raise
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.warning(
            "platform_features.matrix_patch_failed",
            agent_id="platform_features_admin",
            swarm_id="",
            task_id="",
            error=str(exc),
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Matrix update failed.") from exc

    overrides = await load_policy_overrides(db)
    logger.info(
        "platform_features.matrix_patched",
        agent_id="platform_features_admin",
        swarm_id="",
        task_id="",
        update_count=len(body.updates),
    )
    return build_feature_matrix(policy_overrides=overrides)


@router.post("/reset", summary="Reset one profile column to catalog defaults")
async def reset_platform_feature_profile(
    _: DashboardAdmin,
    db: DbSession,
    profile_key: str = Query(..., min_length=1, max_length=32),
) -> dict[str, Any]:
    """Delete all overrides for one profile column."""

    valid_profiles = {str(row["key"]) for row in PROFILE_COLUMNS}
    key = profile_key.strip()
    if key not in valid_profiles:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Unknown profile_key: {key}")

    try:
        overrides = await load_policy_overrides(db)
        for (feature_key, pk), _enabled in list(overrides.items()):
            if pk == key:
                await delete_policy_override(db, feature_key=feature_key, profile_key=pk)
        await db.commit()
    except SQLAlchemyError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Reset failed.") from exc

    fresh = await load_policy_overrides(db)
    return build_feature_matrix(policy_overrides=fresh)
