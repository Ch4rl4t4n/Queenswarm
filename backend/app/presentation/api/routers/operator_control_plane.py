"""Operator Control Plane API — unified cockpit, context, actions, innovation lab."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field, StrictBool

from app.application.services.hive_innovation_lab import (
    InnovationBrainstormRequest,
    brainstorm_innovation_proposal,
    compose_innovation_lab_snapshot,
    implement_innovation_proposal,
    review_innovation_proposal,
)
from app.application.services.apps_tools_index_analytics import (
    AppsToolsAnalyticsEventIn,
    compose_apps_tools_index_analytics_snapshot,
    persist_apps_tools_index_analytics_preferences,
    record_apps_tools_index_event,
)
from app.application.services.apps_tools_index_snapshot import compose_apps_tools_index_snapshot
from app.application.services.capability_registry import compose_capability_registry_snapshot
from app.application.services.module_policy_packs import (
    ModuleKey,
    compose_module_policy_pack_snapshot,
    get_module_policy_pack,
)
from app.application.services.mcp_ops_studio_snapshot import compose_mcp_ops_studio_snapshot
from app.application.services.approval_inbox import (
    ApprovalInboxSnapshotOut,
    compose_approval_inbox_snapshot,
)
from app.application.services.business_operator import (
    BusinessOperatorSnapshotOut,
    compose_business_operator_snapshot,
)
from app.application.services.business_goal_stack import (
    BusinessGoalStackOut,
    BusinessGoalStackPatchIn,
    compose_business_goal_stack,
    persist_goal_definitions,
)
from app.application.services.business_operator_dispatch import (
    BusinessOperatorDispatchIn,
    BusinessOperatorDispatchOut,
    dispatch_business_operator_action,
)
from app.application.services.proactive_pulse import ProactivePulseOut, compose_proactive_pulse
from app.application.services.prompt_injection_guard import (
    PromptInjectionViolationError,
    guard_operator_input,
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
    queue_maintainer: bool = False
    acknowledge_high_risk: bool = False


class CrystallizeRequest(BaseModel):
    """Preview or launch crystallized intent."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=8, max_length=8000)
    launch: bool = False


class AppsToolsAnalyticsPreferencesPatch(BaseModel):
    """Operator UI analytics preference patch payload."""

    model_config = ConfigDict(extra="ignore")

    window: Literal["24h", "7d", "all"] | None = None
    compact_mode: StrictBool | None = None


def _require_owner_or_admin(principal: dict[str, Any]) -> None:
    role = str(principal.get("tenant_role") or "guest")
    if role not in {"owner", "admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner or admin tenant role required.")


def _reviewer_subject(principal: dict[str, Any]) -> str:
    user = principal.get("user")
    email = getattr(user, "email", None) if user is not None else None
    return str(email or "operator")


@router.get(
    "/approvals",
    response_model=ApprovalInboxSnapshotOut,
    summary="Unified approval inbox (BA4)",
)
async def operator_approval_inbox(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    limit: int = Query(default=30, ge=1, le=50),
) -> ApprovalInboxSnapshotOut:
    """Pending publish packs, agent suggestions, lane digests, and revenue steps."""

    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    if tenant_id is None or user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    return await compose_approval_inbox_snapshot(
        db,
        tenant_id=uuid.UUID(str(tenant_id)),
        dashboard_user_id=user.id,
        tenant=tenant,
        limit=limit,
    )


@router.get(
    "/business/snapshot",
    response_model=BusinessOperatorSnapshotOut,
    summary="Chief Business Operator brief (read-only, BA1)",
)
async def business_operator_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> BusinessOperatorSnapshotOut:
    """Revenue, catalog, missions, and top 3 business actions."""

    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    if tenant_id is None or user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    return await compose_business_operator_snapshot(
        db,
        tenant_id=uuid.UUID(str(tenant_id)),
        dashboard_user_id=user.id,
        tenant=tenant,
    )


