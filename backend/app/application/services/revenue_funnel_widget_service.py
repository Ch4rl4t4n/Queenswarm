"""MK10 — Unified revenue funnel strip for Mission Home (MK6 scale + Gumroad launch)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.catalog_wave_widget_service import compose_catalog_wave_widget_snapshot
from app.application.services.factory_launch_widget_service import compose_factory_launch_widget_snapshot
from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger(__name__)


class RevenueFunnelStepOut(BaseModel):
    """One step in the MK6 → sellable → live → loop funnel."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    done: bool
    detail: str


class RevenueFunnelPrimaryActionOut(BaseModel):
    """Highest-priority operator CTA derived from catalog + launch snapshots."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    href: str | None = None
    post_path: str | None = None
    priority: str = "high"


class RevenueFunnelWidgetOut(BaseModel):
    """Unified revenue funnel snapshot for Mission Home strip."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    scorecard_clean_count: int = 0
    mk6_target: int = 50
    gap_to_mk6: int = 0
    sellable_count: int = 0
    published_gumroad_count: int = 0
    revenue_loop_ready: bool = False
    funnel_complete: bool = False
    steps: list[RevenueFunnelStepOut] = Field(default_factory=list)
    primary_action: RevenueFunnelPrimaryActionOut | None = None
    operator_hint: str = ""
    factory_href: str = "/apps-tools/skill-factory"
    catalog_href: str = "/skills"
    launch_href: str = "/apps-tools/skill-factory?section=launch#launch"


def _derive_primary_action(
    *,
    catalog_enabled: bool,
    launch_enabled: bool,
    scorecard_clean: int,
    mk6_target: int,
    gap_to_mk6: int,
    seed_pending_count: int,
    wave_complete: bool,
    sellable_count: int,
    launch_and_verify_available: bool,
    full_funnel_available: bool,
    prepare_available: bool,
    factory_href: str,
    catalog_href: str,
    launch_href: str,
) -> RevenueFunnelPrimaryActionOut | None:
    """Pick one primary CTA — launch-first when sellable, scale-first when catalog gap."""

    if launch_enabled and launch_and_verify_available:
        return RevenueFunnelPrimaryActionOut(
            id="launch_and_verify",
            label="Launch & verify",
            post_path="dashboard/factory-launch/launch-and-verify",
            priority="high",
        )
    if launch_enabled and full_funnel_available:
        return RevenueFunnelPrimaryActionOut(
            id="full_funnel",
            label="Run full launch funnel",
            post_path="dashboard/factory-launch/full-funnel",
            priority="high",
        )
    if catalog_enabled and seed_pending_count > 0 and gap_to_mk6 > 0:
        return RevenueFunnelPrimaryActionOut(
            id="factory_seeds",
            label="Build pending catalog seeds",
            href=factory_href,
            priority="medium",
        )
    if launch_enabled and prepare_available and sellable_count > 0:
        return RevenueFunnelPrimaryActionOut(
            id="prepare",
            label="Prepare Gumroad batch",
            post_path="dashboard/factory-launch/prepare",
            priority="medium",
        )
    if catalog_enabled and not wave_complete and gap_to_mk6 > 0:
        return RevenueFunnelPrimaryActionOut(
            id="factory_scale",
            label=f"Scale factory ({scorecard_clean}/{mk6_target} MK6)",
            href=factory_href,
            priority="medium",
        )
    if launch_enabled and sellable_count == 0:
        return RevenueFunnelPrimaryActionOut(
            id="build_sellable",
            label="Build sellable harness",
            href=launch_href,
            priority="medium",
        )
    return RevenueFunnelPrimaryActionOut(
        id="catalog",
        label="View skills catalog",
        href=catalog_href,
        priority="low",
    )


def _compose_steps(
    *,
    wave_complete: bool,
    scorecard_clean: int,
    mk6_target: int,
    sellable_count: int,
    published_gumroad_count: int,
    revenue_loop_ready: bool,
) -> list[RevenueFunnelStepOut]:
    """Four-step funnel: catalog scale → sellable → live listing → closed loop."""

    return [
        RevenueFunnelStepOut(
            id="catalog_scale",
            label="MK6 catalog scale",
            done=wave_complete,
            detail=f"{scorecard_clean}/{mk6_target} scorecard-clean",
        ),
        RevenueFunnelStepOut(
            id="sellable_harness",
            label="Sellable harness",
            done=sellable_count > 0,
            detail=f"{sellable_count} sellable in library",
        ),
        RevenueFunnelStepOut(
            id="gumroad_live",
            label="Live Gumroad listing",
            done=published_gumroad_count > 0,
            detail=f"{published_gumroad_count} published",
        ),
        RevenueFunnelStepOut(
            id="revenue_loop",
            label="Revenue loop closed",
            done=revenue_loop_ready,
            detail="webhook + onboarding + catalog" if revenue_loop_ready else "verify purchase path",
        ),
    ]


