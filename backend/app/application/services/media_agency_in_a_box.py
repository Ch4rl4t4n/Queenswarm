"""Faceless Media Agency in a Box — white-label publish lane snapshot (P2 #84 beta)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.enterprise_workspace import get_white_label_config
from app.application.services.publish_operator_onboarding import compose_publish_onboarding_snapshot
from app.application.services.publish_performance import build_publish_performance_snapshot
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant


class MediaAgencyClientLaneOut(BaseModel):
    """One client publish lane row."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    channel: str
    status: str
    detail: str


class MediaAgencyActionOut(BaseModel):
    """Operator action for agency lane."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    detail: str
    priority: str
    href: str | None = None


class MediaAgencySnapshotOut(BaseModel):
    """Agency in a box unified snapshot."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    brand_name: str = "Queenswarm"
    white_label_ready: bool = False
    hide_platform_branding: bool = False
    publish_prep_pct: int = 0
    live_posts: int = 0
    client_lanes: list[MediaAgencyClientLaneOut] = Field(default_factory=list)
    actions: list[MediaAgencyActionOut] = Field(default_factory=list)


def _default_client_lanes() -> list[MediaAgencyClientLaneOut]:
    return [
        MediaAgencyClientLaneOut(
            id="client-a",
            label="Client A",
            channel="instagram",
            status="pending",
            detail="Awaiting first simulate pack.",
        ),
        MediaAgencyClientLaneOut(
            id="client-b",
            label="Client B",
            channel="twitter",
            status="pending",
            detail="Awaiting OAuth or simulate.",
        ),
        MediaAgencyClientLaneOut(
            id="client-c",
            label="Client C",
            channel="tiktok",
            status="pending",
            detail="Template lane — assign in swarm routine.",
        ),
    ]


def _merge_stored_clients(tenant: Tenant | None) -> list[MediaAgencyClientLaneOut]:
    root = dict((tenant.operator_settings or {}).get("media_agency") or {}) if tenant is not None else {}
    stored = root.get("clients")
    if not isinstance(stored, list) or not stored:
        return _default_client_lanes()

    lanes: list[MediaAgencyClientLaneOut] = []
    for idx, row in enumerate(stored[:12]):
        if not isinstance(row, dict):
            continue
        lanes.append(
            MediaAgencyClientLaneOut(
                id=str(row.get("id") or f"client-{idx}"),
                label=str(row.get("label") or row.get("name") or f"Client {idx + 1}"),
                channel=str(row.get("channel") or "instagram"),
                status=str(row.get("status") or "pending"),
                detail=str(row.get("detail") or "Agency lane")[:240],
            ),
        )
    return lanes or _default_client_lanes()


async def compose_media_agency_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
) -> MediaAgencySnapshotOut:
    """Compose white-label + publish onboarding + client lane template."""

    if not settings.media_agency_in_a_box_enabled:
        return MediaAgencySnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
        )

    white_label = get_white_label_config(tenant) if tenant is not None else {}
    brand_name = str(white_label.get("brand_name") or "Queenswarm").strip() or "Queenswarm"
    hide_branding = bool(white_label.get("hide_platform_branding"))
    white_label_ready = bool(brand_name != "Queenswarm" or hide_branding or white_label.get("logo_url"))

    onboarding = await compose_publish_onboarding_snapshot(
        session,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
    )
    perf = build_publish_performance_snapshot(tenant, window_days=30)
    client_lanes = _merge_stored_clients(tenant)

    channel_stats = {row.channel: row for row in perf.by_channel}
    enriched_lanes: list[MediaAgencyClientLaneOut] = []
    for lane in client_lanes:
        ch = channel_stats.get(lane.channel)
        status = lane.status
        detail = lane.detail
        if ch is not None:
            if ch.live_ok > 0:
                status = "live_ok"
                detail = f"{ch.live_ok} live post(s) in window."
            elif ch.simulate_ok > 0:
                status = "simulate_ok"
                detail = f"{ch.simulate_ok} successful simulate(s)."
        enriched_lanes.append(lane.model_copy(update={"status": status, "detail": detail}))

    actions: list[MediaAgencyActionOut] = []
    if not white_label_ready:
        actions.append(
            MediaAgencyActionOut(
                id="white_label",
                label="Configure white-label brand",
                detail="Set brand name + logo before client-facing publish.",
                priority="high",
                href="/settings/enterprise",
            ),
        )
    if onboarding.progress_pct < 100:
        actions.append(
            MediaAgencyActionOut(
                id="publish_prep",
                label=f"Publish prep {onboarding.progress_pct}%",
                detail="Complete Brain Pack → OAuth → simulate before client live.",
                priority="high",
                href="/integrations?tab=studio#publish-queue",
            ),
        )
    if perf.live_posts == 0 and perf.totals.get("social_simulate", 0) >= 2:
        actions.append(
            MediaAgencyActionOut(
                id="first_client_live",
                label="Ready for first client live post",
                detail="Simulate history looks good — human approve live lane.",
                priority="medium",
                href="/integrations?tab=studio",
            ),
        )

    return MediaAgencySnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        brand_name=brand_name,
        white_label_ready=white_label_ready,
        hide_platform_branding=hide_branding,
        publish_prep_pct=onboarding.progress_pct,
        live_posts=perf.live_posts,
        client_lanes=enriched_lanes[:12],
        actions=actions[:6],
    )


__all__ = ["MediaAgencySnapshotOut", "compose_media_agency_snapshot"]
