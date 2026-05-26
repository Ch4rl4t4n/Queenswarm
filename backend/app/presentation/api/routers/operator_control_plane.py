"""Operator Control Plane API — unified cockpit, context, actions, innovation lab."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.hive_innovation_lab import (
    InnovationBrainstormRequest,
    brainstorm_innovation_proposal,
    compose_innovation_lab_snapshot,
    implement_innovation_proposal,
    review_innovation_proposal,
)
from app.application.services.operator_control_plane import (
    OperatorActRequest,
    compose_operator_cockpit_snapshot,
    compose_operator_context,
    execute_operator_action,
)
from app.application.services.operator_telegram_gateway import (
    process_telegram_webhook,
    verify_operator_telegram_webhook_secret,
)
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role

router = APIRouter(prefix="/operator", tags=["Operator Control Plane"])


class InnovationReviewRequest(BaseModel):
    """Approve or reject innovation proposal."""

    model_config = ConfigDict(extra="forbid")

    decision: Literal["approved", "rejected"]


class CrystallizeRequest(BaseModel):
    """Preview or launch crystallized intent."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=8, max_length=8000)
    launch: bool = False


def _require_owner_or_admin(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "guest")
    if role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner or admin tenant role required.")


def _reviewer_subject(principal: dict[str, Any]) -> str:
    user = principal.get("user")
    email = getattr(user, "email", None) if user is not None else None
    return str(email or "operator")


