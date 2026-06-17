"""REV4–REV8 — Factory Launch widget for Mission Home (Gumroad sellable harness funnel)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger(__name__)


def _smtp_ready() -> bool:
    """True when SMTP credentials exist for REV1 buyer onboarding email."""

    return bool((settings.smtp_user or "").strip() and (settings.smtp_pass or "").strip())


def _purchase_webhook_ready() -> bool:
    """True when Gumroad sale ping ingress is configured."""

    return bool(settings.commerce_webhooks_enabled and (settings.gumroad_webhook_secret or "").strip())


def _post_purchase_onboarding_ready() -> bool:
    """True when REV1 post-purchase onboarding can send email."""

    return bool(settings.gumroad_post_purchase_onboarding_enabled and _smtp_ready())


def _gumroad_webhook_url_template() -> str:
    """Operator-facing Gumroad ping URL pattern (secret placeholder)."""

    domain = (settings.domain or "queenswarm.love").strip()
    return f"https://{domain}/api/v1/commerce/webhooks/gumroad/<GUMROAD_WEBHOOK_SECRET>"


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
    prepare_available: bool = False
    gumroad_auto_draft_available: bool = False
    pending_gumroad_draft_count: int = 0
    pending_gumroad_publish_count: int = 0
    gumroad_auto_publish_available: bool = False
    published_gumroad_count: int = 0
    purchase_webhook_ready: bool = False
    post_purchase_onboarding_ready: bool = False
    revenue_loop_ready: bool = False
    revenue_smoke_available: bool = False
    catalog_href: str = "/skills"
    operator_hint: str = ""
    factory_href: str = "/apps-tools/skill-factory"
    launch_href: str = "/apps-tools/skill-factory?section=launch#launch"
    top_launch_titles: list[str] = Field(default_factory=list)


class FactoryLaunchGumroadDraftRowOut(BaseModel):
    """One Gumroad draft attempt in a Mission Home batch."""

    model_config = ConfigDict(extra="ignore")

    skill_id: str
    slug: str
    title: str
    ok: bool
    product_url: str | None = None
    product_id: str | None = None
    error: str | None = None


class FactoryLaunchGumroadDraftOut(BaseModel):
    """Batch Gumroad draft result for Mission Home widget."""

    model_config = ConfigDict(extra="ignore")

    ok: bool = False
    drafted_count: int = 0
    skipped_count: int = 0
    drafts: list[FactoryLaunchGumroadDraftRowOut] = Field(default_factory=list)
    message: str = ""


class FactoryLaunchGumroadPublishRowOut(BaseModel):
    """One Gumroad publish attempt in a Mission Home batch."""

    model_config = ConfigDict(extra="ignore")

    skill_id: str
    slug: str
    title: str
    ok: bool
    product_url: str | None = None
    product_id: str | None = None
    published: bool | None = None
    error: str | None = None


class FactoryLaunchGumroadPublishOut(BaseModel):
    """Batch Gumroad publish result for Mission Home widget."""

    model_config = ConfigDict(extra="ignore")

    ok: bool = False
    published_count: int = 0
    skipped_count: int = 0
    publishes: list[FactoryLaunchGumroadPublishRowOut] = Field(default_factory=list)
    message: str = ""


class FactoryLaunchRevenueSmokeCheckOut(BaseModel):
    """One checklist row for buyer revenue loop verification."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    ok: bool
    detail: str


