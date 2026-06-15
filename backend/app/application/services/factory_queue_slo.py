"""TR4 — Skill Factory queue SLO panel metrics."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger(__name__)

SloStatus = Literal["healthy", "warn", "critical"]


class FactoryQueueSloOut(BaseModel):
    """Queue health snapshot for Skill Factory operator panel."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    status: SloStatus = "healthy"
    awaiting_forge: int = 0
    awaiting_forge_warn: int = 3
    awaiting_forge_critical: int = 8
    critic_approval_rate: float | None = None
    critic_samples: int = 0
    weekly_builds_used: int = 0
    weekly_build_cap: int = 10
    weekly_cap_pct: float = 0.0
    alerts: list[str] = Field(default_factory=list)
    next_operator_action: str = "Queue healthy — no action required."
    loop5_preset_id: str | None = None
    loop5_preset_label: str | None = None
    loop5_min_score: float | None = None
    loop5_max_turns: int | None = None


def _critic_metrics(forge_critic_approved: list[bool | None]) -> tuple[float | None, int]:
    """Compute critic approval rate from forge review samples."""

    reviewed = [value for value in forge_critic_approved if value is not None]
    if not reviewed:
        return None, 0
    approved = sum(1 for value in reviewed if value is True)
    return round(approved / len(reviewed), 4), len(reviewed)


def _resolve_slo_status(
    *,
    awaiting_forge: int,
    awaiting_forge_warn: int,
    awaiting_forge_critical: int,
    critic_rate: float | None,
    critic_rate_warn: float,
    weekly_used: int,
    weekly_cap: int,
    weekly_cap_warn_pct: float,
) -> tuple[SloStatus, list[str], str]:
    """Derive aggregate SLO status, alert lines, and operator next step."""

    alerts: list[str] = []
    weekly_pct = weekly_used / weekly_cap if weekly_cap > 0 else 0.0

    if awaiting_forge >= awaiting_forge_critical:
        alerts.append(
            f"Critical: {awaiting_forge} builds awaiting forge review (≥{awaiting_forge_critical}).",
        )
    elif awaiting_forge >= awaiting_forge_warn:
        alerts.append(
            f"Warn: {awaiting_forge} builds awaiting forge review (≥{awaiting_forge_warn}).",
        )

    if critic_rate is not None and critic_rate < critic_rate_warn:
        pct = int(critic_rate * 100)
        floor = int(critic_rate_warn * 100)
        alerts.append(f"Warn: critic approval rate {pct}% below {floor}% target.")

    if weekly_cap > 0 and weekly_used >= weekly_cap:
        alerts.append(f"Critical: weekly build cap reached ({weekly_used}/{weekly_cap}).")
    elif weekly_cap > 0 and weekly_pct >= weekly_cap_warn_pct:
        alerts.append(
            f"Warn: weekly builds at {int(weekly_pct * 100)}% of cap ({weekly_used}/{weekly_cap}).",
        )

    if any("Critical:" in row for row in alerts):
        status: SloStatus = "critical"
        if awaiting_forge >= awaiting_forge_critical:
            next_action = "Open queue tab — approve or reject awaiting_forge builds before starting new runs."
        elif weekly_used >= weekly_cap:
            next_action = "Pause auto-drain and research cron until the rolling 7-day window resets."
        else:
            next_action = "Resolve critical queue alerts before adding new factory builds."
    elif alerts:
        status = "warn"
        if awaiting_forge >= awaiting_forge_warn:
            next_action = "Review forge queue — drain or reject stale awaiting_forge rows."
        elif critic_rate is not None and critic_rate < critic_rate_warn:
            next_action = "Inspect failed critic loops — tune prompts or reject low-quality forges."
        else:
            next_action = "Monitor weekly cap — defer non-urgent builds if near limit."
    else:
        status = "healthy"
        next_action = "Queue healthy — no action required."

    return status, alerts, next_action


async def compose_factory_queue_slo(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    awaiting_forge: int,
    max_builds_per_week: int,
    forge_critic_approved: list[bool | None],
) -> FactoryQueueSloOut:
    """Build TR4 queue SLO metrics for Skill Factory snapshot."""

    if not settings.factory_queue_slo_enabled:
        return FactoryQueueSloOut(enabled=False)

    from app.application.services.skill_factory_research import _weekly_build_count

    warn_threshold = settings.factory_queue_slo_awaiting_forge_warn
    critical_threshold = settings.factory_queue_slo_awaiting_forge_critical
    critic_rate, critic_samples = _critic_metrics(forge_critic_approved)
    weekly_used = await _weekly_build_count(session, tenant_id=tenant_id)
    weekly_cap = max_builds_per_week
    weekly_pct = round(weekly_used / weekly_cap, 4) if weekly_cap > 0 else 0.0

    status, alerts, next_action = _resolve_slo_status(
        awaiting_forge=awaiting_forge,
        awaiting_forge_warn=warn_threshold,
        awaiting_forge_critical=critical_threshold,
        critic_rate=critic_rate,
        critic_rate_warn=settings.factory_queue_slo_critic_rate_warn,
        weekly_used=weekly_used,
        weekly_cap=weekly_cap,
        weekly_cap_warn_pct=settings.factory_queue_slo_weekly_cap_warn_pct,
    )

    loop5_preset_id: str | None = None
    loop5_preset_label: str | None = None
    loop5_min_score: float | None = None
    loop5_max_turns: int | None = None
    if settings.closed_loop_presets_enabled:
        from app.application.services.closed_loop_presets_service import get_active_loop5_preset_for_tenant

        active = await get_active_loop5_preset_for_tenant(session, tenant_id=tenant_id)
        if active is not None:
            loop5_preset_id = active.preset_id
            loop5_preset_label = active.label
            loop5_min_score = active.min_score
            loop5_max_turns = active.max_turns
        else:
            factory_preset = None
            from app.application.services.closed_loop_presets_service import get_closed_loop_preset

            factory_preset = get_closed_loop_preset("factory_forge")
            if factory_preset is not None:
                loop5_preset_id = factory_preset.preset_id
                loop5_preset_label = factory_preset.label
                loop5_min_score = factory_preset.min_score
                loop5_max_turns = factory_preset.max_turns

    _logger.info(
        "factory_queue_slo.composed",
        agent_id="factory_queue_slo",
        swarm_id=str(tenant_id),
        status=status,
        awaiting_forge=awaiting_forge,
        critic_samples=critic_samples,
        weekly_builds_used=weekly_used,
    )

    return FactoryQueueSloOut(
        enabled=True,
        status=status,
        awaiting_forge=awaiting_forge,
        awaiting_forge_warn=warn_threshold,
        awaiting_forge_critical=critical_threshold,
        critic_approval_rate=critic_rate,
        critic_samples=critic_samples,
        weekly_builds_used=weekly_used,
        weekly_build_cap=weekly_cap,
        weekly_cap_pct=weekly_pct,
        alerts=alerts,
        next_operator_action=next_action,
        loop5_preset_id=loop5_preset_id,
        loop5_preset_label=loop5_preset_label,
        loop5_min_score=loop5_min_score,
        loop5_max_turns=loop5_max_turns,
    )


__all__ = [
    "FactoryQueueSloOut",
    "compose_factory_queue_slo",
]