async def compose_revenue_funnel_widget_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> RevenueFunnelWidgetOut:
    """Merge MK9 catalog wave + REV factory launch into one funnel snapshot."""

    if not settings.revenue_funnel_mission_home_enabled:
        return RevenueFunnelWidgetOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            operator_hint="Revenue funnel strip disabled.",
        )

    catalog = compose_catalog_wave_widget_snapshot()
    launch = await compose_factory_launch_widget_snapshot(session, tenant_id=tenant_id)

    catalog_active = catalog.enabled and settings.catalog_wave_mission_home_enabled
    launch_active = launch.enabled and settings.factory_launch_mission_home_enabled

    if not catalog_active and not launch_active:
        return RevenueFunnelWidgetOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            operator_hint="Enable catalog wave or factory launch widgets.",
        )

    scorecard_clean = catalog.scorecard_clean_count if catalog_active else 0
    mk6_target = catalog.mk6_target if catalog_active else 50
    gap_to_mk6 = catalog.gap_to_mk6 if catalog_active else 0
    wave_complete = catalog.wave_complete if catalog_active else False
    seed_pending = catalog.seed_pending_count if catalog_active else 0

    sellable = launch.sellable_count if launch_active else 0
    published = launch.published_gumroad_count if launch_active else 0
    loop_ready = launch.revenue_loop_ready if launch_active else False

    steps = _compose_steps(
        wave_complete=wave_complete,
        scorecard_clean=scorecard_clean,
        mk6_target=mk6_target,
        sellable_count=sellable,
        published_gumroad_count=published,
        revenue_loop_ready=loop_ready,
    )
    funnel_complete = all(step.done for step in steps)

    primary = None if funnel_complete else _derive_primary_action(
        catalog_enabled=catalog_active,
        launch_enabled=launch_active,
        scorecard_clean=scorecard_clean,
        mk6_target=mk6_target,
        gap_to_mk6=gap_to_mk6,
        seed_pending_count=seed_pending,
        wave_complete=wave_complete,
        sellable_count=sellable,
        launch_and_verify_available=launch.launch_and_verify_available if launch_active else False,
        full_funnel_available=launch.full_funnel_available if launch_active else False,
        prepare_available=launch.prepare_available if launch_active else False,
        factory_href=catalog.factory_href if catalog_active else launch.factory_href,
        catalog_href=catalog.catalog_href if catalog_active else launch.catalog_href,
        launch_href=launch.launch_href if launch_active else "/apps-tools/skill-factory?section=launch#launch",
    )

    if funnel_complete:
        hint = (
            f"Revenue funnel complete — {published} live listing(s), loop closed. "
            "Drive traffic to letagentscook.org."
        )
    elif launch.operator_hint and launch_active:
        hint = launch.operator_hint
    elif catalog.operator_hint and catalog_active:
        hint = catalog.operator_hint
    elif primary:
        hint = f"Next: {primary.label}."
    else:
        hint = "Run Factory → export → Launch & verify on Mission Home."

    _logger.info(
        "revenue_funnel_widget.composed",
        agent_id="revenue_funnel_widget",
        tenant_id=str(tenant_id),
        scorecard_clean=scorecard_clean,
        sellable=sellable,
        published=published,
        loop_ready=loop_ready,
        funnel_complete=funnel_complete,
        primary_id=primary.id if primary else None,
    )

    return RevenueFunnelWidgetOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        scorecard_clean_count=scorecard_clean,
        mk6_target=mk6_target,
        gap_to_mk6=gap_to_mk6,
        sellable_count=sellable,
        published_gumroad_count=published,
        revenue_loop_ready=loop_ready,
        funnel_complete=funnel_complete,
        steps=steps,
        primary_action=primary,
        operator_hint=hint,
        factory_href=catalog.factory_href if catalog_active else launch.factory_href,
        catalog_href=catalog.catalog_href if catalog_active else launch.catalog_href,
        launch_href=launch.launch_href if launch_active else "/apps-tools/skill-factory?section=launch#launch",
    )


__all__ = [
    "RevenueFunnelPrimaryActionOut",
    "RevenueFunnelStepOut",
    "RevenueFunnelWidgetOut",
    "compose_revenue_funnel_widget_snapshot",
]