class FactoryLaunchRevenueSmokeOut(BaseModel):
    """Dry-run buyer loop readiness — publish → webhook → onboarding."""

    model_config = ConfigDict(extra="ignore")

    ok: bool = False
    checks: list[FactoryLaunchRevenueSmokeCheckOut] = Field(default_factory=list)
    message: str = ""
    gumroad_webhook_url_template: str = ""
    catalog_href: str = "/skills"


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
    pending_gumroad_draft_count = sum(1 for row in launch_queue if not row.gumroad_product_id)
    pending_gumroad_publish_count = sum(
        1 for row in launch_queue if row.gumroad_product_id and row.gumroad_published is not True
    )
    gumroad_auto_draft_available = bool(snapshot.gumroad_listing_ready and pending_gumroad_draft_count > 0)
    gumroad_auto_publish_available = bool(snapshot.gumroad_publish_ready and pending_gumroad_publish_count > 0)
    published_gumroad_count = sum(1 for row in launch_queue if row.gumroad_published is True)
    purchase_webhook_ready = _purchase_webhook_ready()
    post_purchase_onboarding_ready = _post_purchase_onboarding_ready()
    revenue_loop_ready = bool(
        published_gumroad_count > 0 and purchase_webhook_ready and post_purchase_onboarding_ready
    )
    revenue_smoke_available = bool(published_gumroad_count > 0 or (launch_queue and sellable > 0))

    from app.application.services.purchase_onboarding import marketing_public_origin

    catalog_href = f"{marketing_public_origin()}/skills"

    if sellable == 0:
        hint = "No sellable harness yet — run Factory research → build → approve forge."
    elif not launch_queue:
        hint = f"{sellable} sellable skill(s) — open Launch tab to queue Gumroad export."
    elif not gumroad_ready:
        hint = f"{len(launch_queue)} in launch queue — set Gumroad token or manual upload path."
    elif pending_gumroad_draft_count > 0:
        hint = (
            f"{pending_gumroad_draft_count} harness pack(s) ready — "
            "create Gumroad drafts or use Prepare batch for manual upload."
        )
    elif pending_gumroad_publish_count > 0:
        hint = (
            f"{pending_gumroad_publish_count} Gumroad draft(s) ready — "
            "publish live listings when copy and assets are verified."
        )
    elif published_gumroad_count > 0 and not revenue_loop_ready:
        hint = (
            f"{published_gumroad_count} live listing(s) — wire Gumroad ping webhook + SMTP "
            "for post-purchase buyer onboarding."
        )
    elif revenue_loop_ready:
        hint = (
            f"Revenue loop closed — {published_gumroad_count} live listing(s), "
            "webhook + onboarding ready."
        )
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
        prepare_available=sellable > 0,
        gumroad_auto_draft_available=gumroad_auto_draft_available,
        pending_gumroad_draft_count=pending_gumroad_draft_count,
        pending_gumroad_publish_count=pending_gumroad_publish_count,
        gumroad_auto_publish_available=gumroad_auto_publish_available,
        published_gumroad_count=published_gumroad_count,
        purchase_webhook_ready=purchase_webhook_ready,
        post_purchase_onboarding_ready=post_purchase_onboarding_ready,
        revenue_loop_ready=revenue_loop_ready,
        revenue_smoke_available=revenue_smoke_available,
        catalog_href=catalog_href,
        operator_hint=hint,
        top_launch_titles=titles,
    )


async def prepare_factory_launch_batch_from_widget(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    limit: int = 3,
) -> dict[str, object]:
    """Export top sellable skills for Gumroad upload (Mission Home one-click)."""

    if not settings.factory_launch_mission_home_enabled or not settings.skill_factory_enabled:
        return {"ok": False, "error": "factory_launch_disabled", "message": "Factory launch widget disabled."}

    from app.application.services.skill_factory_launch import LaunchPrepareOut, prepare_launch_batch

    capped = max(1, min(limit, 12))
    result: LaunchPrepareOut = await prepare_launch_batch(session, tenant_id=tenant_id, limit=capped)
    _logger.info(
        "factory_launch_widget.prepare_batch",
        agent_id="factory_launch_widget",
        swarm_id=str(tenant_id),
        exported_count=result.exported_count,
        sellable_recommended=result.sellable_recommended,
    )
    payload = result.model_dump(mode="json")
    payload["ok"] = result.exported_count > 0
    return payload


