"""Track L DA9 — Weekly leadership analytics routine + morning brief KPI."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.analytics_export_lane_service import CRITIC_MIN_SCORE
from app.application.services.analytics_workspace_deliverable_utils import is_analytics_deliverable
from app.application.services.loop_guardrails_service import min_score_to_five_scale
from app.application.services.supervisor.routine_service import create_supervisor_routine
from app.core.config import settings
from app.core.logging import get_logger
from app.domain.outputs.service import list_owned_deliverables
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

ROUTINE_NAME = "Weekly leadership analytics deck"
ANALYTICS_ROUTINE_LANE = "analytics_weekly"

GOAL_TEMPLATE = """\
Weekly leadership analytics deck (verify-first, read-only connectors).

Produce ONE business analytics report for operator leadership review:
1. **Question:** What moved our core KPIs week over week?
2. **Date range:** Last 7 complete days ending yesterday (UTC).
3. **Sources:** GA4 Data API read-only + HiveMind recall — never mutate GA4/warehouse config.
4. **Deliverables:** Executive narrative markdown + ≥3 chart blocks with connector · query · timestamp lineage.
5. **Critic:** self-review-loop rubric ≥4/5 before export staging (Notion/Slides simulate-only).

Template `business-analytics-report`. Skills: business-analytics-playbook, ga4-analytics-playbook, self-review-loop.
Save deliverable tagged analytics + decision-report. Operator approve before live export.
""".strip()

RoutineStatus = Literal["missing", "scheduled", "running", "ready", "disabled"]


class AnalyticsRoutineKpiOut(BaseModel):
    """DA9 routine + morning brief KPI strip for workspace and CBO."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    routine_status: RoutineStatus = "missing"
    routine_id: str | None = None
    routine_name: str = ROUTINE_NAME
    next_run_at: datetime | None = None
    last_run_at: datetime | None = None
    last_session_status: str | None = None
    last_session_href: str | None = None
    report_title: str | None = None
    report_deliverable_id: str | None = None
    critic_score_label: str | None = None
    critic_passed: bool = False
    export_ready: bool = False
    connector_ready_count: int = 0
    morning_brief_line: str = ""
    operator_hint: str = ""
    workspace_href: str = "/apps-tools/analytics?section=overview#analytics-overview"


def _weekly_cron_expr() -> str:
    """Cron for Monday 07:00 UTC (override via settings)."""

    minute = int(settings.analytics_weekly_routine_cron_minute)
    hour = int(settings.analytics_weekly_routine_cron_hour)
    day = int(settings.analytics_weekly_routine_cron_day_of_week)
    return f"{minute} {hour} * * {day}"


async def ensure_analytics_weekly_routine(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    created_by_subject: str | None = None,
) -> dict[str, object]:
    """Idempotently register weekly analytics supervisor routine for tenant."""

    if not settings.analytics_weekly_routine_enabled:
        return {"status": "disabled", "routine_id": None}

    existing = await session.scalar(
        select(SupervisorRoutine)
        .where(
            SupervisorRoutine.tenant_id == tenant_id,
            SupervisorRoutine.name == ROUTINE_NAME,
        )
        .limit(1),
    )
    if existing is not None:
        return {
            "status": "exists",
            "routine_id": str(existing.id),
            "next_run_at": existing.next_run_at.isoformat() if existing.next_run_at else None,
        }

    row = await create_supervisor_routine(
        session,
        name=ROUTINE_NAME,
        goal_template=GOAL_TEMPLATE,
        created_by_subject=created_by_subject or "system:analytics-weekly-routine",
        schedule_kind="cron",
        interval_seconds=None,
        cron_expr=_weekly_cron_expr(),
        runtime_mode="durable",
        roles=["orchestrator", "researcher", "critic"],
        retrieval_contract="customer_history+policy+last_3_tasks",
        skills=[
            "business-analytics-playbook",
            "ga4-analytics-playbook",
            "self-review-loop",
        ],
        context_payload={
            "lane": ANALYTICS_ROUTINE_LANE,
            "simulate_first": True,
            "template_id": "business-analytics-report",
            "critic_min_score": CRITIC_MIN_SCORE,
        },
        tenant_id=tenant_id,
    )
    await session.flush()
    _logger.info(
        "analytics_weekly_routine.created",
        agent_id="analytics_weekly_routine",
        swarm_id=str(tenant_id),
        routine_id=str(row.id),
    )
    return {
        "status": "created",
        "routine_id": str(row.id),
        "next_run_at": row.next_run_at.isoformat() if row.next_run_at else None,
        "schedule": _weekly_cron_expr(),
    }


