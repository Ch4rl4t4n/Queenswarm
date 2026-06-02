"""Four Cs readiness audit — context, connections, capabilities, cadence (Nate Herk AI OS framework)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.curated_memory_service import CuratedMemoryService
from app.application.services.queen_maintainer.maintainer_guard import count_maintainer_runs_today, maintainer_daily_run_limit
from app.application.services.queen_maintainer.pre_tool_denylist import pre_tool_denylist_summary
from app.application.services.harness_snapshot import _collect_skills_summary
from app.core.config import settings
from app.infrastructure.connectors.mcp_adapter import MCPAdapter
from app.infrastructure.persistence.models.goal import GoalORM
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine

CsLetter = Literal["context", "connections", "capabilities", "cadence"]
CsStatus = Literal["ok", "warn", "missing"]


class FourCsDimension(BaseModel):
    """Score for one C dimension."""

    model_config = ConfigDict(extra="ignore")

    id: CsLetter
    label: str
    score: int = Field(ge=0, le=100)
    status: CsStatus
    signals: list[str] = Field(default_factory=list)
    actions: list[str] = Field(default_factory=list)


class FourCsAuditOut(BaseModel):
    """Read-only Four Cs audit for Settings → Harness."""

    model_config = ConfigDict(extra="ignore")

    generated_at: datetime
    overall_score: int = Field(ge=0, le=100)
    overall_status: CsStatus
    dimensions: list[FourCsDimension] = Field(default_factory=list)
    maintainer_safety: list[dict[str, str]] = Field(default_factory=list)
    manual_anchor: str = "/manual#harness-four-cs"


def _status_from_score(score: int) -> CsStatus:
    if score >= 70:
        return "ok"
    if score >= 40:
        return "warn"
    return "missing"


async def compose_four_cs_audit(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
) -> FourCsAuditOut:
    """Build lightweight Four Cs readiness snapshot (no LLM)."""

    dimensions: list[FourCsDimension] = []

    # —— Context ——
    ctx_signals: list[str] = []
    ctx_actions: list[str] = []
    ctx_score = 20
    if tenant_id is not None:
        bundle = await CuratedMemoryService(session).get_bundle(tenant_id)
        instr = str(bundle.get("instructions") or "").strip()
        if len(instr) >= 200:
            ctx_score += 35
            ctx_signals.append(f"Curated instructions ~{len(instr)} chars")
        elif len(instr) > 0:
            ctx_score += 15
            ctx_signals.append("Curated instructions present (short)")
            ctx_actions.append("Expand Settings → AI · harness curated memory")
        else:
            ctx_actions.append("Add behavioral instructions in Settings → harness")
        if settings.wiki_layer_enabled:
            ctx_score += 25
            ctx_signals.append("Wiki Layer enabled")
        else:
            ctx_actions.append("Enable Wiki Layer for hot-tier recall")
    if settings.skill_hot_tier_enabled:
        ctx_score += 10
        ctx_signals.append("Skill hot tier ON")
    ctx_score = min(100, ctx_score)
    dimensions.append(
        FourCsDimension(
            id="context",
            label="Context",
            score=ctx_score,
            status=_status_from_score(ctx_score),
            signals=ctx_signals,
            actions=ctx_actions,
        ),
    )

    # —— Connections ——
    conn_signals: list[str] = []
    conn_actions: list[str] = []
    conn_score = 15
    mcp_count = 0
    if session is not None:
        mcp_count = len(await MCPAdapter.dynamic_tool_catalog(session))
    if mcp_count >= 3:
        conn_score += 30
        conn_signals.append(f"{mcp_count} MCP tools registered")
    elif mcp_count >= 1:
        conn_score += 15
        conn_signals.append(f"{mcp_count} MCP tool(s)")
    else:
        conn_actions.append("Connect integrations / MCP in Integrations hub")
    if settings.routines_enabled:
        conn_score += 20
        conn_signals.append("Supervisor routines enabled")
    else:
        conn_actions.append("Enable ROUTINES_ENABLED for L3 cadence")
    if settings.supervisor_routine_webhook_enabled:
        conn_score += 15
        conn_signals.append("Routine webhooks (L4) enabled")
    if settings.hive_innovation_lab_enabled:
        conn_score += 10
        conn_signals.append("Innovation Lab enabled")
    conn_score = min(100, conn_score)
    dimensions.append(
        FourCsDimension(
            id="connections",
            label="Connections",
            score=conn_score,
            status=_status_from_score(conn_score),
            signals=conn_signals,
            actions=conn_actions,
        ),
    )

    # —— Capabilities ——
    cap_signals: list[str] = []
    cap_actions: list[str] = []
    cap_score = 10
    skill_count = len(_collect_skills_summary())
    if skill_count >= 10:
        cap_score += 25
    elif skill_count >= 1:
        cap_score += 15
    cap_signals.append(f"{skill_count} harness skills")
    if settings.recipes_enabled:
        cap_score += 20
        cap_signals.append("Recipe Library enabled")
    else:
        cap_actions.append("Enable RECIPES_ENABLED")
    if settings.queen_maintainer_enabled:
        cap_score += 25
        cap_signals.append("Queen Maintainer (PR-only)")
    else:
        cap_actions.append("Enable QUEEN_MAINTAINER_ENABLED for self-improvement")
    if settings.supervisor_pattern_router_enabled:
        cap_score += 10
        cap_signals.append("Pattern Router enabled")
    cap_score = min(100, cap_score)
    dimensions.append(
        FourCsDimension(
            id="capabilities",
            label="Capabilities",
            score=cap_score,
            status=_status_from_score(cap_score),
            signals=cap_signals,
            actions=cap_actions,
        ),
    )

    # —— Cadence ——
    cad_signals: list[str] = []
    cad_actions: list[str] = []
    cad_score = 10
    routine_count = 0
    goal_count = 0
    if tenant_id is not None and session is not None:
        routine_count = int(
            await session.scalar(
                select(func.count())
                .select_from(SupervisorRoutine)
                .where(
                    SupervisorRoutine.tenant_id == tenant_id,
                    SupervisorRoutine.is_active.is_(True),
                ),
            )
            or 0,
        )
        goal_count = int(
            await session.scalar(
                select(func.count()).select_from(GoalORM).where(GoalORM.tenant_id == tenant_id),
            )
            or 0,
        )
        runs_today = await count_maintainer_runs_today(session, tenant_id=tenant_id)
        daily = maintainer_daily_run_limit()
        cad_signals.append(f"Maintainer runs today {runs_today}/{daily}")
    if routine_count >= 1:
        cad_score += 35
        cad_signals.append(f"{routine_count} active routine(s)")
    else:
        cad_actions.append("Schedule a verified recipe as routine (Knowledge → Recipes)")
    if goal_count >= 1:
        cad_score += 25
        cad_signals.append(f"{goal_count} goal(s) tracked")
    else:
        cad_actions.append("Add a multi-iteration goal in Knowledge → Goals (L5)")
    if settings.autonomous_routines_enabled:
        cad_score += 15
        cad_signals.append("Autonomous routines enabled")
    cad_score = min(100, cad_score)
    dimensions.append(
        FourCsDimension(
            id="cadence",
            label="Cadence",
            score=cad_score,
            status=_status_from_score(cad_score),
            signals=cad_signals,
            actions=cad_actions,
        ),
    )

    overall = sum(d.score for d in dimensions) // max(len(dimensions), 1)
    return FourCsAuditOut(
        generated_at=datetime.now(tz=UTC),
        overall_score=overall,
        overall_status=_status_from_score(overall),
        dimensions=dimensions,
        maintainer_safety=pre_tool_denylist_summary(),
    )


__all__ = ["FourCsAuditOut", "FourCsDimension", "compose_four_cs_audit"]