async def draft_factory_launch_gumroad_from_widget(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    limit: int = 3,
) -> dict[str, object]:
    """Create Gumroad draft listings for launch-queue skills (Mission Home one-click)."""

    if not settings.factory_launch_mission_home_enabled or not settings.skill_factory_enabled:
        return FactoryLaunchGumroadDraftOut(
            message="Factory launch widget disabled.",
        ).model_dump(mode="json") | {"ok": False, "error": "factory_launch_disabled"}

    if not settings.skill_factory_gumroad_listing_enabled:
        return FactoryLaunchGumroadDraftOut(
            message="Gumroad listing is disabled — enable skill_factory_gumroad_listing_enabled.",
        ).model_dump(mode="json") | {"ok": False, "error": "gumroad_listing_disabled"}

    from app.application.services.skill_factory_gumroad_listing import (
        create_gumroad_draft_from_skill,
        gumroad_listing_ready,
    )
    from app.application.services.skill_factory_service import compose_skill_factory_snapshot

    if not await gumroad_listing_ready(session):
        return FactoryLaunchGumroadDraftOut(
            message="Gumroad token not configured — add connector or SKILL_FACTORY_GUMROAD_ACCESS_TOKEN.",
        ).model_dump(mode="json") | {"ok": False, "error": "gumroad_not_configured"}

    snapshot = await compose_skill_factory_snapshot(session, tenant_id=tenant_id)
    launch_queue = list(snapshot.launch_queue or [])
    pending = [row for row in launch_queue if not row.gumroad_product_id]
    if not pending:
        return FactoryLaunchGumroadDraftOut(
            message="Launch queue skills already have Gumroad product IDs.",
        ).model_dump(mode="json") | {"ok": False, "error": "no_pending_drafts"}

    capped = pending[: max(1, min(limit, 12))]
    draft_rows: list[FactoryLaunchGumroadDraftRowOut] = []
    drafted_count = 0
    for skill in capped:
        skill_uuid = uuid.UUID(str(skill.id))
        result = await create_gumroad_draft_from_skill(
            session,
            tenant_id=tenant_id,
            skill_id=skill_uuid,
        )
        ok = bool(result.get("ok"))
        if ok:
            drafted_count += 1
        draft_rows.append(
            FactoryLaunchGumroadDraftRowOut(
                skill_id=str(skill.id),
                slug=skill.slug,
                title=skill.title,
                ok=ok,
                product_url=str(result.get("product_url") or "") or None,
                product_id=str(result.get("product_id") or "") or None,
                error=None if ok else str(result.get("error") or result.get("message") or "gumroad_draft_failed"),
            ),
        )

    skipped_count = len(capped) - drafted_count
    message = (
        f"Created {drafted_count} Gumroad draft(s)."
        if drafted_count
        else "No Gumroad drafts created — check token and LISTING.md content."
    )
    _logger.info(
        "factory_launch_widget.gumroad_draft_batch",
        agent_id="factory_launch_widget",
        swarm_id=str(tenant_id),
        drafted_count=drafted_count,
        skipped_count=skipped_count,
    )
    out = FactoryLaunchGumroadDraftOut(
        ok=drafted_count > 0,
        drafted_count=drafted_count,
        skipped_count=skipped_count,
        drafts=draft_rows,
        message=message,
    )
    return out.model_dump(mode="json")


async def publish_factory_launch_gumroad_from_widget(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    limit: int = 3,
) -> dict[str, object]:
    """Publish Gumroad draft listings for launch-queue skills (Mission Home one-click)."""

    if not settings.factory_launch_mission_home_enabled or not settings.skill_factory_enabled:
        return FactoryLaunchGumroadPublishOut(
            message="Factory launch widget disabled.",
        ).model_dump(mode="json") | {"ok": False, "error": "factory_launch_disabled"}

    if not settings.skill_factory_gumroad_publish_enabled:
        return FactoryLaunchGumroadPublishOut(
            message="Gumroad publish is disabled — enable skill_factory_gumroad_publish_enabled.",
        ).model_dump(mode="json") | {"ok": False, "error": "gumroad_publish_disabled"}

    from app.application.services.skill_factory_gumroad_listing import (
        gumroad_publish_ready,
        publish_gumroad_listing_for_skill,
    )
    from app.application.services.skill_factory_service import compose_skill_factory_snapshot

    if not await gumroad_publish_ready(session):
        return FactoryLaunchGumroadPublishOut(
            message="Gumroad publish not ready — configure token and listing flags.",
        ).model_dump(mode="json") | {"ok": False, "error": "gumroad_not_configured"}

    snapshot = await compose_skill_factory_snapshot(session, tenant_id=tenant_id)
    launch_queue = list(snapshot.launch_queue or [])
    pending = [
        row for row in launch_queue if row.gumroad_product_id and row.gumroad_published is not True
    ]
    if not pending:
        return FactoryLaunchGumroadPublishOut(
            message="No unpublished Gumroad drafts in launch queue.",
        ).model_dump(mode="json") | {"ok": False, "error": "no_pending_publish"}

    capped = pending[: max(1, min(limit, 12))]
    publish_rows: list[FactoryLaunchGumroadPublishRowOut] = []
    published_count = 0
    for skill in capped:
        skill_uuid = uuid.UUID(str(skill.id))
        result = await publish_gumroad_listing_for_skill(
            session,
            tenant_id=tenant_id,
            skill_id=skill_uuid,
            product_id=str(skill.gumroad_product_id or ""),
        )
        ok = bool(result.get("ok"))
        if ok:
            published_count += 1
        publish_rows.append(
            FactoryLaunchGumroadPublishRowOut(
                skill_id=str(skill.id),
                slug=skill.slug,
                title=skill.title,
                ok=ok,
                product_url=str(result.get("product_url") or result.get("short_url") or "") or None,
                product_id=str(result.get("product_id") or skill.gumroad_product_id or "") or None,
                published=bool(result.get("published")) if ok else None,
                error=None if ok else str(result.get("error") or result.get("message") or "gumroad_publish_failed"),
            ),
        )

    skipped_count = len(capped) - published_count
    message = (
        f"Published {published_count} Gumroad listing(s)."
        if published_count
        else "No Gumroad listings published — verify drafts in Gumroad UI first."
    )
    _logger.info(
        "factory_launch_widget.gumroad_publish_batch",
        agent_id="factory_launch_widget",
        swarm_id=str(tenant_id),
        published_count=published_count,
        skipped_count=skipped_count,
    )
    out = FactoryLaunchGumroadPublishOut(
        ok=published_count > 0,
        published_count=published_count,
        skipped_count=skipped_count,
        publishes=publish_rows,
        message=message,
    )
    return out.model_dump(mode="json")


