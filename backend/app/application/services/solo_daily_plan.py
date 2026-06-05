"""Solo daily plan — top actions for PO, marketing, trading, and ops (max 3–5 items)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.operator_loop import compose_operator_loop_snapshot
from app.application.services.solo_operator_trio import get_solo_trio_status
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant

SoloDailyLane = Literal["po", "marketing", "trading", "ops"]


class SoloDailyPlanItemOut(BaseModel):
    """One prioritized action for the operator's day."""

    model_config = ConfigDict(extra="ignore")

    id: str
    lane: SoloDailyLane
    title: str
    detail: str
    href: str | None = None
    priority: int = Field(ge=1, le=5, description="1 = do first")


class SoloDailyPlanOut(BaseModel):
    """Merged daily plan for solo operator dashboard + Operator Hub."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    phase: str
    items: list[SoloDailyPlanItemOut] = Field(default_factory=list)
    links: dict[str, str] = Field(default_factory=dict)


def _lane_for_loop_action(action_id: str) -> SoloDailyLane:
    if action_id in {"approve_publish", "publish_onboarding"}:
        return "marketing"
    if action_id in {"trading_halted", "paper_tick"}:
        return "trading"
    return "ops"


def _priority_for_loop_action(priority: str) -> int:
    if priority == "high":
        return 1
    if priority == "medium":
        return 2
    return 3


async def compose_solo_daily_plan(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
    max_items: int = 5,
) -> SoloDailyPlanOut:
    """Build a focused daily plan from Operator Loop + solo lane defaults."""

    if not settings.solo_mode_enabled and not settings.operator_loop_enabled:
        return SoloDailyPlanOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            phase="anytime",
        )

    loop = await compose_operator_loop_snapshot(
        session,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
        phase="morning",
    )

    items: list[SoloDailyPlanItemOut] = []

    # PO lane — always surface one bank/product-owner action (no sensitive data in prompts).
    items.append(
        SoloDailyPlanItemOut(
            id="po_supervisor_brief",
            lane="po",
            title="Bank PO — brief alebo backlog review",
            detail="Nová supervisor session: stakeholder brief, PI plán alebo rozhodnutie. "
            "Bez citlivých bank dát v LLM — len anonymizované / verejné podklady.",
            href="/agents?preset=bank-po-brief",
            priority=2,
        ),
    )

    for action in loop.actions:
        items.append(
            SoloDailyPlanItemOut(
                id=f"loop_{action.id}",
                lane=_lane_for_loop_action(action.id),
                title=action.label,
                detail=action.detail,
                href=action.href,
                priority=_priority_for_loop_action(action.priority),
            ),
        )

    if settings.calendar_daily_planner_enabled:
        from app.application.services.calendar_daily_planner import compose_calendar_daily_planner

        calendar = await compose_calendar_daily_planner(
            session,
            dashboard_user_id=dashboard_user_id,
        )
        for event in calendar.items[:3]:
            items.append(
                SoloDailyPlanItemOut(
                    id=event.id,
                    lane="po",
                    title=f"Calendar: {event.title}",
                    detail=event.detail or calendar.message,
                    href=event.href,
                    priority=1,
                ),
            )

    trio = await get_solo_trio_status(session, tenant_id=tenant_id)
    bound = int(trio.get("lanes_bound") or trio.get("bound_lane_count") or 0)
    if bound >= 1:
        items.append(
            SoloDailyPlanItemOut(
                id="trio_cycle",
                lane="ops",
                title="Run today's cycle (My 3 Bees)",
                detail=f"{bound}/3 lanes bound — spusti ranný trio cyklus.",
                href="/settings/harness",
                priority=1 if bound >= 2 else 3,
            ),
        )
    else:
        items.append(
            SoloDailyPlanItemOut(
                id="bind_trio",
                lane="ops",
                title="Bind My 3 Bees routines",
                detail="Settings → AI harness → prepoj Hive Learner / SCV / Life OS.",
                href="/settings/harness",
                priority=3,
            ),
        )

    onboard_pct = 0
    if isinstance(loop.publish_onboarding, dict):
        onboard_pct = int(loop.publish_onboarding.get("progress_pct") or 0)
    has_onboard_action = any(action.id == "publish_onboarding" for action in loop.actions)
    if onboard_pct < 100 and not has_onboard_action:
        items.append(
            SoloDailyPlanItemOut(
                id="marketing_onboarding",
                lane="marketing",
                title=f"Publish onboarding {onboard_pct}%",
                detail="Dokonči OAuth + simulate pred prvým live postom.",
                href="/settings/harness#operator-hub",
                priority=1 if onboard_pct < 60 else 2,
            ),
        )

    # Dedupe by id, sort by priority, cap
    seen: set[str] = set()
    unique: list[SoloDailyPlanItemOut] = []
    for row in sorted(items, key=lambda x: (x.priority, x.lane)):
        if row.id in seen:
            continue
        seen.add(row.id)
        unique.append(row)

    return SoloDailyPlanOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        phase=loop.phase,
        items=unique[:max_items],
        links={
            **loop.links,
            "daily_plan_doc": "docs/SOLO_OPERATOR_TRIO_GUIDE.md",
            "operator_hub": "/settings/harness#operator-hub",
        },
    )


__all__ = ["SoloDailyPlanOut", "SoloDailyPlanItemOut", "compose_solo_daily_plan"]