async def _latest_routine_session(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    routine_id: uuid.UUID,
) -> SupervisorSession | None:
    return await session.scalar(
        select(SupervisorSession)
        .where(
            SupervisorSession.tenant_id == tenant_id,
            SupervisorSession.context_summary["routine_id"].astext == str(routine_id),
        )
        .order_by(desc(SupervisorSession.started_at))
        .limit(1),
    )


def _critic_from_structured(structured: dict[str, object]) -> tuple[float | None, bool]:
    for key in ("critic_rubric_score", "loop_last_rubric_score"):
        raw = structured.get(key)
        if isinstance(raw, (int, float)):
            val = float(raw)
            score = val if val <= 1.0 else val / 5.0
            return score, score >= CRITIC_MIN_SCORE
    raw_five = structured.get("critic_score_5")
    if isinstance(raw_five, (int, float)):
        score = max(0.0, min(float(raw_five) / 5.0, 1.0))
        return score, score >= CRITIC_MIN_SCORE
    return None, False


async def compose_analytics_routine_kpi(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID | None = None,
) -> AnalyticsRoutineKpiOut:
    """Compose weekly routine + latest report KPI for CBO morning brief."""

    if not settings.analytics_weekly_routine_enabled:
        return AnalyticsRoutineKpiOut(
            enabled=False,
            routine_status="disabled",
            operator_hint="Weekly analytics routine disabled.",
        )

    routine = await session.scalar(
        select(SupervisorRoutine)
        .where(
            SupervisorRoutine.tenant_id == tenant_id,
            SupervisorRoutine.name == ROUTINE_NAME,
        )
        .limit(1),
    )

    connector_ready_count = 0
    if dashboard_user_id is not None and settings.analytics_connector_profile_enabled:
        from app.application.services.analytics_connector_profile_service import (
            compose_analytics_connector_profile_snapshot,
        )

        profile = await compose_analytics_connector_profile_snapshot(
            session,
            dashboard_user_id=dashboard_user_id,
        )
        connector_ready_count = profile.ready_count if profile.enabled else 0

    report_title: str | None = None
    deliverable_id: str | None = None
    critic_score_label: str | None = None
    critic_passed = False
    export_ready = False

    if dashboard_user_id is not None:
        rows = await list_owned_deliverables(
            session,
            dashboard_user_id=dashboard_user_id,
            limit=20,
            tag="analytics",
        )
        for row in rows:
            if not is_analytics_deliverable(row):
                continue
            structured = dict(row.structured_json) if isinstance(row.structured_json, dict) else {}
            score, passed = _critic_from_structured(structured)
            report_title = row.title
            deliverable_id = str(row.id)
            critic_score_label = min_score_to_five_scale(score) if score is not None else None
            critic_passed = passed
            export_ready = passed and len(row.markdown_body.strip()) >= 20
            break

    if routine is None:
        hint = "Bootstrap weekly deck routine — runs Monday 07:00 UTC after GA4 connectors ready."
        line = "Analytics deck routine not scheduled — open Analytics workspace to bootstrap."
        return AnalyticsRoutineKpiOut(
            enabled=True,
            routine_status="missing",
            connector_ready_count=connector_ready_count,
            report_title=report_title,
            report_deliverable_id=deliverable_id,
            critic_score_label=critic_score_label,
            critic_passed=critic_passed,
            export_ready=export_ready,
            morning_brief_line=line,
            operator_hint=hint,
        )

    last_session_status: str | None = None
    last_session_href: str | None = None
    last_run_at = routine.last_run_at

    session_row = await _latest_routine_session(
        session,
        tenant_id=tenant_id,
        routine_id=routine.id,
    )
    if session_row is not None:
        last_session_status = session_row.status
        last_session_href = f"/agents#sessions?session={session_row.id}"
        if session_row.completed_at is not None:
            last_run_at = session_row.completed_at
        elif session_row.started_at is not None:
            last_run_at = session_row.started_at

    routine_status: RoutineStatus = "scheduled"
    if last_session_status in {"running", "needs_input", "pending"}:
        routine_status = "running"
    elif export_ready:
        routine_status = "ready"
    elif last_run_at is not None:
        routine_status = "scheduled"

    due_soon = (
        routine.next_run_at is not None
        and routine.next_run_at <= datetime.now(tz=UTC) + timedelta(hours=24)
    )
    if report_title:
        line = f"Analytics deck: «{report_title}» — critic {critic_score_label or 'pending'}."
    elif due_soon:
        line = "Weekly leadership analytics deck due — verify GA4 connector before Monday run."
    else:
        line = f"Next analytics deck {routine.next_run_at.strftime('%a %H:%M UTC') if routine.next_run_at else 'scheduled'}."

    hint_parts = [
        f"Routine {routine_status} — Monday leadership deck via business-analytics-report.",
    ]
    if not critic_passed and report_title:
        hint_parts.append(f"Critic below {min_score_to_five_scale(CRITIC_MIN_SCORE)} — run closed review before export.")
    elif export_ready:
        hint_parts.append("Export lane ready — stage Notion/Slides simulate-first.")

    _logger.info(
        "analytics_weekly_routine.kpi",
        agent_id="analytics_weekly_routine",
        swarm_id=str(tenant_id),
        routine_status=routine_status,
        export_ready=export_ready,
    )

    return AnalyticsRoutineKpiOut(
        enabled=True,
        routine_status=routine_status,
        routine_id=str(routine.id),
        next_run_at=routine.next_run_at,
        last_run_at=last_run_at,
        last_session_status=last_session_status,
        last_session_href=last_session_href,
        report_title=report_title,
        report_deliverable_id=deliverable_id,
        critic_score_label=critic_score_label,
        critic_passed=critic_passed,
        export_ready=export_ready,
        connector_ready_count=connector_ready_count,
        morning_brief_line=line,
        operator_hint=" ".join(hint_parts),
    )