async def run_factory_launch_revenue_smoke(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> dict[str, object]:
    """Dry-run buyer loop checklist: live listing → Gumroad ping → REV1 email."""

    if not settings.factory_launch_mission_home_enabled or not settings.skill_factory_enabled:
        return FactoryLaunchRevenueSmokeOut(
            message="Factory launch widget disabled.",
        ).model_dump(mode="json") | {"ok": False, "error": "factory_launch_disabled"}

    snapshot = await compose_factory_launch_widget_snapshot(session, tenant_id=tenant_id)
    from app.application.services.purchase_onboarding import marketing_public_origin

    catalog_href = f"{marketing_public_origin()}/skills"
    checks = [
        FactoryLaunchRevenueSmokeCheckOut(
            id="sellable_harness",
            label="Sellable harness in library",
            ok=snapshot.sellable_count > 0,
            detail=f"{snapshot.sellable_count} sellable skill(s)",
        ),
        FactoryLaunchRevenueSmokeCheckOut(
            id="live_gumroad_listing",
            label="Live Gumroad listing",
            ok=snapshot.published_gumroad_count > 0,
            detail=f"{snapshot.published_gumroad_count} published in launch queue",
        ),
        FactoryLaunchRevenueSmokeCheckOut(
            id="gumroad_webhook",
            label="Gumroad sale ping webhook",
            ok=snapshot.purchase_webhook_ready,
            detail=(
                "COMMERCE_WEBHOOKS_ENABLED + GUMROAD_WEBHOOK_SECRET configured"
                if snapshot.purchase_webhook_ready
                else "Set webhook secret and enable commerce webhooks"
            ),
        ),
        FactoryLaunchRevenueSmokeCheckOut(
            id="post_purchase_onboarding",
            label="Post-purchase onboarding email",
            ok=snapshot.post_purchase_onboarding_ready,
            detail=(
                "REV1 onboarding + SMTP ready"
                if snapshot.post_purchase_onboarding_ready
                else "Enable GUMROAD_POST_PURCHASE_ONBOARDING + SMTP credentials"
            ),
        ),
        FactoryLaunchRevenueSmokeCheckOut(
            id="marketing_catalog",
            label="Public skills catalog",
            ok=bool((settings.marketing_public_origin or "").strip()),
            detail=f"Buyer catalog at {catalog_href}",
        ),
    ]
    loop_ok = all(row.ok for row in checks if row.id != "sellable_harness")
    message = (
        "Revenue loop verified — buyer ping will unlock + send onboarding."
        if loop_ok and snapshot.published_gumroad_count > 0
        else "Revenue loop incomplete — fix failing checks before first sale."
    )
    _logger.info(
        "factory_launch_widget.revenue_smoke",
        agent_id="factory_launch_widget",
        swarm_id=str(tenant_id),
        ok=loop_ok,
        published_count=snapshot.published_gumroad_count,
    )
    out = FactoryLaunchRevenueSmokeOut(
        ok=loop_ok and snapshot.published_gumroad_count > 0,
        checks=checks,
        message=message,
        gumroad_webhook_url_template=_gumroad_webhook_url_template(),
        catalog_href=catalog_href,
    )
    return out.model_dump(mode="json")


__all__ = [
    "FactoryLaunchGumroadDraftOut",
    "FactoryLaunchGumroadDraftRowOut",
    "FactoryLaunchGumroadPublishOut",
    "FactoryLaunchGumroadPublishRowOut",
    "FactoryLaunchRevenueSmokeCheckOut",
    "FactoryLaunchRevenueSmokeOut",
    "FactoryLaunchWidgetOut",
    "compose_factory_launch_widget_snapshot",
    "draft_factory_launch_gumroad_from_widget",
    "prepare_factory_launch_batch_from_widget",
    "publish_factory_launch_gumroad_from_widget",
    "run_factory_launch_revenue_smoke",
]
