"""Create Gumroad draft listings from Skill Factory export bundles."""

from __future__ import annotations

import html
import json
import re
import uuid
from typing import Any

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.skill_export import build_export_bundle_from_tenant_skill
from app.application.services.skill_factory_listing import (
    build_factory_listing_md,
    listing_context_from_skill_and_opportunity,
)
from app.core.config import settings
from app.infrastructure.persistence.models.skill_opportunity import SkillOpportunityORM
from app.infrastructure.persistence.models.tenant_skill import TenantSkillORM

logger = structlog.get_logger(__name__)

_GUMROAD_SLUG = "gumroad_rest"
_GUMROAD_API = "https://api.gumroad.com/v2/products"
_HEADING_RE = re.compile(r"^#{1,6}\s+(.+)$", re.MULTILINE)


def _resolve_gumroad_token(secrets: dict[str, Any]) -> str:
    """Read bearer/access token from connector secrets or settings."""

    for key in ("bearer_token", "access_token", "api_key"):
        value = str(secrets.get(key) or "").strip()
        if value:
            return value
    return settings.skill_factory_gumroad_access_token.strip()


async def gumroad_listing_ready(session: AsyncSession) -> bool:
    """True when Gumroad listing is enabled and credentials exist."""

    if not settings.skill_factory_gumroad_listing_enabled:
        return False
    from app.infrastructure.connectors.dynamic.service import DynamicConnectorService

    row = await DynamicConnectorService().fetch_by_slug(session, slug=_GUMROAD_SLUG)
    if row is not None and row.is_active:
        svc = DynamicConnectorService()
        secrets = svc._secrets_dict(row)  # noqa: SLF001
        if _resolve_gumroad_token(secrets):
            return True
    return bool(settings.skill_factory_gumroad_access_token.strip())


def _markdown_to_gumroad_html(markdown: str) -> str:
    """Minimal Markdown → HTML for Gumroad product description."""

    chunks: list[str] = []
    for block in markdown.split("\n\n"):
        text = block.strip()
        if not text:
            continue
        if text.startswith("```"):
            chunks.append(f"<pre>{html.escape(text)}</pre>")
            continue
        heading = _HEADING_RE.match(text)
        if heading:
            chunks.append(f"<h3>{html.escape(heading.group(1).strip())}</h3>")
            continue
        if text.startswith("- [ ]") or text.startswith("- [x]"):
            items = []
            for line in text.splitlines():
                line = line.strip()
                if not line.startswith("- "):
                    continue
                items.append(f"<li>{html.escape(line[2:].strip())}</li>")
            if items:
                chunks.append("<ul>" + "".join(items) + "</ul>")
            continue
        if text.startswith("- "):
            items = [f"<li>{html.escape(line[2:].strip())}</li>" for line in text.splitlines() if line.strip().startswith("- ")]
            if items:
                chunks.append("<ul>" + "".join(items) + "</ul>")
            continue
        chunks.append(f"<p>{html.escape(text).replace(chr(10), '<br>')}</p>")
    return "\n".join(chunks)[:65_000]


def _extract_product_url(payload: dict[str, Any]) -> str | None:
    """Parse Gumroad create-product response."""

    product = payload.get("product")
    if isinstance(product, dict):
        for key in ("short_url", "url", "permalink"):
            value = str(product.get(key) or "").strip()
            if value.startswith("http"):
                return value
    for key in ("short_url", "url"):
        value = str(payload.get(key) or "").strip()
        if value.startswith("http"):
            return value
    return None


async def _gumroad_token_for_session(session: AsyncSession) -> str | None:
    """Resolve active Gumroad token from connector or env."""

    from app.infrastructure.connectors.dynamic.service import DynamicConnectorService

    row = await DynamicConnectorService().fetch_by_slug(session, slug=_GUMROAD_SLUG)
    if row is not None and row.is_active:
        svc = DynamicConnectorService()
        secrets = svc._secrets_dict(row)  # noqa: SLF001
        token = _resolve_gumroad_token(secrets)
        if token:
            return token
    env_token = settings.skill_factory_gumroad_access_token.strip()
    return env_token or None


