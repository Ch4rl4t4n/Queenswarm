"""Optional Monid video hook when TikTok publish pack lacks media_url."""

from __future__ import annotations

import json
import re
import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.execution_studio import execute_studio_tool
from app.application.services.publish_media import classify_publish_media_url, is_safe_publish_media_url
from app.application.services.publish_pack import PublishPackArtifact
from app.core.config import settings
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService
from app.infrastructure.persistence.models.tenant import Tenant

logger = structlog.get_logger(__name__)

_MONID_SLUG = "monid_mcp"
_RE_HTTPS_MEDIA = re.compile(r"https://[^\s\"'<>]+", re.IGNORECASE)
_VIDEO_EXTENSIONS = (".mp4", ".webm", ".mov", ".m4v")


def _monid_video_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    lane = dict(root.get("publish_lane") or {})
    bucket = dict(lane.get("monid_video") or {})
    return bucket if isinstance(bucket, dict) else {}


def _extract_video_url_from_upstream(upstream: dict[str, Any]) -> str | None:
    """Parse first safe HTTPS video URL from Monid run/discover output."""

    chunks: list[str] = []
    simulated = upstream.get("simulated_result")
    if simulated is not None:
        chunks.append(json.dumps(simulated) if isinstance(simulated, dict) else str(simulated))
    raw = upstream.get("result")
    if raw is not None:
        chunks.append(str(raw))
    for chunk in chunks:
        for match in _RE_HTTPS_MEDIA.finditer(chunk):
            candidate = match.group(0).rstrip(".,);]")
            if not is_safe_publish_media_url(candidate):
                continue
            kind = classify_publish_media_url(candidate)
            if kind in {"video", "unknown"} and (
                kind == "video" or candidate.lower().endswith(_VIDEO_EXTENSIONS)
            ):
                return candidate
    return None


async def _monid_connector_ready(session: AsyncSession, *, dashboard_user_id: uuid.UUID) -> bool:
    svc = DynamicConnectorService()
    row = await svc.fetch_by_slug(session, slug=_MONID_SLUG)
    if row is None or not row.is_active:
        return False
    secrets = svc._secrets_dict(row)  # noqa: SLF001
    token = str(secrets.get("bearer_token") or secrets.get("api_key") or "").strip()
    return bool(token)


def _build_monid_video_input(pack: PublishPackArtifact, bucket: dict[str, Any]) -> dict[str, Any]:
    template = dict(bucket.get("input_template") or {})
    if template:
        rendered: dict[str, Any] = {}
        for key, value in template.items():
            text = str(value)
            text = text.replace("{{title}}", pack.title).replace("{{body}}", pack.body[:500])
            rendered[str(key)] = text
        return rendered
    return {
        "prompt": f"TikTok short video for: {pack.title}. {pack.body[:400]}",
        "duration_sec": 15,
    }


async def maybe_enrich_tiktok_video_media(
    session: AsyncSession,
    *,
    pack: PublishPackArtifact,
    dashboard_user_id: uuid.UUID | None,
    tenant: Tenant | None,
) -> PublishPackArtifact:
    """When enabled, resolve TikTok video URL via tenant Monid config or discover."""

    if not settings.publish_pack_monid_video_hook_enabled:
        return pack
    if pack.channel != "tiktok" or pack.media_url:
        return pack
    if dashboard_user_id is None:
        return pack
    if not await _monid_connector_ready(session, dashboard_user_id=dashboard_user_id):
        logger.info(
            "publish_pack.monid_video_skipped",
            agent_id="publish_pack",
            reason="monid_not_ready",
        )
        return pack

    bucket = _monid_video_bucket(tenant.operator_settings if tenant is not None else None)
    provider = str(bucket.get("provider") or "").strip()
    endpoint = str(bucket.get("endpoint") or "").strip()

    if not provider or not endpoint:
        discover = await execute_studio_tool(
            session,
            dashboard_user_id=dashboard_user_id,
            tenant=tenant,
            connector_slug=_MONID_SLUG,
            tool_name="discover",
            arguments={"query": "short form video generation social media", "limit": 5},
            mode="live",
            operator_confirmed=True,
        )
        if not discover.get("ok"):
            return pack
        raw = str(discover.get("result") or "")
        try:
            payload = json.loads(raw) if raw.startswith("{") else {}
        except json.JSONDecodeError:
            payload = {}
        endpoints = payload.get("endpoints") if isinstance(payload.get("endpoints"), list) else []
        for item in endpoints:
            if not isinstance(item, dict):
                continue
            provider = str(item.get("provider") or provider).strip()
            endpoint = str(item.get("endpoint") or endpoint).strip()
            if provider and endpoint:
                break
        if not provider or not endpoint:
            logger.warning(
                "publish_pack.monid_video_no_endpoint",
                agent_id="publish_pack",
            )
            return pack

    run_args = {
        "provider": provider,
        "endpoint": endpoint,
        "input": _build_monid_video_input(pack, bucket),
    }
    upstream = await execute_studio_tool(
        session,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
        connector_slug=_MONID_SLUG,
        tool_name="run",
        arguments=run_args,
        mode="live",
        operator_confirmed=True,
    )
    if not upstream.get("ok"):
        logger.warning(
            "publish_pack.monid_video_run_failed",
            agent_id="publish_pack",
            error=str(upstream.get("error") or "")[:200],
        )
        return pack

    url = _extract_video_url_from_upstream(upstream)
    if not url:
        logger.warning(
            "publish_pack.monid_video_no_url",
            agent_id="publish_pack",
        )
        return pack

    logger.info(
        "publish_pack.monid_video_applied",
        agent_id="publish_pack",
        media_url=url[:120],
    )
    return pack.model_copy(update={"media_url": url})


__all__ = [
    "extract_monid_video_url_from_upstream",
    "maybe_enrich_tiktok_video_media",
    "monid_video_bucket_from_operator_settings",
]


def extract_monid_video_url_from_upstream(upstream: dict[str, Any]) -> str | None:
    """Parse first safe HTTPS video URL from Monid run/discover output."""

    return _extract_video_url_from_upstream(upstream)


def monid_video_bucket_from_operator_settings(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    """Return tenant publish_lane.monid_video config bucket."""

    return _monid_video_bucket(operator_settings)
