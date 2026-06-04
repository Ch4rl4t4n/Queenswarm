"""Content Pack Factory HTTP API — research, queue, library, export."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.content_pack_factory_research import (
    auto_queue_content_pack_builds,
    run_content_pack_market_research,
)
from app.application.services.factory_policy_limits import (
    FACTORY_MAX_BUILDS_PER_WEEK_CAP,
    FACTORY_MAX_BUILDS_PER_WEEK_DEFAULT,
)
from app.application.services.factory_vertical_seeds import vertical_seeds_payload
from app.application.services.content_pack_factory_service import (
    ContentPackFactoryPolicyOut,
    ContentPackFactorySnapshotOut,
    compose_content_pack_factory_snapshot,
    dismiss_opportunity,
    export_tenant_content_pack_bundle,
    get_content_pack_factory_policy,
    list_content_pack_opportunities,
    save_content_pack_factory_policy,
    start_content_pack_factory_build,
)
from app.core.config import settings
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/content-pack-factory", tags=["Content Pack Factory"])


class ContentPackFactoryPolicyBody(BaseModel):
    """Update Content Pack Factory automation policy."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    niche_seeds: list[str] = Field(default_factory=list, max_length=12)
    auto_build_enabled: bool = False
    auto_build_min_score: float = Field(default=0.72, ge=0.0, le=1.0)
    max_builds_per_week: int = Field(
        default=FACTORY_MAX_BUILDS_PER_WEEK_DEFAULT,
        ge=1,
        le=FACTORY_MAX_BUILDS_PER_WEEK_CAP,
    )
    research_cron_enabled: bool = True


def _tenant_id(principal: dict) -> uuid.UUID:
    raw = principal.get("tenant_id")
    if raw is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant required.")
    return raw if isinstance(raw, uuid.UUID) else uuid.UUID(str(raw))


def _ensure_enabled() -> None:
    if not settings.content_pack_factory_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content Pack Factory disabled.")


@router.get("/snapshot", response_model=ContentPackFactorySnapshotOut, summary="Content Pack Factory dashboard")
async def content_pack_factory_snapshot(
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> ContentPackFactorySnapshotOut:
    """Return policy, opportunities, and tenant content pack library."""

    _ensure_enabled()
    return await compose_content_pack_factory_snapshot(db, tenant_id=_tenant_id(principal))


@router.put("/policy", response_model=ContentPackFactoryPolicyOut, summary="Update automation policy")
async def content_pack_factory_update_policy(
    body: ContentPackFactoryPolicyBody,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> ContentPackFactoryPolicyOut:
    """Persist Content Pack Factory research/build automation settings."""

    _ensure_enabled()
    policy = ContentPackFactoryPolicyOut.model_validate(body.model_dump())
    saved = await save_content_pack_factory_policy(db, tenant_id=_tenant_id(principal), policy=policy)
    await db.commit()
    return saved


@router.post("/research/run", summary="Run market research now")
async def content_pack_factory_run_research(
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, int | bool]:
    """Scan niches and insert ranked content pack opportunities."""

    _ensure_enabled()
    tenant_id = _tenant_id(principal)
    policy = await get_content_pack_factory_policy(db, tenant_id=tenant_id)
    created = await run_content_pack_market_research(db, tenant_id=tenant_id, policy=policy)
    started = 0
    if policy.auto_build_enabled:
        subject = str(principal.get("sub") or "operator")
        started = await auto_queue_content_pack_builds(
            db,
            tenant_id=tenant_id,
            policy=policy,
            created_by_subject=subject,
        )
    await db.commit()
    active = sum(
        1
        for row in await list_content_pack_opportunities(db, tenant_id=tenant_id, limit=100)
        if row.status in {"pending", "queued", "building", "awaiting_forge"}
    )
    return {"created": len(created), "builds_started": started, "active_opportunities": active}


@router.post("/opportunities/{opportunity_id}/build", summary="Start factory build")
async def content_pack_factory_build(
    opportunity_id: uuid.UUID,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, str]:
    """Launch supervisor session to produce content pack for one opportunity."""

    _ensure_enabled()
    tenant_id = _tenant_id(principal)
    subject = str(principal.get("sub") or "operator")
    try:
        row = await start_content_pack_factory_build(
            db,
            tenant_id=tenant_id,
            opportunity_id=opportunity_id,
            created_by_subject=subject,
        )
    except ValueError as exc:
        detail = str(exc)
        if detail == "weekly_build_cap_reached":
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Weekly build cap reached — wait or raise max builds in Settings.",
            ) from exc
        if detail == "opportunity_not_found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail) from exc
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=detail) from exc
    await db.commit()
    return {
        "opportunity_id": str(row.id),
        "session_id": str(row.supervisor_session_id or ""),
        "status": row.status,
    }


