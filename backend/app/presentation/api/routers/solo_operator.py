"""Solo operator preset group — trio orchestration, morning brief, session search."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.publish_operator_onboarding import compose_publish_onboarding_snapshot
from app.application.services.hive_session_search import search_supervisor_sessions
from app.application.services.mission_operator_search import search_mission_operator
from app.application.services.operator_mission_feed import (
    list_mission_feed_events,
    mark_mission_feed_read,
)
from app.application.services.morning_hive_brief import compose_morning_hive_brief
from app.application.services.morning_publish_pipeline import (
    compose_morning_publish_pipeline_snapshot,
    run_morning_publish_pipeline,
)
from app.application.services.solo_operator_digest_inbox import (
    DigestInboxOut,
    compose_four_lane_digest_inbox,
    promote_digest_session_to_task,
)
from app.application.services.solo_operator_four_lanes import (
    FourLaneId,
    FourLaneSnapshotOut,
    compose_four_lane_snapshot,
    ensure_four_lane_bootstrap,
    pause_legacy_routines,
    set_four_lane_active,
    trigger_automation_lane,
)
from app.application.services.solo_operator_trio import (
    TrioLaneId,
    get_solo_trio_status,
    run_solo_trio_cycle,
    tag_routine_for_trio_lane,
)
from app.presentation.api.deps import DbSession, require_dashboard_user_with_tenant_role
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine

router = APIRouter(prefix="/solo-operator", tags=["Solo operator"])


class TrioRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lane_ids: list[TrioLaneId] | None = Field(
        default=None,
        description="Subset of lanes to trigger; default = all three.",
    )


class TrioBindRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    routine_id: uuid.UUID
    lane_id: TrioLaneId


class MorningPublishRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trigger_content: bool = Field(
        default=True,
        description="Also trigger the content/marketing publish routine when bound.",
    )


@router.get("/trio", summary="Solo operator trio status (preset group, not a new hive)")
async def solo_trio_status(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    return await get_solo_trio_status(db, tenant_id=tenant_id)


@router.post("/trio/run", summary="Trigger bound trio routines (sequential)")
async def solo_trio_run(
    body: TrioRunRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    result = await run_solo_trio_cycle(db, tenant_id=tenant_id, lane_ids=body.lane_ids)
    await db.commit()
    return result


@router.put("/trio/bind", summary="Explicitly bind a routine to a trio lane")
async def solo_trio_bind(
    body: TrioBindRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, str]:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    routine = await db.get(SupervisorRoutine, body.routine_id)
    if routine is None or routine.tenant_id != tenant_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Routine not found.")
    await tag_routine_for_trio_lane(db, routine=routine, lane_id=body.lane_id)
    await db.commit()
    return {"lane_id": body.lane_id, "routine_id": str(routine.id)}


@router.get("/morning-brief", summary="Composite morning digest from trio lanes")
async def morning_hive_brief(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    return await compose_morning_hive_brief(db, tenant_id=tenant_id)


@router.get(
    "/morning-publish-pipeline",
    summary="Morning → Publish pipeline snapshot (Phase D)",
)
async def morning_publish_pipeline_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    if tenant_id is None or user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    snapshot = await compose_morning_publish_pipeline_snapshot(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
    )
    return snapshot.model_dump(mode="json")


@router.post(
    "/morning-publish/run",
    summary="Trigger Life OS + content publish routines (simulate-first)",
)
async def morning_publish_pipeline_run(
    body: MorningPublishRunRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    if tenant_id is None or user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    result = await run_morning_publish_pipeline(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
        trigger_content=body.trigger_content,
    )
    await db.commit()
    return result


@router.get(
    "/publish-onboarding",
    summary="Publish lane onboarding checklist (Brain Pack → simulate → live)",
)
async def publish_onboarding_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    if tenant_id is None or user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    from app.infrastructure.persistence.models.tenant import Tenant

    tenant = await db.get(Tenant, tenant_id)
    snapshot = await compose_publish_onboarding_snapshot(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
        tenant=tenant,
    )
    return snapshot.model_dump(mode="json")


@router.get(
    "/operator-loop",
    summary="Unified Operator Loop — overnight + brief + publish + trading",
)
async def operator_loop_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    if tenant_id is None or user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    from app.application.services.operator_loop import compose_operator_loop_snapshot
    from app.infrastructure.persistence.models.tenant import Tenant

    tenant = await db.get(Tenant, tenant_id)
    snapshot = await compose_operator_loop_snapshot(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
        tenant=tenant,
        phase="morning",
    )
    return snapshot.model_dump(mode="json")


@router.get(
    "/daily-plan",
    summary="Solo daily plan — PO, marketing, trading, ops (top actions)",
)
async def solo_daily_plan(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    if tenant_id is None or user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    from app.application.services.solo_daily_plan import compose_solo_daily_plan
    from app.infrastructure.persistence.models.tenant import Tenant

    tenant = await db.get(Tenant, tenant_id)
    snapshot = await compose_solo_daily_plan(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
        tenant=tenant,
    )
    return snapshot.model_dump(mode="json")


@router.get(
    "/session-presets",
    summary="Quick-start supervisor session goal presets (solo)",
)
async def solo_session_presets(
    _principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    from app.application.services.solo_session_presets import list_solo_session_presets

    presets = list_solo_session_presets()
    return {
        "count": len(presets),
        "presets": [row.model_dump(mode="json") for row in presets],
    }


@router.get("/first-run", summary="Solo first-run wizard checklist (LLM → brief → session)")
async def solo_first_run(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    if tenant_id is None or user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    from app.application.services.solo_operator_first_run import compose_solo_first_run

    snapshot = await compose_solo_first_run(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
    )
    return snapshot.model_dump(mode="json")


class FirstRunStarterBriefRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


@router.post("/first-run/starter-brief", summary="Apply starter PROJECT brief to curated Instructions")
async def solo_first_run_starter_brief(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    _body: FirstRunStarterBriefRequest | None = None,
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    if tenant_id is None or user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    from app.application.services.solo_operator_first_run import apply_starter_project_brief

    return await apply_starter_project_brief(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=user.id,
    )


@router.get("/session-search", summary="Search past supervisor sessions")
async def session_search(
    db: DbSession,
    q: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(20, ge=1, le=50),
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    hits = await search_supervisor_sessions(db, tenant_id=tenant_id, query=q, limit=limit)
    return {"query": q, "count": len(hits), "hits": hits}


@router.get("/mission-search", summary="Unified Mission Control search (sessions + tasks)")
async def mission_search(
    db: DbSession,
    q: str = Query(..., min_length=2, max_length=200),
    session_limit: int = Query(12, ge=1, le=30),
    task_limit: int = Query(12, ge=1, le=30),
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    """Hermes-style instant search across supervisor sessions and kanban tasks."""

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    return await search_mission_operator(
        db,
        tenant_id=tenant_id,
        query=q,
        session_limit=session_limit,
        task_limit=task_limit,
    )


class FourLaneBootstrapRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pause_legacy: bool = Field(default=True, description="Pause non-four-lane routines.")


class FourLaneActiveRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active: bool = Field(description="Enable or pause the lane routine.")


class DigestPromoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=500)
    approve_first: bool = Field(default=True, description="Approve session before creating task.")


@router.get(
    "/four-lanes/digest-inbox",
    response_model=DigestInboxOut,
    summary="Unified digest inbox for four-lane sessions",
)
async def solo_four_lanes_digest_inbox(
    db: DbSession,
    limit: int = Query(20, ge=1, le=50),
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> DigestInboxOut:
    """Pending marketing/e-shop/tech digests with promote-ready flag."""

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    return await compose_four_lane_digest_inbox(db, tenant_id=tenant_id, limit=limit)


@router.post(
    "/four-lanes/digest-inbox/{session_id}/promote",
    summary="Approve digest and create task in one step",
)
async def solo_four_lanes_digest_promote(
    session_id: uuid.UUID,
    body: DigestPromoteRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    if tenant_id is None or user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    subject = f"dashboard:{user.id}"
    result = await promote_digest_session_to_task(
        db,
        tenant_id=tenant_id,
        session_id=session_id,
        reviewer_subject=subject,
        title=body.title,
        approve_first=body.approve_first,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(result.get("error")))
    await db.commit()
    return result


@router.get(
    "/four-lanes",
    response_model=FourLaneSnapshotOut,
    summary="Four-lane solo operator control snapshot",
)
async def solo_four_lanes_snapshot(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> FourLaneSnapshotOut:
    """Return marketing / tech SCV / e-shop / automation lane status."""

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    return await compose_four_lane_snapshot(db, tenant_id=tenant_id)


@router.post(
    "/four-lanes/bootstrap",
    summary="Bootstrap four-lane operator model (pause legacy + ensure lanes)",
)
async def solo_four_lanes_bootstrap(
    body: FourLaneBootstrapRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    user = principal.get("user")
    if tenant_id is None or user is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    subject = f"dashboard:{user.id}"
    result = await ensure_four_lane_bootstrap(
        db,
        tenant_id=tenant_id,
        created_by_subject=subject,
        pause_legacy=body.pause_legacy,
    )
    await db.commit()
    return result


@router.post(
    "/four-lanes/pause-legacy",
    summary="Pause all routines not tagged with four_lane_id",
)
async def solo_four_lanes_pause_legacy(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    result = await pause_legacy_routines(db, tenant_id=tenant_id)
    await db.commit()
    return result


@router.patch(
    "/four-lanes/{lane_id}/active",
    summary="Pause or resume one four-lane routine",
)
async def solo_four_lane_set_active(
    lane_id: FourLaneId,
    body: FourLaneActiveRequest,
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    result = await set_four_lane_active(
        db,
        tenant_id=tenant_id,
        lane_id=lane_id,
        active=body.active,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(result.get("error")))
    await db.commit()
    return result


@router.post(
    "/four-lanes/automation/trigger",
    summary="Manually run Automation Factory lane (approved items → tasks checklist)",
)
async def solo_four_lanes_automation_trigger(
    db: DbSession,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    result = await trigger_automation_lane(db, tenant_id=tenant_id)
    if not result.get("ok"):
        code = status.HTTP_403_FORBIDDEN if result.get("error") == "routines_disabled" else status.HTTP_404_NOT_FOUND
        raise HTTPException(status_code=code, detail=str(result.get("error")))
    await db.commit()
    return result


class MissionFeedDismissRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_ids: list[str] = Field(..., min_length=1, max_length=50)


@router.get("/mission-feed", summary="In-app mission completion feed for notification center")
async def solo_mission_feed(
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
    limit: int = Query(20, ge=1, le=50),
) -> dict[str, Any]:
    """Recent task/session completions surfaced in the sidebar notification center."""

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    events = await list_mission_feed_events(tenant_id, limit=limit)
    unread = sum(1 for row in events if not row.get("read"))
    return {"events": events, "unread": unread, "total": len(events)}


@router.post("/mission-feed/dismiss", summary="Mark mission feed events as read")
async def solo_mission_feed_dismiss(
    body: MissionFeedDismissRequest,
    principal: dict[str, Any] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, Any]:
    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    updated = await mark_mission_feed_read(tenant_id, body.event_ids)
    return {"updated": updated}


__all__ = ["router"]
