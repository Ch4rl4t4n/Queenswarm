"""Publish lane operator onboarding — progress snapshot for solo operator."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.curated_memory_service import CuratedMemoryService
from app.application.services.publish_audit import build_publish_audit_snapshot
from app.application.services.solo_operator_trio import get_solo_trio_status
from app.application.services.social_publish import (
    SOCIAL_OAUTH_CHANNEL_IDS,
    build_social_publish_snapshot,
)
from app.application.services.social_publish_trusted_auto import build_trusted_auto_policy
from app.core.config import settings
from app.domain.memory.curated import CuratedFileKind
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService
from app.infrastructure.persistence.models.tenant import Tenant

OnboardingStepStatus = Literal["done", "ready", "pending", "blocked"]


class PublishOnboardingStepOut(BaseModel):
    """One checklist row for publish lane setup."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    status: OnboardingStepStatus
    detail: str
    link: str | None = None


class PublishOnboardingSnapshotOut(BaseModel):
    """Single snapshot for Settings harness publish onboarding panel."""

    model_config = ConfigDict(extra="ignore")

    generated_at: datetime
    progress_pct: int = Field(ge=0, le=100)
    steps: list[PublishOnboardingStepOut] = Field(default_factory=list)
    links: dict[str, str] = Field(default_factory=dict)
    flags: dict[str, bool] = Field(default_factory=dict)


def _brain_pack_filled_count(bundle: dict[CuratedFileKind, str]) -> int:
    from app.application.services.brain_pack_starters import starter_kinds

    return sum(1 for kind in starter_kinds() if (bundle.get(kind) or "").strip())


def _audit_has_kind(tenant: Tenant | None, kind: str) -> bool:
    audit = build_publish_audit_snapshot(tenant, limit=40)
    return any(entry.kind == kind and entry.ok is not False for entry in audit.entries)


def _has_simulate_audit(tenant: Tenant | None) -> bool:
    return _audit_has_kind(tenant, "social_simulate")


def _has_live_audit(tenant: Tenant | None) -> bool:
    return _audit_has_kind(tenant, "social_live") or _audit_has_kind(tenant, "social_live_auto")


def _ready_items_with_media(social) -> int:
    total = 0
    for item in social.ready_items or []:
        if getattr(item, "media_url", None):
            total += 1
    return total