@router.post("/opportunities/{opportunity_id}/dismiss", summary="Dismiss opportunity")
async def content_pack_factory_dismiss(
    opportunity_id: uuid.UUID,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, str]:
    """Mark opportunity dismissed."""

    _ensure_enabled()
    row = await dismiss_opportunity(db, tenant_id=_tenant_id(principal), opportunity_id=opportunity_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found.")
    await db.commit()
    return {"id": str(row.id), "status": row.status}


@router.post("/packs/{pack_id}/export", summary="Export Gumroad bundle")
async def content_pack_factory_export(
    pack_id: uuid.UUID,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> dict:
    """Return publish_pack JSON + LISTING + PACK export bundle."""

    _ensure_enabled()
    try:
        bundle = await export_tenant_content_pack_bundle(
            db,
            tenant_id=_tenant_id(principal),
            pack_id=pack_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await db.commit()
    return bundle


class GumroadPublishBody(BaseModel):
    """Optional Gumroad publish overrides."""

    model_config = ConfigDict(extra="forbid")

    product_id: str | None = None
    create_if_missing: bool = False


@router.post("/packs/{pack_id}/export/gumroad-draft", summary="Create Gumroad draft listing")
async def content_pack_factory_export_gumroad_draft(
    pack_id: uuid.UUID,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> dict:
    """Create a Gumroad draft product from content pack LISTING.md."""

    _ensure_enabled()
    from app.application.services.content_pack_factory_gumroad_listing import create_gumroad_draft_from_content_pack

    result = await create_gumroad_draft_from_content_pack(
        db,
        tenant_id=_tenant_id(principal),
        pack_id=pack_id,
    )
    if not result.get("ok"):
        detail = str(result.get("error") or "gumroad_draft_failed")
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        if detail == "pack_not_found":
            status_code = status.HTTP_404_NOT_FOUND
        elif detail in {"gumroad_listing_disabled", "gumroad_not_configured"}:
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=detail)
    await db.commit()
    return result


@router.post("/packs/{pack_id}/export/gumroad-publish", summary="Publish Gumroad listing")
async def content_pack_factory_export_gumroad_publish(
    pack_id: uuid.UUID,
    body: GumroadPublishBody,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> dict:
    """Enable (publish) a Gumroad product linked to this content pack."""

    _ensure_enabled()
    from app.application.services.content_pack_factory_gumroad_listing import publish_gumroad_listing_for_content_pack

    result = await publish_gumroad_listing_for_content_pack(
        db,
        tenant_id=_tenant_id(principal),
        pack_id=pack_id,
        product_id=body.product_id,
        create_if_missing=body.create_if_missing,
    )
    if not result.get("ok"):
        detail = str(result.get("error") or "gumroad_publish_failed")
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        if detail == "pack_not_found":
            status_code = status.HTTP_404_NOT_FOUND
        elif detail in {"gumroad_publish_disabled", "gumroad_not_configured", "gumroad_product_id_missing"}:
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=detail)
    await db.commit()
    return result


@router.get("/vertical-seeds", summary="Monetization vertical niche catalog")
async def content_pack_factory_vertical_seeds(
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, list[str]]:
    """Return SSOT vertical seeds for operator presets."""

    del principal
    _ensure_enabled()
    payload = vertical_seeds_payload()
    return {
        "vertical": payload["content_pack_factory"],
        "starter": payload["content_pack_starter"],
    }
