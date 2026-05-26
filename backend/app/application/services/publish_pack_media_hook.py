"""Optional Venice image_generate hook when publish pack lacks media_url."""

from __future__ import annotations

import json
import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.execution_studio import execute_studio_tool
from app.application.services.publish_media import is_safe_publish_media_url
from app.application.services.publish_pack import PublishPackArtifact
from app.core.config import settings
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService
from app.infrastructure.persistence.models.tenant import Tenant

logger = structlog.get_logger(__name__)

_VENICE_SLUG = "venice_mcp"
_IMAGE_CHANNELS = frozenset({"instagram", "facebook", "blog", "other"})


def _build_image_prompt(pack: PublishPackArtifact) -> str:
    tags = " ".join(f"#{tag}" for tag in pack.hashtags[:6])
    return (
        f"Social media post image for {pack.channel}: {pack.title}. "
        f"{pack.body[:400]}. {tags}. Professional, on-brand, no text overlay."
    ).strip()


def _extract_image_url_from_upstream(upstream: dict[str, Any]) -> str | None:
    """Best-effort parse HTTPS image URL from Venice image_generate result."""

    candidates: list[str] = []
    simulated = upstream.get("simulated_result")
    if isinstance(simulated, dict):
        for key in ("url", "image_url", "image"):
            val = simulated.get(key)
            if isinstance(val, str):
                candidates.append(val)
    raw = upstream.get("result")
    if raw:
        text = str(raw).strip()
        candidates.append(text)
        try:
            payload = json.loads(text) if text.startswith("{") else None
        except json.JSONDecodeError:
            payload = None
        if isinstance(payload, dict):
            for key in ("url", "image_url", "image"):
                val = payload.get(key)
                if isinstance(val, str):
                    candidates.append(val)
            images = payload.get("images") or payload.get("data")
            if isinstance(images, list):
                for item in images:
                    if isinstance(item, dict):
                        for key in ("url", "image_url"):
                            val = item.get(key)
                            if isinstance(val, str):
                                candidates.append(val)
                    elif isinstance(item, str):
                        candidates.append(item)
    for candidate in candidates:
        url = candidate.strip()
        if url.startswith("https://") and is_safe_publish_media_url(url):
            return url
        if "https://" in url:
            start = url.find("https://")
            fragment = url[start:].split()[0].strip("\"'`,}")
            if is_safe_publish_media_url(fragment):
                return fragment
    return None


async def _venice_connector_ready(session: AsyncSession, *, dashboard_user_id: uuid.UUID) -> bool:
    svc = DynamicConnectorService()
    row = await svc.fetch_by_slug(session, slug=_VENICE_SLUG)
    if row is None or not row.is_active:
        return False
    secrets = svc._secrets_dict(row)  # noqa: SLF001
    token = str(secrets.get("bearer_token") or secrets.get("api_key") or "").strip()
    return bool(token)


async def maybe_enrich_publish_pack_media(
    session: AsyncSession,
    *,
    pack: PublishPackArtifact,
    dashboard_user_id: uuid.UUID | None,
    tenant: Tenant | None,
) -> PublishPackArtifact:
    """When enabled, generate image via Venice if pack has no media_url."""

    if not settings.publish_pack_venice_media_hook_enabled:
        return pack
    if pack.media_url:
        return pack
    if pack.channel not in _IMAGE_CHANNELS:
        return pack
    if dashboard_user_id is None:
        return pack
    if not await _venice_connector_ready(session, dashboard_user_id=dashboard_user_id):
        logger.info(
            "publish_pack.venice_hook_skipped",
            agent_id="publish_pack",
            reason="venice_not_ready",
            channel=pack.channel,
        )
        return pack

    prompt = _build_image_prompt(pack)
    upstream = await execute_studio_tool(
        session,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
        connector_slug=_VENICE_SLUG,
        tool_name="image_generate",
        arguments={"prompt": prompt, "n": 1},
        mode="live",
        operator_confirmed=True,
    )
    if not upstream.get("ok"):
        logger.warning(
            "publish_pack.venice_hook_failed",
            agent_id="publish_pack",
            channel=pack.channel,
            error=str(upstream.get("error") or "")[:200],
        )
        return pack

    url = _extract_image_url_from_upstream(upstream)
    if not url:
        logger.warning(
            "publish_pack.venice_hook_no_url",
            agent_id="publish_pack",
            channel=pack.channel,
        )
        return pack

    logger.info(
        "publish_pack.venice_hook_applied",
        agent_id="publish_pack",
        channel=pack.channel,
        media_url=url[:120],
    )
    return pack.model_copy(update={"media_url": url})


__all__ = ["maybe_enrich_publish_pack_media"]
