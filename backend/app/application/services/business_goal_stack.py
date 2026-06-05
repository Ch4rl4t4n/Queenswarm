"""BA2 — Business Goal Stack: tenant KPIs, drift alerts, mission tagging hints."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.application.services.business_operator import (
        BusinessCatalogSummaryOut,
        BusinessMissionSummaryOut,
        BusinessRevenueSummaryOut,
    )
from app.core.logging import get_logger
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

BusinessGoalKind = Literal[
    "gumroad_listings",
    "mission_triage_clear",
    "factory_queue",
    "catalog_products",
    "polymarket_live",
    "custom",
]

DriftSeverity = Literal["ok", "warning", "critical"]


class BusinessGoalIn(BaseModel):
    """One editable tenant business goal."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, max_length=64)
    kind: BusinessGoalKind
    label: str = Field(..., min_length=1, max_length=120)
    target_value: float = Field(ge=0)
    unit: str = Field(default="", max_length=32)
    enabled: bool = True


class BusinessGoalProgressOut(BaseModel):
    """Goal with measured progress and drift."""

    model_config = ConfigDict(extra="ignore")

    id: str
    kind: BusinessGoalKind
    label: str
    target_value: float
    current_value: float
    unit: str
    enabled: bool = True
    drift_severity: DriftSeverity = "ok"
    drift_detail: str = ""
    mission_lane: str | None = None


