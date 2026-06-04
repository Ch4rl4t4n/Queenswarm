"""Skill Factory HTTP API — research, queue, library, export."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.application.services.factory_policy_limits import (
    FACTORY_MAX_BUILDS_PER_WEEK_CAP,
    FACTORY_MAX_BUILDS_PER_WEEK_DEFAULT,
)
from app.application.services.factory_product_presets import (
    factory_product_presets,
    merged_vertical_seeds_payload,
    preset_by_id,
)
from app.application.services.skill_factory_research import auto_queue_factory_builds, run_skill_market_research
from app.application.services.harness_eval_service import HarnessEvalResultOut
from app.application.services.skill_factory_launch import LaunchPrepareOut, prepare_launch_batch
from app.application.services.skill_factory_service import (
    SkillFactoryPolicyOut,
    SkillFactorySnapshotOut,
    compose_skill_factory_snapshot,
    dismiss_opportunity,
    export_tenant_skill_bundle,
    get_skill_factory_policy,
    list_skill_opportunities,
    rebuild_factory_opportunity,
    reject_failed_factory_forges,
    reject_factory_forge,
    save_skill_factory_policy,
    start_factory_build,
)
from app.application.services.skill_picker_usage import (
    get_skill_picker_usage_map,
    increment_skill_picker_usage,
    sync_skill_picker_usage_counts,
)
from app.application.services.tenant_skill_loader import list_all_skill_slugs_for_tenant
from app.core.config import settings
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/skill-factory", tags=["Skill Factory"])


class SkillFactoryPolicyBody(BaseModel):
    """Update Skill Factory automation policy."""

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
    apify_deep_scrape_enabled: bool = False
    monid_listing_signals_enabled: bool = False
    monid_listing_preview_on_approve: bool = False
    monid_listing_video_preview_on_approve: bool = False


class SkillCatalogItemOut(BaseModel):
    """One skill row for operator picker."""

    model_config = ConfigDict(extra="ignore")

    slug: str
    title: str
    keywords: list[str] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)
    is_builtin: bool = True
    is_tenant: bool = False
    usage_count: int = Field(default=0, ge=0)


class SkillPickerUsageBody(BaseModel):
    """Record manual skill selection in session/task pickers."""

    model_config = ConfigDict(extra="forbid")

    slugs: list[str] = Field(default_factory=list, max_length=32)


class SkillPickerUsageSyncBody(BaseModel):
    """One-time merge of browser localStorage counts into backend tallies."""

    model_config = ConfigDict(extra="forbid")

    counts: dict[str, int] = Field(default_factory=dict, max_length=50)


def _tenant_id(principal: dict) -> uuid.UUID:
    raw = principal.get("tenant_id")
    if raw is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant required.")
    return raw if isinstance(raw, uuid.UUID) else uuid.UUID(str(raw))


def _ensure_enabled() -> None:
    if not settings.skill_factory_enabled:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill Factory disabled.")


@router.get("/snapshot", response_model=SkillFactorySnapshotOut, summary="Skill Factory dashboard")
async def skill_factory_snapshot(
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> SkillFactorySnapshotOut:
    """Return policy, opportunities, and tenant skill library."""

    _ensure_enabled()
    snapshot = await compose_skill_factory_snapshot(db, tenant_id=_tenant_id(principal))
    await db.commit()
    return snapshot


@router.get("/catalog", response_model=list[SkillCatalogItemOut], summary="All skills for picker")
async def skill_factory_catalog(
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> list[SkillCatalogItemOut]:
    """Builtin + tenant skills for session/task skill picker."""

    _ensure_enabled()
    tenant_id = _tenant_id(principal)
    rows = await list_all_skill_slugs_for_tenant(db, tenant_id=tenant_id)
    usage_map = await get_skill_picker_usage_map(db, tenant_id=tenant_id)
    return [
        SkillCatalogItemOut.model_validate(
            {
                **row,
                "usage_count": usage_map.get(str(row["slug"]).lower(), 0),
            },
        )
        for row in rows
    ]


@router.post("/catalog/usage", status_code=status.HTTP_204_NO_CONTENT, summary="Record skill picker usage")
async def skill_factory_record_picker_usage(
    body: SkillPickerUsageBody,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> None:
    """Increment usage tallies when operator manually selects skills."""

    _ensure_enabled()
    await increment_skill_picker_usage(db, tenant_id=_tenant_id(principal), slugs=body.slugs)
    await db.commit()


@router.post("/catalog/usage/sync", status_code=status.HTTP_204_NO_CONTENT, summary="Merge localStorage usage")
async def skill_factory_sync_picker_usage(
    body: SkillPickerUsageSyncBody,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> None:
    """Additive merge for one-time migration from browser localStorage."""

    _ensure_enabled()
    await sync_skill_picker_usage_counts(db, tenant_id=_tenant_id(principal), counts=body.counts)
    await db.commit()


@router.put("/policy", response_model=SkillFactoryPolicyOut, summary="Update automation policy")
async def skill_factory_update_policy(
    body: SkillFactoryPolicyBody,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> SkillFactoryPolicyOut:
    """Persist Skill Factory research/build automation settings."""

    _ensure_enabled()
    policy = SkillFactoryPolicyOut.model_validate(body.model_dump())
    saved = await save_skill_factory_policy(db, tenant_id=_tenant_id(principal), policy=policy)
    await db.commit()
    return saved


@router.post("/research/run", summary="Run market research now")
async def skill_factory_run_research(
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, int | bool]:
    """Scan niches and insert ranked opportunities."""

    _ensure_enabled()
    tenant_id = _tenant_id(principal)
    policy = await get_skill_factory_policy(db, tenant_id=tenant_id)
    created = await run_skill_market_research(db, tenant_id=tenant_id, policy=policy)
    started = 0
    if policy.auto_build_enabled:
        subject = str(principal.get("sub") or "operator")
        started = await auto_queue_factory_builds(
            db,
            tenant_id=tenant_id,
            policy=policy,
            created_by_subject=subject,
        )
    await db.commit()
    active = sum(
        1
        for row in await list_skill_opportunities(db, tenant_id=tenant_id, limit=100)
        if row.status in {"pending", "queued", "building", "awaiting_forge"}
    )
    return {"created": len(created), "builds_started": started, "active_opportunities": active}


@router.post("/opportunities/{opportunity_id}/build", summary="Start factory build")
async def skill_factory_build(
    opportunity_id: uuid.UUID,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, str]:
    """Launch supervisor session to produce skill for one opportunity."""

    _ensure_enabled()
    tenant_id = _tenant_id(principal)
    subject = str(principal.get("sub") or "operator")
    try:
        row = await start_factory_build(
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
async def skill_factory_dismiss(
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


class RebuildOut(BaseModel):
    """Factory rebuild response."""

    model_config = ConfigDict(extra="ignore")

    opportunity_id: str
    session_id: str
    status: str


@router.post("/opportunities/{opportunity_id}/reject-forge", summary="Reject pending forge")
async def skill_factory_reject_forge(
    opportunity_id: uuid.UUID,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, bool]:
    """Reject failed verified_skill_forge for one opportunity."""

    _ensure_enabled()
    tenant_id = _tenant_id(principal)
    try:
        await reject_factory_forge(
            db,
            tenant_id=tenant_id,
            opportunity_id=opportunity_id,
            reviewer_subject=str(principal.get("sub") or "dashboard:skill_factory"),
        )
    except ValueError as exc:
        code = str(exc)
        status_code = status.HTTP_404_NOT_FOUND if code == "opportunity_not_found" else status.HTTP_422_UNPROCESSABLE_CONTENT
        raise HTTPException(status_code=status_code, detail=code) from exc
    await db.commit()
    return {"rejected": True}


@router.post("/opportunities/{opportunity_id}/rebuild", response_model=RebuildOut, summary="Reject forge and rebuild")
async def skill_factory_rebuild(
    opportunity_id: uuid.UUID,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> RebuildOut:
    """Reject failed forge (if pending) and queue a fresh factory session."""

    _ensure_enabled()
    tenant_id = _tenant_id(principal)
    subject = str(principal.get("sub") or "dashboard:skill_factory")
    try:
        row = await rebuild_factory_opportunity(
            db,
            tenant_id=tenant_id,
            opportunity_id=opportunity_id,
            created_by_subject=subject,
            reviewer_subject=subject,
        )
    except ValueError as exc:
        code = str(exc)
        if code == "weekly_build_cap_reached":
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=code) from exc
        status_code = status.HTTP_404_NOT_FOUND if code == "opportunity_not_found" else status.HTTP_422_UNPROCESSABLE_CONTENT
        raise HTTPException(status_code=status_code, detail=code) from exc
    await db.commit()
    return RebuildOut(
        opportunity_id=str(row.id),
        session_id=str(row.supervisor_session_id or ""),
        status=row.status,
    )


@router.post("/queue/reject-failed-forges", summary="Bulk reject forges that failed quality gate")
async def skill_factory_reject_failed_forges(
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, int]:
    """Reject all pending skill forges where quality gate failed."""

    _ensure_enabled()
    rejected = await reject_failed_factory_forges(
        db,
        tenant_id=_tenant_id(principal),
        reviewer_subject=str(principal.get("sub") or "dashboard:skill_factory"),
    )
    await db.commit()
    return {"rejected": rejected}


@router.post("/skills/{skill_id}/export", summary="Export GitHub bundle")
async def skill_factory_export(
    skill_id: uuid.UUID,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> dict:
    """Return SKILL.md + README + LISTING export bundle."""

    _ensure_enabled()
    try:
        bundle = await export_tenant_skill_bundle(
            db,
            tenant_id=_tenant_id(principal),
            skill_id=skill_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await db.commit()
    return bundle


@router.post("/skills/{skill_id}/export/github-pr", summary="Push export to GitHub PR")
async def skill_factory_export_github_pr(
    skill_id: uuid.UUID,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> dict:
    """Commit Skill Factory bundle to a branch and open a GitHub PR for review."""

    _ensure_enabled()
    from app.application.services.skill_factory_github_export import push_skill_export_github_pr

    result = await push_skill_export_github_pr(
        db,
        tenant_id=_tenant_id(principal),
        skill_id=skill_id,
    )
    if not result.get("ok"):
        detail = str(result.get("error") or "github_pr_failed")
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        if detail in {"skill_not_found"}:
            status_code = status.HTTP_404_NOT_FOUND
        elif detail in {"github_pr_disabled", "github_target_not_configured"}:
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=detail)
    await db.commit()
    return result


@router.post("/skills/{skill_id}/export/gumroad-draft", summary="Create Gumroad draft listing")
async def skill_factory_export_gumroad_draft(
    skill_id: uuid.UUID,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> dict:
    """Create a Gumroad draft product from LISTING.md (operator finishes in Gumroad UI)."""

    _ensure_enabled()
    from app.application.services.skill_factory_gumroad_listing import create_gumroad_draft_from_skill

    result = await create_gumroad_draft_from_skill(
        db,
        tenant_id=_tenant_id(principal),
        skill_id=skill_id,
    )
    if not result.get("ok"):
        detail = str(result.get("error") or "gumroad_draft_failed")
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        if detail == "skill_not_found":
            status_code = status.HTTP_404_NOT_FOUND
        elif detail in {"gumroad_listing_disabled", "gumroad_not_configured"}:
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=detail)
    await db.commit()
    return result


class GumroadPublishBody(BaseModel):
    """Optional Gumroad publish overrides."""

    model_config = ConfigDict(extra="forbid")

    product_id: str | None = None
    create_if_missing: bool = False


@router.post("/skills/{skill_id}/export/gumroad-publish", summary="Publish Gumroad listing")
async def skill_factory_export_gumroad_publish(
    skill_id: uuid.UUID,
    body: GumroadPublishBody,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> dict:
    """Enable (publish) a Gumroad product linked to this skill."""

    _ensure_enabled()
    from app.application.services.skill_factory_gumroad_listing import publish_gumroad_listing_for_skill

    result = await publish_gumroad_listing_for_skill(
        db,
        tenant_id=_tenant_id(principal),
        skill_id=skill_id,
        product_id=body.product_id,
        create_if_missing=body.create_if_missing,
    )
    if not result.get("ok"):
        detail = str(result.get("error") or "gumroad_publish_failed")
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        if detail == "skill_not_found":
            status_code = status.HTTP_404_NOT_FOUND
        elif detail in {"gumroad_publish_disabled", "gumroad_not_configured", "gumroad_product_id_missing"}:
            status_code = status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=status_code, detail=detail)
    await db.commit()
    return result


class LaunchPrepareBody(BaseModel):
    """Launch batch preparation options."""

    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=3, ge=1, le=12)


@router.post("/launch/prepare", response_model=LaunchPrepareOut, summary="Prepare Gumroad launch batch")
async def skill_factory_launch_prepare(
    body: LaunchPrepareBody,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> LaunchPrepareOut:
    """Export sellable skills server-side and return operator checklist."""

    _ensure_enabled()
    result = await prepare_launch_batch(
        db,
        tenant_id=_tenant_id(principal),
        limit=body.limit,
    )
    await db.commit()
    return result


@router.post("/skills/{skill_id}/eval", response_model=HarnessEvalResultOut, summary="Eval tenant skill markdown")
async def skill_factory_eval_skill(
    skill_id: uuid.UUID,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
):
    """Run Eval-as-a-Service on a library skill."""

    _ensure_enabled()
    from app.application.services.harness_eval_service import HarnessEvalRequest, run_harness_eval
    from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM

    row = await db.scalar(
        select(TenantSkillORM).where(
            TenantSkillORM.id == skill_id,
            TenantSkillORM.tenant_id == _tenant_id(principal),
        ),
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Skill not found.")
    return await run_harness_eval(
        HarnessEvalRequest(
            workflow_markdown=row.markdown_body or "",
            title=row.title,
            run_llm_critic=False,
        ),
    )


@router.get("/vertical-seeds", summary="Monetization vertical niche catalog")
async def skill_factory_vertical_seeds(
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, list[str] | list[dict[str, object]]]:
    """Return SSOT vertical seeds for operator presets."""

    del principal
    _ensure_enabled()
    payload = merged_vertical_seeds_payload()
    return {
        "vertical": payload["skill_factory"],
        "starter": payload["skill_factory_starter"],
        "product_presets": payload["product_presets"],
    }


@router.get("/product-presets", summary="Revenue-oriented factory presets")
async def skill_factory_product_presets(
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> list[dict[str, object]]:
    """Return Pigford + Middleton preset bundles for Settings UI."""

    del principal
    _ensure_enabled()
    return [row.model_dump(mode="json") for row in factory_product_presets()]


class ApplyProductPresetOut(BaseModel):
    """Policy after applying a product preset."""

    model_config = ConfigDict(extra="ignore")

    preset_id: str
    niche_seeds: list[str]
    policy: SkillFactoryPolicyOut


@router.post("/product-presets/{preset_id}/apply", response_model=ApplyProductPresetOut, summary="Apply preset seeds")
async def skill_factory_apply_product_preset(
    preset_id: str,
    db: DbSession,
    principal: dict = Depends(require_dashboard_user_with_tenant_role),
) -> ApplyProductPresetOut:
    """Replace niche seeds with a curated revenue preset (Pigford / Middleton)."""

    _ensure_enabled()
    preset = preset_by_id(preset_id)
    if preset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="preset_not_found")
    tenant_id = _tenant_id(principal)
    current = await get_skill_factory_policy(db, tenant_id=tenant_id)
    updated = current.model_copy(update={"niche_seeds": list(preset.niche_seeds)[:12]})
    saved = await save_skill_factory_policy(db, tenant_id=tenant_id, policy=updated)
    await db.commit()
    return ApplyProductPresetOut(preset_id=preset.id, niche_seeds=list(saved.niche_seeds), policy=saved)


__all__ = ["router"]
