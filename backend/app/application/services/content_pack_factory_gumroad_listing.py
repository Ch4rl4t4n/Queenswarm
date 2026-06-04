"""Create Gumroad draft listings from Content Pack Factory export bundles."""

from __future__ import annotations

from datetime import UTC, datetime

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.content_pack_factory_export import build_content_pack_export_bundle
from app.application.services.content_pack_factory_listing import (
    build_content_pack_listing_md,
    listing_context_from_pack_and_opportunity,
)
from app.application.services.skill_factory_gumroad_listing import (
    _extract_product_url,
    _gumroad_enable_product,
    _gumroad_token_for_session,
    _markdown_to_gumroad_html,
    gumroad_listing_ready,
    gumroad_publish_ready,
)
from app.common.schemas.skill_export import SkillExportFile
from app.core.config import settings
from app.infrastructure.persistence.models.content_pack_opportunity import ContentPackOpportunityORM
from app.infrastructure.persistence.models.tenant_content_pack import TenantContentPackORM

logger = structlog.get_logger(__name__)

_GUMROAD_API = "https://api.gumroad.com/v2/products"


def read_gumroad_listing_ref(opportunity: ContentPackOpportunityORM | None) -> dict[str, Any] | None:
    """Return gumroad_listing ref from content pack opportunity if present."""

    if opportunity is None:
        return None
    for item in list(opportunity.source_refs or []):
        if isinstance(item, dict) and str(item.get("kind") or "") == "gumroad_listing":
            return item
    return None


def persist_gumroad_listing_ref(
    opportunity: ContentPackOpportunityORM,
    *,
    product_id: str,
    product_url: str | None,
    published: bool = False,
) -> None:
    """Store Gumroad product linkage on content pack opportunity source_refs."""

    refs: list[Any] = list(opportunity.source_refs or [])
    refs = [item for item in refs if not (isinstance(item, dict) and item.get("kind") == "gumroad_listing")]
    refs.append(
        {
            "kind": "gumroad_listing",
            "product_id": product_id,
            "product_url": product_url,
            "published": published,
        },
    )
    opportunity.source_refs = refs[:24]