async def compose_publish_onboarding_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None = None,
) -> PublishOnboardingSnapshotOut:
    """Build operator checklist for Brain Pack → OAuth → simulate → live publish."""

    memory = CuratedMemoryService(db=session)
    bundle = await memory.get_bundle(tenant_id)
    filled = _brain_pack_filled_count(bundle)
    instructions_ok = bool((bundle.get(CuratedFileKind.INSTRUCTIONS) or "").strip())
    soul_ok = bool((bundle.get(CuratedFileKind.SOUL) or "").strip())
    brain_done = instructions_ok and soul_ok and filled >= 3

    trio = await get_solo_trio_status(session, tenant_id=tenant_id)
    lanes_bound = int(trio.get("lanes_bound") or 0)
    lanes_total = int(trio.get("lanes_total") or 3)
    trio_bound_done = lanes_bound >= lanes_total
    trio_ran = any(
        lane.get("last_session_status") in {"completed", "done", "success"}
        for lane in trio.get("lanes") or []
        if isinstance(lane, dict)
    )

    social = await build_social_publish_snapshot(
        session,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
        limit=5,
    )
    oauth_channels = [
        row
        for row in social.channels
        if row.channel in SOCIAL_OAUTH_CHANNEL_IDS and row.credentials_ok and row.active
    ]
    oauth_done = len(oauth_channels) > 0
    simulate_done = _has_simulate_audit(tenant)
    live_flag = bool(settings.social_publish_live_enabled)
    approved_ready = len(social.ready_items) > 0
    media_ready_count = _ready_items_with_media(social)
    media_done = media_ready_count > 0

    venice_row = await DynamicConnectorService().fetch_by_slug(session, slug="venice_mcp")
    venice_present = venice_row is not None
    venice_active = bool(venice_row is not None and venice_row.is_active)
    venice_status: OnboardingStepStatus = (
        "done" if venice_active else ("ready" if venice_present else "pending")
    )

    trusted_policy = build_trusted_auto_policy(tenant)
    trusted_auto_done = bool(
        trusted_policy.tenant_enabled
        and settings.social_publish_trusted_auto_enabled
        and any(ch.auto_eligible for ch in trusted_policy.channels),
    )
    live_post_done = _has_live_audit(tenant)

    steps: list[PublishOnboardingStepOut] = [
        PublishOnboardingStepOut(
            id="brain_pack",
            label="Brain Pack loaded",
            status="done" if brain_done else "pending",
            detail=f"{filled}/5 curated slots filled — use Load starter pack in Knowledge.",
            link="/knowledge?tab=memory#brain-pack",
        ),
        PublishOnboardingStepOut(
            id="trio_bound",
            label="My 3 Bees bound",
            status="done" if trio_bound_done else "pending",
            detail=f"{lanes_bound}/{lanes_total} lanes bound to routines.",
            link="/settings/harness#solo-trio",
        ),
        PublishOnboardingStepOut(
            id="trio_run",
            label="Trio cycle run once",
            status="done" if trio_ran else ("ready" if trio_bound_done else "pending"),
            detail="Run today's cycle after binding all three lanes.",
            link="/settings/harness#solo-trio",
        ),
        PublishOnboardingStepOut(
            id="publish_media",
            label="Publish pack with media",
            status="done" if media_done else ("ready" if approved_ready else "pending"),
            detail=(
                f"{media_ready_count} approved pack(s) include media_url (preview in Publish Queue)."
                if media_done
                else "Add media_url via Publish Pack Bee + Venice, or enable PUBLISH_PACK_VENICE_MEDIA_HOOK."
            ),
            link="/integrations?tab=studio#publish-queue",
        ),
        PublishOnboardingStepOut(
            id="venice_connector",
            label="Venice MCP installed (media gen)",
            status=venice_status,
            detail=(
                "venice_mcp active — Publish Pack Bee can call image_generate."
                if venice_active
                else (
                    "venice_mcp installed — add Bearer token in Hub → Test connection to activate."
                    if venice_present
                    else "Install Venice from Marketplace for automated pack images."
                )
            ),
            link="/integrations?tab=marketplace",
        ),
        PublishOnboardingStepOut(
            id="social_oauth",
            label="Social OAuth connected",
            status="done" if oauth_done else "pending",
            detail=(
                f"{len(oauth_channels)} social channel(s) ready (Instagram/X/TikTok)."
                if oauth_done
                else "Install a social connector (Instagram/X/TikTok) + Connector Hub OAuth."
            ),
            link="/integrations?tab=marketplace",
        ),
        PublishOnboardingStepOut(
            id="publish_approved",
            label="Publish Queue approved pack",
            status="done" if approved_ready else ("ready" if oauth_done else "pending"),
            detail=(
                f"{len(social.ready_items)} approved pack(s) ready for Social publish."
                if approved_ready
                else "Approve at least one verified publish pack."
            ),
            link="/integrations?tab=studio#publish-queue",
        ),
        PublishOnboardingStepOut(
            id="social_simulate",
            label="Social publish Simulate OK",
            status="done" if simulate_done else ("ready" if approved_ready else "pending"),
            detail="Run Simulate in Execution Studio before any live API call.",
            link="/integrations?tab=studio#social-publish",
        ),
        PublishOnboardingStepOut(
            id="live_enabled",
            label="Live publish enabled",
            status="done" if live_flag else ("ready" if simulate_done else "blocked"),
            detail=(
                "SOCIAL_PUBLISH_LIVE_ENABLED=true — redeploy after OAuth + simulate."
                if not live_flag
                else "Live API enabled — use Live button after operator confirm."
            ),
            link="/integrations?tab=studio#social-publish",
        ),
        PublishOnboardingStepOut(
            id="first_live_post",
            label="First live post published",
            status="done" if live_post_done else ("ready" if live_flag and simulate_done else "blocked"),
            detail=(
                "Audit shows successful social_live — onboarding complete."
                if live_post_done
                else "Confirm Live on one approved pack after OAuth."
            ),
            link="/integrations?tab=studio#social-publish",
        ),
        PublishOnboardingStepOut(
            id="trusted_auto",
            label="Trusted auto-live ready",
            status="done" if trusted_auto_done else ("ready" if live_post_done else "pending"),
            detail=(
                "At least one channel auto-eligible — scheduled tick can live-publish."
                if trusted_auto_done
                else "Enable trusted auto after 5+ simulates per channel (Phase G)."
            ),
            link="/integrations?tab=studio#social-publish",
        ),
    ]

    done_count = sum(1 for step in steps if step.status == "done")
    progress = int(round(100 * done_count / max(len(steps), 1)))

    return PublishOnboardingSnapshotOut(
        generated_at=datetime.now(tz=UTC),
        progress_pct=progress,
        steps=steps,
        links={
            "brain_pack": "/knowledge?tab=memory#brain-pack",
            "execution_studio": "/integrations?tab=studio",
            "oauth_guide": "docs/OPERATOR_SOCIAL_OAUTH_SETUP.md",
            "first_live_post": "docs/OPERATOR_FIRST_LIVE_POST.md",
            "publish_lane_manual": "docs/OPERATOR_PUBLISH_LANE_MANUAL.md",
            **social.links,
        },
        flags={
            "brain_pack_done": brain_done,
            "trio_bound_done": trio_bound_done,
            "trio_ran": trio_ran,
            "publish_media_done": media_done,
            "venice_installed": venice_present,
            "venice_active": venice_active,
            "social_oauth_done": oauth_done,
            "simulate_done": simulate_done,
            "live_enabled": live_flag,
            "live_post_done": live_post_done,
            "trusted_auto_done": trusted_auto_done,
            "social_publish_enabled": bool(settings.social_publish_enabled),
        },
    )


__all__ = [
    "PublishOnboardingSnapshotOut",
    "PublishOnboardingStepOut",
    "compose_publish_onboarding_snapshot",
]