class BusinessGoalStackOut(BaseModel):
    """Goal stack rollup for CBO."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    goals: list[BusinessGoalProgressOut] = Field(default_factory=list)
    drift_count: int = 0
    critical_drift_count: int = 0


class BusinessGoalStackPatchIn(BaseModel):
    """Replace tenant goal definitions."""

    model_config = ConfigDict(extra="forbid")

    goals: list[BusinessGoalIn] = Field(default_factory=list, max_length=12)


GOAL_STACK_KEY = "business_goals"
DEFAULT_GOALS: tuple[BusinessGoalIn, ...] = (
    BusinessGoalIn(
        id="gumroad_live",
        kind="gumroad_listings",
        label="Gumroad listings live",
        target_value=5,
        unit="listings",
    ),
    BusinessGoalIn(
        id="mission_inbox_zero",
        kind="mission_triage_clear",
        label="Mission triage inbox zero",
        target_value=0,
        unit="triage",
    ),
    BusinessGoalIn(
        id="factory_queue",
        kind="factory_queue",
        label="Factory queue drained",
        target_value=0,
        unit="queued",
    ),
)


def _goal_root(tenant: Tenant | None) -> dict[str, Any]:
    if tenant is None:
        return {}
    root = dict(tenant.operator_settings or {})
    block = root.get(GOAL_STACK_KEY)
    return dict(block) if isinstance(block, dict) else {}


def load_goal_definitions(tenant: Tenant | None) -> list[BusinessGoalIn]:
    """Read goal definitions from tenant operator_settings."""

    block = _goal_root(tenant)
    raw = block.get("goals")
    if not isinstance(raw, list) or not raw:
        return list(DEFAULT_GOALS)
    out: list[BusinessGoalIn] = []
    for row in raw:
        if not isinstance(row, dict):
            continue
        try:
            out.append(BusinessGoalIn.model_validate(row))
        except ValueError:
            continue
    return out or list(DEFAULT_GOALS)


def persist_goal_definitions(tenant: Tenant, goals: list[BusinessGoalIn]) -> None:
    """Write goals to tenant operator_settings (caller commits)."""

    root = dict(tenant.operator_settings or {})
    root[GOAL_STACK_KEY] = {
        "goals": [goal.model_dump(mode="json") for goal in goals],
        "updated_at": datetime.now(tz=UTC).isoformat(),
    }
    tenant.operator_settings = root


def _lane_for_kind(kind: BusinessGoalKind) -> str | None:
    mapping: dict[BusinessGoalKind, str] = {
        "gumroad_listings": "revenue",
        "catalog_products": "marketing",
        "factory_queue": "factory",
        "mission_triage_clear": "mission",
        "polymarket_live": "trading",
    }
    return mapping.get(kind)


def _measure_goal(
    goal: BusinessGoalIn,
    *,
    catalog: BusinessCatalogSummaryOut,
    missions: BusinessMissionSummaryOut,
    revenue: BusinessRevenueSummaryOut,
    factory_queue_count: int,
    polymarket_live_ready: bool,
) -> tuple[float, DriftSeverity, str]:
    """Return current value, drift severity, and detail for one goal."""

    if goal.kind == "gumroad_listings":
        current = float(catalog.gumroad_linked_count)
        target = goal.target_value
        if current >= target:
            return current, "ok", f"{int(current)}/{int(target)} listings linked"
        gap = target - current
        severity: DriftSeverity = "critical" if gap >= max(3, target * 0.5) else "warning"
        return current, severity, f"{int(current)}/{int(target)} — {int(gap)} listing(s) behind goal"

    if goal.kind == "catalog_products":
        current = float(catalog.product_count)
        target = goal.target_value
        if current >= target:
            return current, "ok", f"{int(current)}/{int(target)} catalog products"
        return current, "warning", f"{int(current)}/{int(target)} — grow catalog before marketing push"

    if goal.kind == "mission_triage_clear":
        current = float(missions.triage_count)
        if current <= goal.target_value:
            return current, "ok", "Triage inbox clear"
        blocked = missions.blocked_count
        detail = f"{int(current)} triage mission(s)"
        if blocked:
            detail += f", {blocked} blocked"
        severity = "critical" if current >= 3 else "warning"
        return current, severity, detail

    if goal.kind == "factory_queue":
        current = float(factory_queue_count)
        if current <= goal.target_value:
            return current, "ok", "Factory queue clear"
        severity = "warning" if current <= 3 else "critical"
        return current, severity, f"{int(current)} skill(s) queued or building"

    if goal.kind == "polymarket_live":
        current = 1.0 if polymarket_live_ready else 0.0
        if polymarket_live_ready:
            return current, "ok", "Polymarket live lane ready (CLOB + live flag)"
        return current, "critical", "Polymarket live not ready — vault CLOB and enable live flag"

    if goal.kind == "custom":
        return 0.0, "ok", revenue.next_operator_action or "Custom goal — track manually"

    return 0.0, "ok", ""


async def compose_business_goal_stack(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    tenant: Tenant | None,
    catalog: BusinessCatalogSummaryOut,
    missions: BusinessMissionSummaryOut,
    revenue: BusinessRevenueSummaryOut,
    factory_queue_count: int = 0,
    polymarket_live_ready: bool = False,
) -> BusinessGoalStackOut:
    """Measure tenant goals and compute drift for CBO."""

    _ = db, tenant_id
    definitions = [g for g in load_goal_definitions(tenant) if g.enabled]
    goals: list[BusinessGoalProgressOut] = []
    drift_count = 0
    critical_count = 0

    for goal in definitions:
        current, severity, detail = _measure_goal(
            goal,
            catalog=catalog,
            missions=missions,
            revenue=revenue,
            factory_queue_count=factory_queue_count,
            polymarket_live_ready=polymarket_live_ready,
        )
        if severity != "ok":
            drift_count += 1
        if severity == "critical":
            critical_count += 1
        goals.append(
            BusinessGoalProgressOut(
                id=goal.id,
                kind=goal.kind,
                label=goal.label,
                target_value=goal.target_value,
                current_value=current,
                unit=goal.unit,
                enabled=goal.enabled,
                drift_severity=severity,
                drift_detail=detail,
                mission_lane=_lane_for_kind(goal.kind),
            ),
        )

    return BusinessGoalStackOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        goals=goals,
        drift_count=drift_count,
        critical_drift_count=critical_count,
    )


def goal_id_for_lane(lane: str) -> str | None:
    """Map CBO lane to primary goal id for mission tagging."""

    mapping = {
        "revenue": "gumroad_live",
        "marketing": "catalog_products",
        "factory": "factory_queue",
        "mission": "mission_inbox_zero",
        "trading": "polymarket_live",
    }
    return mapping.get(lane)


def mission_goal_payload(lane: str) -> dict[str, str]:
    """Payload fragment to tag missions with business goal."""

    goal_id = goal_id_for_lane(lane)
    if goal_id is None:
        return {}
    return {"business_goal_id": goal_id, "business_goal_lane": lane}


__all__ = [
    "BusinessGoalIn",
    "BusinessGoalProgressOut",
    "BusinessGoalStackOut",
    "BusinessGoalStackPatchIn",
    "compose_business_goal_stack",
    "goal_id_for_lane",
    "load_goal_definitions",
    "mission_goal_payload",
    "persist_goal_definitions",
]