async def run_analytics_weekly_routine_bootstrap_tick(session: AsyncSession) -> dict[str, int]:
    """Ensure weekly analytics routine exists for all tenants (idempotent)."""

    if not settings.analytics_weekly_routine_enabled:
        return {"tenants": 0, "created": 0, "existing": 0}

    tenants = list((await session.scalars(select(Tenant))).all())
    created = 0
    existing = 0
    for tenant in tenants:
        result = await ensure_analytics_weekly_routine(
            session,
            tenant_id=tenant.id,
            created_by_subject="celery:analytics-weekly-bootstrap",
        )
        if result.get("status") == "created":
            created += 1
        elif result.get("status") == "exists":
            existing += 1

    _logger.info(
        "analytics_weekly_routine.bootstrap_tick",
        agent_id="analytics_weekly_routine",
        tenants=len(tenants),
        created=created,
        existing=existing,
    )
    return {"tenants": len(tenants), "created": created, "existing": existing}


__all__ = [
    "ANALYTICS_ROUTINE_LANE",
    "AnalyticsRoutineKpiOut",
    "GOAL_TEMPLATE",
    "ROUTINE_NAME",
    "compose_analytics_routine_kpi",
    "ensure_analytics_weekly_routine",
    "run_analytics_weekly_routine_bootstrap_tick",
]
