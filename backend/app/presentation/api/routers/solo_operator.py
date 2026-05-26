"""Solo operator preset group — trio orchestration, morning brief, session search."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field

from app.application.services.publish_operator_onboarding import compose_publish_onboarding_snapshot
from app.application.services.hive_session_search import search_supervisor_sessions
from app.application.services.morning_hive_brief import compose_morning_hive_brief
from app.application.services.morning_publish_pipeline import (
    compose_morning_publish_pipeline_snapshot,
    run_morning_publish_pipeline,
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


__all__ = ["router"]