@router.post(
    "/business/dispatch",
    response_model=BusinessOperatorDispatchOut,
    status_code=status.HTTP_201_CREATED,
    summary="CBO one-click dispatch (BA6)",
)
async def business_operator_dispatch(
    body: BusinessOperatorDispatchIn,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> BusinessOperatorDispatchOut:
    """Dispatch a CBO top action into supervisor session or mission kanban."""

    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    if tenant_id is None or user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")

    reviewer = _reviewer_subject(principal)
    try:
        if body.goal_override:
            guard_operator_input(body.goal_override, field="goal_override")
        result = await dispatch_business_operator_action(
            db,
            tenant_id=uuid.UUID(str(tenant_id)),
            created_by_subject=reviewer,
            body=body,
        )
        await db.commit()
    except PromptInjectionViolationError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    except RuntimeError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    return result


@router.get(
    "/business/goals",
    response_model=BusinessGoalStackOut,
    summary="Business Goal Stack definitions (BA2)",
)
async def business_goal_stack_get(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> BusinessGoalStackOut:
    """Return tenant goal definitions with measured drift."""

    from app.application.services.business_operator import (
        BusinessCatalogSummaryOut,
        compose_revenue_summary,
        fetch_business_mission_summary,
    )
    from app.application.services.marketing_product_catalog import build_catalog

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    catalog_payload = build_catalog()
    catalog = BusinessCatalogSummaryOut(
        product_count=catalog_payload.product_count,
        featured_count=sum(1 for p in catalog_payload.products if p.featured),
        gumroad_linked_count=sum(1 for p in catalog_payload.products if p.gumroad_url),
    )
    missions = await fetch_business_mission_summary(db, tenant_id=uuid.UUID(str(tenant_id)))
    revenue = compose_revenue_summary()
    return await compose_business_goal_stack(
        db,
        tenant_id=uuid.UUID(str(tenant_id)),
        tenant=tenant,
        catalog=catalog,
        missions=missions,
        revenue=revenue,
    )


@router.patch(
    "/business/goals",
    response_model=BusinessGoalStackOut,
    summary="Update Business Goal Stack (BA2)",
)
async def business_goal_stack_patch(
    body: BusinessGoalStackPatchIn,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> BusinessGoalStackOut:
    """Replace tenant business goal definitions."""

    from app.application.services.business_operator import (
        BusinessCatalogSummaryOut,
        compose_revenue_summary,
        fetch_business_mission_summary,
    )
    from app.application.services.marketing_product_catalog import build_catalog

    _require_owner_or_admin(principal)
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    persist_goal_definitions(tenant, body.goals)
    await db.commit()
    catalog_payload = build_catalog()
    catalog = BusinessCatalogSummaryOut(
        product_count=catalog_payload.product_count,
        featured_count=sum(1 for p in catalog_payload.products if p.featured),
        gumroad_linked_count=sum(1 for p in catalog_payload.products if p.gumroad_url),
    )
    missions = await fetch_business_mission_summary(db, tenant_id=uuid.UUID(str(tenant_id)))
    revenue = compose_revenue_summary()
    return await compose_business_goal_stack(
        db,
        tenant_id=uuid.UUID(str(tenant_id)),
        tenant=tenant,
        catalog=catalog,
        missions=missions,
        revenue=revenue,
    )


@router.get(
    "/business/pulse",
    response_model=ProactivePulseOut,
    summary="Proactive pulse — what changed / what ran (BA5)",
)
async def business_proactive_pulse(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    phase: Literal["morning", "midday", "evening", "anytime"] = Query(default="midday"),
) -> ProactivePulseOut:
    """Midday (or anytime) proactive digest for CBO."""

    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    if tenant_id is None or user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    pulse = await compose_proactive_pulse(
        db,
        tenant_id=uuid.UUID(str(tenant_id)),
        dashboard_user_id=user.id,
        tenant=tenant,
        phase=phase,
    )
    await db.commit()
    return pulse


@router.get("/cockpit", summary="Unified operator cockpit snapshot")
async def operator_cockpit(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    scope: Literal["core", "modules", "full"] = "core",
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
        scope=scope,
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


@router.get("/capabilities", summary="Read-only capability registry snapshot")
async def operator_capabilities_registry(
    include_disabled: bool = False,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return capability contracts for Agentic OS and Apps/Tools layers."""

    if principal.get("tenant_id") is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    snapshot = compose_capability_registry_snapshot(include_disabled=include_disabled)
    return snapshot.model_dump(mode="json")


@router.get("/module-policy-packs", summary="Read-only module policy packs")
async def operator_module_policy_packs(
    include_disabled: bool = False,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return module-level policy packs for Apps & Tools workspace headers."""

    if principal.get("tenant_id") is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    snapshot = compose_module_policy_pack_snapshot(include_disabled=include_disabled)
    return snapshot.model_dump(mode="json")


@router.get("/module-policy-packs/{module_key}", summary="Read-only policy pack by module key")
async def operator_module_policy_pack_detail(
    module_key: str,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return one policy pack for a specific Apps & Tools module."""

    if principal.get("tenant_id") is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    allowed_keys: tuple[ModuleKey, ...] = (
        "marketing_automation",
        "mcp_ops_studio",
        "trading_automation",
        "browser_automation",
        "content_factory",
        "research_workspace",
        "live_lane",
    )
    if module_key not in allowed_keys:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module policy pack not found.")
    pack = get_module_policy_pack(module_key=module_key)
    if pack is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module policy pack not found.")
    return pack.model_dump(mode="json")


@router.get("/apps-tools-index", summary="Unified Apps & Tools index snapshot")
async def operator_apps_tools_index(
    include_disabled: bool = False,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return Apps & Tools-only capability + policy metadata in one payload."""

    if principal.get("tenant_id") is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    snapshot = compose_apps_tools_index_snapshot(include_disabled=include_disabled)
    return snapshot.model_dump(mode="json")


@router.get("/apps-tools/mcp-ops-studio/snapshot", summary="Read-only MCP Ops Studio snapshot")
async def operator_mcp_ops_studio_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return section-card snapshot for MCP Ops Studio route."""

    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    user_id = getattr(user, "id", None)
    if tenant_id is None or user_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    snapshot = await compose_mcp_ops_studio_snapshot(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user_id,
    )
    return snapshot.model_dump(mode="json")


@router.post("/apps-tools-index/events", summary="Record Apps & Tools index analytics event")
async def operator_apps_tools_index_event(
    body: AppsToolsAnalyticsEventIn,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Persist low-volume Apps & Tools UX funnel events for solo optimization."""

    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    if tenant_id is None or user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    out = record_apps_tools_index_event(
        tenant,
        dashboard_user_id=str(user.id),
        payload=body,
    )
    await db.commit()
    return {"ok": True, **out}


@router.get("/apps-tools-index/analytics", summary="Read Apps & Tools index analytics snapshot")
async def operator_apps_tools_index_analytics(
    db: DbSession,
    limit: int = 24,
    window: Literal["24h", "7d", "all"] | None = None,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Return tenant-scoped Apps & Tools funnel counters and recent events."""

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    snapshot = compose_apps_tools_index_analytics_snapshot(tenant, limit=limit, window=window)
    return snapshot.model_dump(mode="json")


@router.patch("/apps-tools-index/analytics/preferences", summary="Persist Apps & Tools analytics UI preferences")
async def operator_apps_tools_index_analytics_preferences(
    body: AppsToolsAnalyticsPreferencesPatch,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Store widget preferences (window + compact mode) per tenant."""

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found.")
    preferences = persist_apps_tools_index_analytics_preferences(
        tenant,
        window=body.window,
        compact_mode=body.compact_mode,
    )
    await db.commit()
    return {"ok": True, **preferences}


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
        result = await review_innovation_proposal(
            db,
            tenant_id=tenant_id,
            proposal_id=proposal_id,
            decision=body.decision,
            reviewer_subject=_reviewer_subject(principal),
            queue_maintainer=body.queue_maintainer and body.decision == "approved",
            acknowledge_high_risk=body.acknowledge_high_risk,
            tenant=await db.get(Tenant, tenant_id),
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    await db.commit()
    if isinstance(result, dict):
        return result
    return result.model_dump(mode="json")


@router.get(
    "/innovation-lab/proposals/{proposal_id}/viability",
    summary="Viability gate for Innovation Lab → Maintainer handoff",
)
async def innovation_viability(
    proposal_id: uuid.UUID,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    acknowledge_high_risk: bool = False,
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    try:
        from app.application.services.hive_innovation_lab import assess_proposal_viability

        viability = await assess_proposal_viability(
            db,
            tenant_id=tenant_id,
            proposal_id=proposal_id,
            acknowledge_high_risk=acknowledge_high_risk,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return viability.model_dump(mode="json")


@router.post(
    "/innovation-lab/proposals/{proposal_id}/implement",
    summary="Auto-implement approved proposal via Queen Maintainer",
)
async def innovation_implement(
    proposal_id: uuid.UUID,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    acknowledge_high_risk: bool = False,
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
        acknowledge_high_risk=acknowledge_high_risk,
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
    apply: Literal["preview", "harness", "knowledge", "recipe"] = "preview"


async def _persist_operator_recipe_draft(
    db: DbSession,
    draft: dict[str, Any],
    *,
    source: str,
    source_id: str,
) -> dict[str, Any]:
    """Validate draft and persist unverified recipe entry."""

    from app.application.services.recipe_write import RecipeWriteConflictError, create_recipe_entry
    from app.common.schemas.recipes_write import RecipeCreateBody
    from app.presentation.api.routers.operator import OperatorSaveRecipeRequest

    req = OperatorSaveRecipeRequest.model_validate(draft)
    ordered = sorted(req.steps, key=lambda step: step.step_order)
    template: dict[str, Any] = {
        "version": 1,
        "source": source,
        "task_text": req.task_text,
        "source_id": source_id,
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
            task_id=source_id,
        )
        await db.commit()
    except RecipeWriteConflictError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return {"recipe_id": str(recipe.id), "name": recipe.name, "href": "/recipes"}


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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


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

    from app.application.services.operator_icm_tools import (
        apply_dialogue_extract,
        build_dialogue_recipe_draft,
        extract_dialogue_structure,
    )

    extraction = extract_dialogue_structure(body.text)
    if body.apply == "recipe":
        _require_owner_or_admin(principal)
        draft = build_dialogue_recipe_draft(extraction)
        saved = await _persist_operator_recipe_draft(
            db,
            draft,
            source="dialogue_extract_icm",
            source_id=str(uuid.uuid4()),
        )
        return {
            "ok": True,
            "extraction": extraction.model_dump(mode="json"),
            "applied": {"ok": True, "target": "recipe", **saved},
        }
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


@router.get(
    "/ballroom/{session_id}/transcript-text",
    summary="ICM — format Ballroom capsule transcript for Dialogue Extract",
)
async def operator_ballroom_transcript_text(
    session_id: uuid.UUID,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Read-only Ballroom transcript → plain dialogue text (no auto-extract)."""

    if not settings.operator_icm_tools_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ICM tools disabled.")
    if principal.get("tenant_id") is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")

    from app.application.services import ballroom_store as ballroom_redis
    from app.application.services.operator_icm_tools import format_ballroom_transcript_text

    try:
        cap = await ballroom_redis.ballroom_load_capsule(session_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ballroom session not found.") from exc

    transcript = cap.get("transcript", [])
    if not isinstance(transcript, list):
        transcript = []
    text = format_ballroom_transcript_text(transcript)
    if len(text.strip()) < 40:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Ballroom transcript too short for dialogue extract (min 40 chars).",
        )
    return {
        "ok": True,
        "session_id": str(session_id),
        "text": text,
        "char_count": len(text),
        "message_count": len(transcript),
    }


@router.get(
    "/dump-sleep/{batch_id}/transcript-text",
    summary="ICM — format Dump & Sleep batch for Dialogue Extract",
)
async def operator_dump_sleep_transcript_text(
    batch_id: uuid.UUID,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Read-only Dump & Sleep briefing → plain dialogue text (no auto-extract)."""

    if not settings.operator_icm_tools_enabled:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="ICM tools disabled.")
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")

    from app.application.services.dump_sleep_service import DumpSleepService
    from app.application.services.operator_icm_tools import format_dump_sleep_dialogue_text
    from app.infrastructure.persistence.models.dump_sleep_batch import DumpSleepStatusORM

    service = DumpSleepService(db=db)
    row = await service.get_batch(tenant_id=tenant_id, batch_id=batch_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dump batch not found.")
    if row.status != DumpSleepStatusORM.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Dump batch must be completed before dialogue extract.",
        )

    text = format_dump_sleep_dialogue_text(
        briefing_md=row.briefing_md or "",
        voice_note_text=row.voice_note_text,
    )
    if len(text.strip()) < 40:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Dump & Sleep content too short for dialogue extract (min 40 chars).",
        )
    return {
        "ok": True,
        "batch_id": str(batch_id),
        "text": text,
        "char_count": len(text),
    }


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

    try:
        draft = await build_session_recipe_draft(db, tenant_id=tenant_id, session_id=session_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc

    saved = await _persist_operator_recipe_draft(
        db,
        draft,
        source="supervisor_session_icm",
        source_id=str(session_id),
    )
    return {"ok": True, **saved}


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
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid JSON.") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Expected object payload.")

    await process_telegram_webhook(db, update=payload)
    return {"status": "ok"}


__all__ = ["router"]
