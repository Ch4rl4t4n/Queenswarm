"""FP3 — Sub-swarm fleet snapshot for Mission Home and operator dashboards."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.dashboard_swarms_overview import build_swarms_overview_payload
from app.application.services.hive_sync import mark_sub_swarm_globally_synced
from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger(__name__)

MAX_FLEET_COLONIES = 10


class SubSwarmFleetColonyOut(BaseModel):
    """One colony row in the fleet widget."""

    model_config = ConfigDict(extra="ignore")

    id: str
    slug: str
    display_name: str
    lane: str
    lane_label: str
    member_count: int
    recommended_bee_count: int
    is_active: bool
    needs_sync: bool
    sync_due_in_sec: int
    sync_progress_pct: int
    wizard_template: str | None = None
    goal_preview: str | None = None
    workspace_href: str = "/swarms"


class SubSwarmFleetSnapshotOut(BaseModel):
    """Fleet-level local hive mind + 5 min sync cadence."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    hive_sync_interval_sec: int
    colony_count: int = 0
    due_sync_count: int = 0
    total_bees: int = 0
    colonies: list[SubSwarmFleetColonyOut] = Field(default_factory=list)
    operator_hint: str = ""
    swarms_href: str = "/swarms"


class SubSwarmFleetSyncDueOut(BaseModel):
    """Batch global sync ack for due colonies."""

    model_config = ConfigDict(extra="ignore")

    ok: bool = True
    synced_count: int = 0
    synced_colony_ids: list[str] = Field(default_factory=list)
    message: str = ""


def _colony_from_overview(row: dict[str, Any]) -> SubSwarmFleetColonyOut:
    mind = dict(row.get("local_mind") or {})
    return SubSwarmFleetColonyOut(
        id=str(row["id"]),
        slug=str(row.get("slug") or ""),
        display_name=str(row.get("display_name") or row.get("slug") or "Colony"),
        lane=str(row.get("lane") or ""),
        lane_label=str(row.get("lane_label") or ""),
        member_count=int(row.get("member_count") or 0),
        recommended_bee_count=int(mind.get("recommended_bee_count") or settings.sub_swarm_size),
        is_active=bool(row.get("is_active")),
        needs_sync=bool(mind.get("needs_sync")),
        sync_due_in_sec=int(mind.get("sync_due_in_sec") or 0),
        sync_progress_pct=int(mind.get("sync_progress_pct") or 0),
        wizard_template=str(mind.get("wizard_template") or "") or None,
        goal_preview=str(mind.get("goal_preview") or "") or None,
        workspace_href=f"/swarms?colony={row['id']}",
    )


async def compose_sub_swarm_fleet_snapshot(session: AsyncSession) -> SubSwarmFleetSnapshotOut:
    """Aggregate up to 10 active colonies with local hive mind sync rings."""

    now = datetime.now(tz=UTC)
    if not settings.sub_swarm_fleet_widget_enabled:
        return SubSwarmFleetSnapshotOut(
            enabled=False,
            generated_at=now,
            hive_sync_interval_sec=int(settings.hive_sync_interval_sec),
            operator_hint="Sub-swarm fleet widget disabled.",
        )

    overview = await build_swarms_overview_payload(session)
    raw_colonies = list(overview.get("colonies") or [])
    active_first = sorted(
        raw_colonies,
        key=lambda row: (
            0 if bool(row.get("is_active")) else 1,
            0 if bool((row.get("local_mind") or {}).get("needs_sync")) else 1,
            str(row.get("display_name") or ""),
        ),
    )
    colonies = [_colony_from_overview(row) for row in active_first[:MAX_FLEET_COLONIES]]
    due_count = sum(1 for row in colonies if row.needs_sync)
    interval = int(overview.get("hive_sync_interval_sec") or settings.hive_sync_interval_sec)
    kpis = dict(overview.get("kpis") or {})

    if not colonies:
        hint = "No sub-swarms yet — bootstrap with scripts/hive_seed.py or Swarm Builder."
    elif due_count:
        hint = f"{due_count} colony/colonies due for global sync (~every {max(1, interval // 60)} min)."
    else:
        hint = f"All {len(colonies)} colonies in cadence — local hive minds synced to global state."

    return SubSwarmFleetSnapshotOut(
        enabled=True,
        generated_at=now,
        hive_sync_interval_sec=interval,
        colony_count=len(colonies),
        due_sync_count=due_count,
        total_bees=int(kpis.get("total_bees") or 0),
        colonies=colonies,
        operator_hint=hint,
    )


async def sync_due_sub_swarm_fleet(
    session: AsyncSession,
    *,
    limit: int = MAX_FLEET_COLONIES,
) -> SubSwarmFleetSyncDueOut:
    """Record global sync checkpoints for all due colonies (max ``limit``)."""

    if not settings.sub_swarm_fleet_widget_enabled:
        raise ValueError("Sub-swarm fleet widget is disabled.")

    overview = await build_swarms_overview_payload(session)
    synced_ids: list[str] = []
    cap = max(1, min(limit, MAX_FLEET_COLONIES))

    for row in overview.get("colonies") or []:
        mind = dict(row.get("local_mind") or {})
        if not mind.get("needs_sync"):
            continue
        colony_id = uuid.UUID(str(row["id"]))
        stamped = await mark_sub_swarm_globally_synced(session, swarm_id=colony_id)
        if stamped is not None:
            synced_ids.append(str(stamped[0]))
        if len(synced_ids) >= cap:
            break

    message = (
        f"Recorded global sync for {len(synced_ids)} colony/colonies."
        if synced_ids
        else "No colonies due for sync."
    )
    _logger.info(
        "sub_swarm_fleet.batch_sync",
        agent_id="sub_swarm_fleet",
        swarm_id="fleet",
        synced_count=len(synced_ids),
    )
    return SubSwarmFleetSyncDueOut(
        ok=True,
        synced_count=len(synced_ids),
        synced_colony_ids=synced_ids,
        message=message,
    )


__all__ = [
    "MAX_FLEET_COLONIES",
    "SubSwarmFleetColonyOut",
    "SubSwarmFleetSnapshotOut",
    "SubSwarmFleetSyncDueOut",
    "compose_sub_swarm_fleet_snapshot",
    "sync_due_sub_swarm_fleet",
]
