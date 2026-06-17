"""Aggregated telemetry for simplified hive dashboards."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select

from app.presentation.api.deps import DashboardSession, DbSession, dashboard_admin_wall, require_dashboard_user_with_tenant_role
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.agent_config import AgentConfig
from app.infrastructure.persistence.models.enums import TaskStatus
from app.infrastructure.persistence.models.task import Task
from app.application.services.dashboard_cockpit import build_dashboard_cockpit_payload
from app.application.services.dashboard_rapid_loop import build_rapid_loop_payload
from app.application.services.dashboard_swarm_board import build_swarm_board_payload
from app.application.services.dashboard_foragers_overview import build_foragers_overview_payload
from app.application.services.dashboard_swarms_overview import build_swarms_overview_payload
from app.application.services.dashboard_task_queue import build_task_queue_payload
from app.application.services.dashboard_time_saved import build_time_saved_payload
from app.application.services.unified_savings import build_unified_savings_payload
from app.application.services.dashboard_workflows import build_workflows_dashboard_payload
from app.application.services.hive_tier import resolve_hive_tier

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(dashboard_admin_wall)],
)


@router.get("/cockpit")
async def dashboard_cockpit(
    db: DbSession,
    _session: DashboardSession,
    agents_limit: int = Query(default=96, ge=1, le=200),
    tasks_limit: int = Query(default=10, ge=1, le=50),
) -> dict[str, object]:
    """Single round-trip bundle: agents, recent tasks, summary, and lite system gauges."""

    return await build_dashboard_cockpit_payload(
        db,
        agents_limit=agents_limit,
        tasks_limit=tasks_limit,
    )


@router.get("/summary")
async def dashboard_summary(db: DbSession, _session: DashboardSession) -> dict[str, object]:
    """Return minimal counts grouped by hive tier plus task backlog."""

    agent_total = await db.scalar(select(func.count()).select_from(Agent))

    stmt_agents_cfg = (
        select(Agent, AgentConfig)
        .outerjoin(AgentConfig, AgentConfig.agent_id == Agent.id)
    )
    rows = (await db.execute(stmt_agents_cfg)).all()

    by_hive_tier: dict[str, int] = {}
    by_status: dict[str, int] = {}
    for agent_row, cfg_row in rows:
        tier_bucket = resolve_hive_tier(agent=agent_row, agent_config=cfg_row) or "unknown"
        by_hive_tier[tier_bucket] = by_hive_tier.get(tier_bucket, 0) + 1
        stat = getattr(agent_row.status, "value", str(agent_row.status))
        by_status[stat] = by_status.get(stat, 0) + 1

    tasks_pending = await db.scalar(
        select(func.count()).select_from(Task).where(Task.status == TaskStatus.PENDING),
    )

    now = datetime.now(tz=UTC)

    return {
        "generated_at": now.isoformat(),
        "agents": {
            "total": int(agent_total or 0),
            "by_status": by_status,
            "by_hive_tier": by_hive_tier,
        },
        "tasks": {
            "pending": int(tasks_pending or 0),
        },
    }


@router.get("/task-queue")
async def dashboard_task_queue(
    db: DbSession,
    _session: DashboardSession,
    limit: int = Query(default=100, ge=1, le=200),
) -> dict[str, object]:
    """Backlog queue with workflow step progress for operator task boards."""

    return await build_task_queue_payload(db, list_limit=limit)


@router.get("/workflows")
async def dashboard_workflows(
    db: DbSession,
    _session: DashboardSession,
    limit: int = Query(default=50, ge=1, le=100),
    focus: uuid.UUID | None = Query(
        default=None,
        description="Pin this workflow as the featured DAG card when present.",
    ),
) -> dict[str, object]:
    """Featured workflow DAG plus recent workflow rows for operator boards."""

    return await build_workflows_dashboard_payload(
        db,
        list_limit=limit,
        focus_workflow_id=focus,
    )


@router.get("/swarm-board")
async def dashboard_swarm_board(db: DbSession, _session: DashboardSession) -> dict[str, object]:
    """Sub-swarm telemetry cards and cross-swarm task handoff feed for operator UI."""

    return await build_swarm_board_payload(db)


@router.get("/swarms-overview")
async def dashboard_swarms_overview(db: DbSession, _session: DashboardSession) -> dict[str, object]:
    """Colonies table, KPI tiles, waggle feed, and hive sync rows for the Swarms page."""

    return await build_swarms_overview_payload(db)


@router.get("/foragers-overview")
async def dashboard_foragers_overview(db: DbSession, _session: DashboardSession) -> dict[str, object]:
    """KPI tiles, configuration table rows, and auto-spawn rules for the Foragers page."""

    return await build_foragers_overview_payload(db)


@router.get("/forager-goldmine-alerts")
async def dashboard_forager_goldmine_alerts(
    db: DbSession,
    principal: dict[str, object] = Depends(require_dashboard_user_with_tenant_role),
    limit: int = Query(default=20, ge=1, le=40),
) -> dict[str, object]:
    """DG7 — Delta alert inbox for goldmine → Mission Kanban dispatch."""

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        return {"enabled": False, "alerts": [], "operator_hint": "Tenant context missing."}
    from app.application.services.forager_goldmine_dispatch_service import compose_forager_goldmine_alerts

    payload = await compose_forager_goldmine_alerts(db, tenant_id=tenant_id, limit=limit)
    return payload.model_dump()


@router.get("/rapid-loop")
async def dashboard_rapid_loop(
    db: DbSession,
    principal: dict[str, object] = Depends(require_dashboard_user_with_tenant_role),
    window_hours: int = Query(default=24, ge=1, le=168),
) -> dict[str, object]:
    """Scrape → reflect → simulate → reward loop counts, SLA, and pattern telemetry."""

    tenant_id = principal.get("tenant_id")
    return await build_rapid_loop_payload(db, window_hours=window_hours, tenant_id=tenant_id)


@router.get("/sub-swarm-fleet")
async def dashboard_sub_swarm_fleet(
    db: DbSession,
    _session: DashboardSession,
) -> dict[str, object]:
    """FP3 — Fleet snapshot: up to 10 colonies with local hive mind sync rings."""

    from app.application.services.sub_swarm_fleet_service import compose_sub_swarm_fleet_snapshot

    payload = await compose_sub_swarm_fleet_snapshot(db)
    return payload.model_dump(mode="json")


@router.post("/sub-swarm-fleet/sync-due")
async def dashboard_sub_swarm_fleet_sync_due(
    db: DbSession,
    _session: DashboardSession,
) -> dict[str, object]:
    """FP3 — Batch record global sync for all due colonies."""

    from app.application.services.sub_swarm_fleet_service import sync_due_sub_swarm_fleet

    try:
        result = await sync_due_sub_swarm_fleet(db)
    except ValueError as exc:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc
    await db.commit()
    return result.model_dump(mode="json")


@router.get("/factory-launch")
async def dashboard_factory_launch(
    db: DbSession,
    principal: dict[str, object] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, object]:
    """REV4 — Skill Factory launch funnel snapshot for Mission Home widget."""

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        return {"enabled": False, "operator_hint": "Tenant context missing."}
    from app.application.services.factory_launch_widget_service import compose_factory_launch_widget_snapshot

    payload = await compose_factory_launch_widget_snapshot(db, tenant_id=tenant_id)
    return payload.model_dump(mode="json")


@router.post("/factory-launch/prepare")
async def dashboard_factory_launch_prepare(
    db: DbSession,
    principal: dict[str, object] = Depends(require_dashboard_user_with_tenant_role),
    limit: int = Query(default=3, ge=1, le=12),
) -> dict[str, object]:
    """REV5 — Export sellable harness batch for Gumroad upload from Mission Home."""

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    from app.application.services.factory_launch_widget_service import prepare_factory_launch_batch_from_widget

    result = await prepare_factory_launch_batch_from_widget(db, tenant_id=tenant_id, limit=limit)
    await db.commit()
    return result


@router.post("/factory-launch/gumroad-draft")
async def dashboard_factory_launch_gumroad_draft(
    db: DbSession,
    principal: dict[str, object] = Depends(require_dashboard_user_with_tenant_role),
    limit: int = Query(default=3, ge=1, le=12),
) -> dict[str, object]:
    """REV6 — Create Gumroad draft listings for launch-queue skills from Mission Home."""

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    from app.application.services.factory_launch_widget_service import draft_factory_launch_gumroad_from_widget

    result = await draft_factory_launch_gumroad_from_widget(db, tenant_id=tenant_id, limit=limit)
    await db.commit()
    return result


@router.post("/factory-launch/gumroad-publish")
async def dashboard_factory_launch_gumroad_publish(
    db: DbSession,
    principal: dict[str, object] = Depends(require_dashboard_user_with_tenant_role),
    limit: int = Query(default=3, ge=1, le=12),
) -> dict[str, object]:
    """REV7 — Publish Gumroad draft listings for launch-queue skills from Mission Home."""

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    from app.application.services.factory_launch_widget_service import publish_factory_launch_gumroad_from_widget

    result = await publish_factory_launch_gumroad_from_widget(db, tenant_id=tenant_id, limit=limit)
    await db.commit()
    return result


@router.post("/factory-launch/revenue-smoke")
async def dashboard_factory_launch_revenue_smoke(
    db: DbSession,
    principal: dict[str, object] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, object]:
    """REV8 — Verify buyer loop: live listing → Gumroad ping → post-purchase onboarding."""

    tenant_id = principal.get("tenant_id")
    if tenant_id is None:
        from fastapi import HTTPException, status

        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant context missing.")
    from app.application.services.factory_launch_widget_service import run_factory_launch_revenue_smoke

    return await run_factory_launch_revenue_smoke(db, tenant_id=tenant_id)


@router.post("/factory-launch/catalog-sync")
async def dashboard_factory_launch_catalog_sync(
    db: DbSession,
    _principal: dict[str, object] = Depends(require_dashboard_user_with_tenant_role),
) -> dict[str, object]:
    """REV9 — Sync Gumroad product URLs into skills catalog (MK7) from Mission Home."""

    from app.application.services.factory_launch_widget_service import sync_factory_launch_catalog_from_widget

    return await sync_factory_launch_catalog_from_widget(db)


@router.get("/time-saved")
async def dashboard_time_saved(
    db: DbSession,
    _session: DashboardSession,
    window_days: int = Query(default=30, ge=1, le=90),
) -> dict[str, object]:
    """Verified workflow ROI — hours saved by template/recipe/custom."""

    return await build_time_saved_payload(db, window_days=window_days)


@router.get("/unified-savings")
async def dashboard_unified_savings(
    db: DbSession,
    principal: dict[str, object] = Depends(require_dashboard_user_with_tenant_role),
    window_days: int = Query(default=30, ge=1, le=90),
) -> dict[str, object]:
    """Merged time ROI + LLM cost savings for the Unified Savings Dashboard."""

    tenant_id = principal.get("tenant_id")
    return await build_unified_savings_payload(
        db,
        tenant_id=tenant_id,
        window_days=window_days,
    )


__all__ = ["router"]
