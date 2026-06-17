"""REV4 — Factory Launch widget for Mission Home (Gumroad sellable harness funnel)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger(__name__)


class FactoryLaunchWidgetOut(BaseModel):
    """Skill Factory launch funnel snapshot for solo Mission Home."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    sellable_count: int = 0
    launch_queue_count: int = 0
    draft_count: int = 0
    rejected_count: int = 0
    library_count: int = 0
    building_count: int = 0
    gumroad_ready: bool = False
    funnel_ready: bool = False
    operator_hint: str = ""
    factory_href: str = "/apps-tools/skill-factory"
    launch_href: str = "/apps-tools/skill-factory?section=launch#launch"
    top_launch_titles: list[str] = Field(default_factory=list)


async def compose_factory_launch_widget_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> FactoryLaunchWidgetOut:
    """Aggregate Skill Factory launch readiness for Mission Home widget."""

    now = datetime.now(tz=UTC)
    if not settings.factory_launch_mission_home_enabled or not settings.skill_factory_enabled:
        return FactoryLaunchWidgetOut(
            enabled=False,
            generated_at=now,
            operator_hint="Skill Factory launch widget disabled.",
        )

    from app.application.services.skill_factory_service import compose_skill_factory_snapshot

    snapshot = await compose_skill_factory_snapshot(session, tenant_id=tenant_id)
    launch = snapshot.launch_readiness
    sellable = int(launch.sellable_count if launch is not None else 0)
    draft = int(launch.draft_count if launch is not None else 0)
    rejected = int(launch.rejected_count if launch is not None else 0)
    launch_queue = list(snapshot.launch_queue or [])
    gumroad_ready = bool(
        snapshot.gumroad_listing_ready
        or (launch is not None and (launch.gumroad_token_configured or launch.gumroad_manual_ready)),
    )
    funnel_ready = sellable > 0 and len(launch_queue) > 0

    if sellable == 0:
        hint = "No sellable harness yet — run Factory research → build → approve forge."
    elif not launch_queue:
        hint = f"{sellable} sellable skill(s) — open Launch tab to queue Gumroad export."
    elif not gumroad_ready:
        hint = f"{len(launch_queue)} in launch queue — set Gumroad token or manual upload path."
    else:
        hint = f"Revenue funnel ready — {len(launch_queue)} harness pack(s) queued for Gumroad."

    titles = [str(row.title or row.slug) for row in launch_queue[:3] if getattr(row, "title", None) or getattr(row, "slug", None)]

    _logger.info(
        "factory_launch_widget.composed",
        agent_id="factory_launch_widget",
        swarm_id=str(tenant_id),
        sellable_count=sellable,
        launch_queue_count=len(launch_queue),
    )
    return FactoryLaunchWidgetOut(
        enabled=True,
        generated_at=now,
        sellable_count=sellable,
        launch_queue_count=len(launch_queue),
        draft_count=draft,
        rejected_count=rejected,
        library_count=len(snapshot.library or []),
        building_count=int(snapshot.building_count or 0),
        gumroad_ready=gumroad_ready,
        funnel_ready=funnel_ready,
        operator_hint=hint,
        top_launch_titles=titles,
    )


__all__ = ["FactoryLaunchWidgetOut", "compose_factory_launch_widget_snapshot"]