async def create_gumroad_draft_from_content_pack(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    pack_id: uuid.UUID,
) -> dict[str, Any]:
    """Create a Gumroad draft product from content pack LISTING.md."""

    if not settings.skill_factory_gumroad_listing_enabled:
        return {"ok": False, "error": "gumroad_listing_disabled"}

    token = await _gumroad_token_for_session(session)
    if not token:
        return {"ok": False, "error": "gumroad_not_configured"}

    row = await session.get(TenantContentPackORM, pack_id)
    if row is None or row.tenant_id != tenant_id:
        return {"ok": False, "error": "pack_not_found"}

    opportunity = await session.scalar(
        select(ContentPackOpportunityORM).where(
            ContentPackOpportunityORM.tenant_id == tenant_id,
            ContentPackOpportunityORM.tenant_content_pack_id == pack_id,
        ),
    )
    bundle = build_content_pack_export_bundle(row, opportunity=opportunity)
    listing_ctx = listing_context_from_pack_and_opportunity(row, opportunity)
    listing_md = row.listing_markdown.strip() or build_content_pack_listing_md(
        pack=row,
        slug=row.slug,
        ctx=listing_ctx,
    )

    name = (listing_ctx.one_line_hook or row.title)[:100]
    price_cents = max(100, int(listing_ctx.price_cents or 1900))
    description_html = _markdown_to_gumroad_html(listing_md)
    tags_list = [str(t) for t in (row.keywords or [])[:8]] or ["content-pack", "social", "simulate-first"]

    fields: list[tuple[str, str]] = [
        ("access_token", token),
        ("name", name),
        ("price", str(price_cents)),
        ("native_type", "digital"),
        ("description", description_html),
        ("custom_summary", (listing_ctx.one_line_hook or row.description or name)[:240]),
        ("custom_permalink", row.slug[:60]),
    ]
    for tag in tags_list:
        fields.append(("tags[]", tag[:40]))

    timeout = httpx.Timeout(30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            rsp = await client.post(_GUMROAD_API, data=fields)
        except httpx.HTTPError as exc:
            logger.warning(
                "content_pack_factory.gumroad_create_failed",
                agent_id="content_pack_factory",
                swarm_id=str(tenant_id),
                error=exc.__class__.__name__,
            )
            return {"ok": False, "error": "gumroad_http_error", "message": exc.__class__.__name__}

    try:
        payload = rsp.json()
    except json.JSONDecodeError:
        payload = {}

    if rsp.status_code >= 400 or not payload.get("success"):
        message = str(payload.get("message") or payload.get("error") or rsp.text[:400])
        return {
            "ok": False,
            "error": "gumroad_api_error",
            "status": rsp.status_code,
            "message": message,
        }

    product_url = _extract_product_url(payload if isinstance(payload, dict) else {})
    from app.application.services.skill_factory_gumroad_assets import (
        _extract_product_id,
        enrich_gumroad_product_assets,
    )

    product_id = _extract_product_id(payload if isinstance(payload, dict) else {})
    if product_id and opportunity is not None:
        persist_gumroad_listing_ref(
            opportunity,
            product_id=product_id,
            product_url=product_url,
            published=False,
        )
        await session.flush()

    assets_result: dict[str, Any] = {}
    if product_id:
        skill_files = [SkillExportFile(path=f.path, content=f.content) for f in bundle.files]
        assets_result = await enrich_gumroad_product_assets(
            token=token,
            product_id=product_id,
            bundle_files=skill_files,
            cover_preview_url=None,
        )
        row.gumroad_exported_at = datetime.now(tz=UTC)
        await session.flush()

    logger.info(
        "content_pack_factory.gumroad_draft_created",
        agent_id="content_pack_factory",
        swarm_id=str(tenant_id),
        task_id=str(pack_id),
        product_url=(product_url or "")[:120],
    )
    return {
        "ok": True,
        "product_url": product_url,
        "product_id": product_id,
        "edit_url": "https://gumroad.com/products",
        "name": name,
        "price_cents": price_cents,
        "assets": assets_result,
    }


async def publish_gumroad_listing_for_content_pack(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    pack_id: uuid.UUID,
    product_id: str | None = None,
    create_if_missing: bool = False,
) -> dict[str, Any]:
    """Publish an existing Gumroad product linked to a content pack."""

    if not settings.skill_factory_gumroad_publish_enabled:
        return {"ok": False, "error": "gumroad_publish_disabled"}

    token = await _gumroad_token_for_session(session)
    if not token:
        return {"ok": False, "error": "gumroad_not_configured"}

    row = await session.get(TenantContentPackORM, pack_id)
    if row is None or row.tenant_id != tenant_id:
        return {"ok": False, "error": "pack_not_found"}

    opportunity = await session.scalar(
        select(ContentPackOpportunityORM).where(
            ContentPackOpportunityORM.tenant_id == tenant_id,
            ContentPackOpportunityORM.tenant_content_pack_id == pack_id,
        ),
    )
    listing_ref = read_gumroad_listing_ref(opportunity)
    resolved_id = (product_id or (listing_ref or {}).get("product_id") or "").strip()

    if not resolved_id and create_if_missing:
        draft = await create_gumroad_draft_from_content_pack(session, tenant_id=tenant_id, pack_id=pack_id)
        if not draft.get("ok"):
            return draft
        resolved_id = str(draft.get("product_id") or "").strip()
        listing_ref = read_gumroad_listing_ref(opportunity)

    if not resolved_id:
        return {"ok": False, "error": "gumroad_product_id_missing"}

    timeout = httpx.Timeout(30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        ok, payload, err = await _gumroad_enable_product(client, token=token, product_id=resolved_id)

    if not ok:
        return {
            "ok": False,
            "error": "gumroad_publish_failed",
            "message": str(payload.get("message") or err)[:300],
        }

    product = payload.get("product") if isinstance(payload.get("product"), dict) else {}
    product_url = _extract_product_url(payload) or str((listing_ref or {}).get("product_url") or "")

    if opportunity is not None:
        persist_gumroad_listing_ref(
            opportunity,
            product_id=resolved_id,
            product_url=product_url or None,
            published=True,
        )
        await session.flush()

    logger.info(
        "content_pack_factory.gumroad_published",
        agent_id="content_pack_factory",
        swarm_id=str(tenant_id),
        task_id=str(pack_id),
        product_id=resolved_id[:80],
    )
    return {
        "ok": True,
        "product_id": resolved_id,
        "product_url": product_url,
        "published": bool(product.get("published", True)),
        "short_url": str(product.get("short_url") or product_url or ""),
    }


__all__ = [
    "create_gumroad_draft_from_content_pack",
    "gumroad_listing_ready",
    "gumroad_publish_ready",
    "persist_gumroad_listing_ref",
    "publish_gumroad_listing_for_content_pack",
    "read_gumroad_listing_ref",
]