@router.get("/cockpit", summary="Unified operator cockpit snapshot")
async def operator_cockpit(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    if tenant_id is None or user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    snapshot = await compose_operator_cockpit_snapshot(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
        tenant=tenant,
    )
    return snapshot.model_dump(mode="json")


@router.get("/context", summary="Unified operator memory context")
async def operator_context(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    snapshot = await compose_operator_context(db, tenant_id=tenant_id)
    return snapshot.model_dump(mode="json")


@router.post("/act", summary="Execute typed control-plane action")
async def operator_act(
    body: OperatorActRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    _require_owner_or_admin(principal)
    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    if tenant_id is None or user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    result = await execute_operator_action(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
        tenant=tenant,
        reviewer_subject=_reviewer_subject(principal),
        body=body,
    )
    await db.commit()
    return result.model_dump(mode="json")


@router.get("/oracle", summary="Hive Oracle v2 — warnings, predictions, optional synthesis")
async def operator_oracle(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    synthesis: bool = False,
) -> dict[str, Any]:
    """Full Hive Oracle snapshot for dedicated /oracle widget."""

    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    if tenant_id is None or user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")

    from app.application.services.hive_innovation_lab import count_pending_innovation_proposals
    from app.application.services.hive_oracle import compose_hive_oracle_snapshot
    from app.application.services.operator_control_plane import _load_swarm_fleet
    from app.application.services.operator_loop import compose_operator_loop_snapshot
    from app.application.services.solo_operator_trio import get_solo_trio_status

    tenant = await db.get(Tenant, tenant_id)
    loop = await compose_operator_loop_snapshot(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
        tenant=tenant,
        phase="anytime",
    )
    trio = await get_solo_trio_status(db, tenant_id=tenant_id)
    fleet = await _load_swarm_fleet(db, tenant_id=tenant_id)
    innovation_pending = 0
    if settings.hive_innovation_lab_enabled:
        innovation_pending = await count_pending_innovation_proposals(db, tenant_id=tenant_id)

    snapshot = await compose_hive_oracle_snapshot(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
        loop_actions=loop.actions,
        fleet=fleet,
        trio=trio,
        loop=loop.model_dump(mode="json"),
        innovation_pending=innovation_pending,
        include_synthesis=synthesis,
    )
    return snapshot.model_dump(mode="json")


@router.post("/crystallize", summary="Intent Crystallizer v2 — preview or launch")
async def operator_crystallize(
    body: CrystallizeRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Crystallize free text → plan; optionally launch Queen goal."""

    if not settings.intent_crystallizer_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Intent Crystallizer disabled.")

    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    if tenant_id is None or user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")

    from app.application.services.intent_crystallizer import crystallize_intent, launch_crystallized_intent

    plan = crystallize_intent(body.text)
    if not body.launch:
        return {"ok": True, "preview": True, "plan": plan.model_dump(mode="json")}

    _require_owner_or_admin(principal)
    tenant = await db.get(Tenant, tenant_id)
    launched = await launch_crystallized_intent(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
        tenant=tenant,
        reviewer_subject=_reviewer_subject(principal),
        plan=plan,
        spawn_factory="micro-saas-factory" in plan.suggested_templates,
    )
    await db.commit()
    if launched.get("requires_confirm"):
        return {
            "ok": False,
            "preview": False,
            "message": "Live lane requires explicit confirm in Advanced UI.",
            "plan": plan.model_dump(mode="json"),
        }
    return {
        "ok": True,
        "preview": False,
        "message": "Queen goal queued (verify-first).",
        "plan": plan.model_dump(mode="json"),
        "launched": launched,
        "href": launched.get("href"),
    }


@router.get("/innovation-lab", summary="Innovation lab proposals snapshot")
async def innovation_lab_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    snapshot = await compose_innovation_lab_snapshot(db, tenant_id=tenant_id)
    return snapshot.model_dump(mode="json")


@router.post("/innovation-lab/brainstorm", summary="Brainstorm new hive capability")
async def innovation_brainstorm(
    body: InnovationBrainstormRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    _require_owner_or_admin(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    if not settings.hive_innovation_lab_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Innovation lab disabled.")
    try:
        proposal = await brainstorm_innovation_proposal(db, tenant_id=tenant_id, body=body)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    await db.commit()
    return proposal.model_dump(mode="json")


@router.post(
    "/innovation-lab/proposals/{proposal_id}/review",
    summary="Approve or reject innovation proposal",
)
async def innovation_review(
    proposal_id: uuid.UUID,
    body: InnovationReviewRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    _require_owner_or_admin(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    try:
        proposal = await review_innovation_proposal(
            db,
            tenant_id=tenant_id,
            proposal_id=proposal_id,
            decision=body.decision,
            reviewer_subject=_reviewer_subject(principal),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await db.commit()
    return proposal.model_dump(mode="json")


@router.post(
    "/innovation-lab/proposals/{proposal_id}/implement",
    summary="Auto-implement approved proposal via Queen Maintainer",
)
async def innovation_implement(
    proposal_id: uuid.UUID,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    _require_owner_or_admin(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    result = await implement_innovation_proposal(
        db,
        tenant=tenant,
        proposal_id=proposal_id,
        reviewer_subject=_reviewer_subject(principal),
    )
    await db.commit()
    return result


class LinkDropRequest(BaseModel):
    """On-demand URL brief — read-only fetch."""

    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=8, max_length=2048)
    persist: bool = False


class DialogueExtractRequest(BaseModel):
    """Paste dialogue transcript for structure extraction."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=40, max_length=120_000)
    apply: Literal["preview", "harness", "knowledge"] = "preview"


class KeywordScanRequest(BaseModel):
    """Scan transcript for suggested actions (never auto-fire)."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=8, max_length=120_000)


@router.post("/link-drop", summary="ICM Link Drop — URL → structured brief")
async def operator_link_drop(
    body: LinkDropRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Read-only URL fetch → Research Bee brief; optional HiveMind persist."""

    if not settings.operator_icm_tools_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ICM tools disabled.")
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")

    from app.application.services.operator_icm_tools import preview_link_drop
    from app.application.services.research_bee import compose_research_brief

    try:
        if body.persist:
            _require_owner_or_admin(principal)
            brief = await compose_research_brief(
                db,
                tenant_id=tenant_id,
                source_url=body.url.strip(),
                persist=True,
            )
        else:
            brief = await preview_link_drop(db, tenant_id=tenant_id, url=body.url)
        await db.commit()
        return {"ok": True, "brief": brief.model_dump(mode="json")}
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/dialogue-extract", summary="ICM Dialogue Extract — goals/constraints/decisions")
async def operator_dialogue_extract(
    body: DialogueExtractRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Extract structure from dialogue; optional apply to harness or Knowledge."""

    if not settings.operator_icm_tools_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ICM tools disabled.")
    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    if tenant_id is None or user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")

    from app.application.services.operator_icm_tools import apply_dialogue_extract, extract_dialogue_structure

    extraction = extract_dialogue_structure(body.text)
    if body.apply != "preview":
        _require_owner_or_admin(principal)
        applied = await apply_dialogue_extract(
            db,
            tenant_id=tenant_id,
            dashboard_user_id=user.id,
            extraction=extraction,
            target=body.apply,
        )
        await db.commit()
        return {
            "ok": True,
            "extraction": extraction.model_dump(mode="json"),
            "applied": applied,
        }
    return {"ok": True, "extraction": extraction.model_dump(mode="json")}


@router.post("/keyword-scan", summary="ICM keyword hints from transcript")
async def operator_keyword_scan(
    body: KeywordScanRequest,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Suggest operator actions from keywords — human approve only."""

    if not settings.operator_icm_tools_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ICM tools disabled.")
    if principal.get("tenant_id") is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")

    from app.application.services.operator_icm_tools import scan_transcript_keywords

    scan = scan_transcript_keywords(body.text)
    return {"ok": True, "scan": scan.model_dump(mode="json")}


@router.post(
    "/sessions/{session_id}/recipe-draft",
    summary="Save supervisor session as recipe draft",
)
async def operator_session_recipe_draft(
    session_id: uuid.UUID,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Build recipe draft from completed session — unverified template."""

    _require_owner_or_admin(principal)
    if not settings.operator_icm_tools_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ICM tools disabled.")
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")

    from app.application.services.operator_icm_tools import build_session_recipe_draft
    from app.application.services.recipe_write import RecipeWriteConflictError, create_recipe_entry
    from app.common.schemas.recipes_write import RecipeCreateBody
    from app.presentation.api.routers.operator import OperatorRecipeStepBody, OperatorSaveRecipeRequest

    try:
        draft = await build_session_recipe_draft(db, tenant_id=tenant_id, session_id=session_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    req = OperatorSaveRecipeRequest.model_validate(draft)
    ordered = sorted(req.steps, key=lambda step: step.step_order)
    template: dict[str, Any] = {
        "version": 1,
        "source": "supervisor_session_icm",
        "task_text": req.task_text,
        "session_id": str(session_id),
        "steps": [step.model_dump(mode="json") for step in ordered],
    }
    recipe_body = RecipeCreateBody(
        name=req.name.strip(),
        description=req.description,
        topic_tags=req.topic_tags,
        workflow_template=template,
        mark_verified=False,
    )
    try:
        recipe = await create_recipe_entry(
            db,
            recipe_body,
            swarm_id="operator_recipe",
            task_id=str(session_id),
        )
        await db.commit()
    except RecipeWriteConflictError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return {"ok": True, "recipe_id": str(recipe.id), "name": recipe.name, "href": "/recipes"}


@router.post(
    "/telegram/webhook/{webhook_secret}",
    include_in_schema=False,
    summary="Telegram inbound webhook for Zero-UI Hive Mode",
)
async def operator_telegram_webhook(
    webhook_secret: str,
    request: Request,
    db: DbSession,
) -> dict[str, str]:
    """Receive Telegram updates and route to Control Plane actions."""

    if not settings.operator_telegram_inbound_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Telegram inbound disabled.")

    secret = (settings.operator_telegram_webhook_secret or "").strip()
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OPERATOR_TELEGRAM_WEBHOOK_SECRET is not configured.",
        )

    header_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if not verify_operator_telegram_webhook_secret(
        path_secret=webhook_secret,
        header_secret=header_secret,
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid webhook secret.")

    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid JSON.") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Expected object payload.")

    await process_telegram_webhook(db, update=payload)
    return {"status": "ok"}


__all__ = ["router"]