async def create_gumroad_draft_from_skill(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    skill_id: uuid.UUID,
) -> dict[str, Any]:
    """Create a Gumroad draft product from factory LISTING.md content."""

    if not settings.skill_factory_gumroad_listing_enabled:
        return {"ok": False, "error": "gumroad_listing_disabled"}

    token = await _gumroad_token_for_session(session)
    if not token:
        return {"ok": False, "error": "gumroad_not_configured"}

    row = await session.get(TenantSkillORM, skill_id)
    if row is None or row.tenant_id != tenant_id:
        return {"ok": False, "error": "skill_not_found"}

    opportunity = await session.scalar(
        select(SkillOpportunityORM).where(
            SkillOpportunityORM.tenant_id == tenant_id,
            SkillOpportunityORM.tenant_skill_id == skill_id,
        ),
    )
    bundle = build_export_bundle_from_tenant_skill(row, opportunity=opportunity)
    listing_ctx = listing_context_from_skill_and_opportunity(row, opportunity)
    listing_md = build_factory_listing_md(skill=row, slug=bundle.meta.slug, ctx=listing_ctx)

    name = (listing_ctx.one_line_hook or row.title)[:100]
    price_cents = max(100, int(listing_ctx.price_cents or settings.skill_export_premium_price_eur_cents))
    description_html = _markdown_to_gumroad_html(listing_md)
    tags_list = [str(t) for t in (row.keywords or [])[:8]] or ["agent-skill", "skill-factory", "cursor"]

    fields: list[tuple[str, str]] = [
        ("access_token", token),
        ("name", name),
        ("price", str(price_cents)),
        ("native_type", "digital"),
        ("description", description_html),
        ("custom_summary", (listing_ctx.one_line_hook or row.description or name)[:240]),
        ("custom_permalink", bundle.meta.slug[:60]),
    ]
    for tag in tags_list:
        fields.append(("tags[]", tag[:40]))

    timeout = httpx.Timeout(30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            rsp = await client.post(_GUMROAD_API, data=fields)
        except httpx.HTTPError as exc:
            logger.warning(
                "skill_factory.gumroad_create_failed",
                agent_id="skill_factory",
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
        logger.warning(
            "skill_factory.gumroad_create_rejected",
            agent_id="skill_factory",
            swarm_id=str(tenant_id),
            status=rsp.status_code,
            message=message[:200],
        )
        return {
            "ok": False,
            "error": "gumroad_api_error",
            "status": rsp.status_code,
            "message": message,
        }

    product_payload = payload if isinstance(payload, dict) else {}
    product_url = _extract_product_url(product_payload)
    assets_result: dict[str, Any] = {}
    from app.application.services.skill_factory_gumroad_assets import (
        _extract_product_id,
        enrich_gumroad_product_assets,
    )

    product_id = _extract_product_id(product_payload)
    if product_id:
        assets_result = await enrich_gumroad_product_assets(
            token=token,
            product_id=product_id,
            bundle_files=bundle.files,
            cover_preview_url=listing_ctx.video_preview_url,
        )

    logger.info(
        "skill_factory.gumroad_draft_created",
        agent_id="skill_factory",
        swarm_id=str(tenant_id),
        task_id=str(skill_id),
        product_url=(product_url or "")[:120],
        assets=assets_result,
    )
    return {
        "ok": True,
        "product_url": product_url,
        "product_id": product_id,
        "edit_url": "https://gumroad.com/products",
        "name": name,
        "price_cents": price_cents,
        "assets": assets_result,
        "gumroad_response_preview": json.dumps(payload)[:1500],
    }


__all__ = [
    "create_gumroad_draft_from_skill",
    "gumroad_listing_ready",
    "_markdown_to_gumroad_html",
]
