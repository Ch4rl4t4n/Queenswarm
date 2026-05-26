"""TikTok Content Posting API helpers — creator info after OAuth."""

from __future__ import annotations

import uuid
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService

logger = get_logger(__name__)

_TIKTOK_API = "https://open.tiktokapis.com/v2"


class TikTokAccountSnapshotOut(BaseModel):
    """Creator publishing capabilities from Content Posting API."""

    model_config = ConfigDict(extra="ignore")

    oauth_configured: bool = False
    connector_ready: bool = False
    creator_nickname: str | None = None
    max_video_post_duration_sec: int | None = None
    message: str = ""
    review_required: bool = True
    review_note: str = Field(
        default="TikTok Content Posting API requires developer app review before live publish.",
    )


def _connector_token_ok(auth_type: str, secrets: dict[str, Any]) -> bool:
    if auth_type == "oauth2":
        return bool(str(secrets.get("oauth2_access_token") or secrets.get("access_token") or "").strip())
    return False


async def _read_tiktok_access_token(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
) -> str | None:
    svc = DynamicConnectorService()
    row = await svc.fetch_by_slug(session, slug="tiktok_content")
    if row is None:
        return None
    secrets = svc._secrets_dict(row)  # noqa: SLF001
    if not _connector_token_ok(str(row.auth_type or ""), secrets):
        return None
    token = str(secrets.get("oauth2_access_token") or secrets.get("access_token") or "").strip()
    return token or None


async def fetch_tiktok_creator_info(*, access_token: str) -> dict[str, Any]:
    """Query creator_info via Content Posting API."""

    headers = {
        "Authorization": f"Bearer {access_token.strip()}",
        "Content-Type": "application/json; charset=UTF-8",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{_TIKTOK_API}/post/publish/creator_info/query/",
            headers=headers,
            json={},
        )
    if resp.status_code >= 400:
        msg = f"tiktok_creator_info_http_{resp.status_code}"
        raise ValueError(msg)
    payload = resp.json()
    if not isinstance(payload, dict):
        msg = "tiktok_creator_info_invalid_response"
        raise ValueError(msg)
    data = payload.get("data")
    if isinstance(data, dict):
        return data
    return payload


async def build_tiktok_account_snapshot(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    oauth_tiktok_configured: bool,
) -> TikTokAccountSnapshotOut:
    """Verify TikTok OAuth token and load creator publishing metadata."""

    token = await _read_tiktok_access_token(session, dashboard_user_id=dashboard_user_id)
    if token is None:
        return TikTokAccountSnapshotOut(
            oauth_configured=oauth_tiktok_configured,
            connector_ready=False,
            message="Install TikTok connector and complete OAuth in Connector Hub.",
        )
    try:
        info = await fetch_tiktok_creator_info(access_token=token)
    except ValueError as exc:
        logger.warning(
            "tiktok_social_context.fetch_failed",
            agent_id=str(dashboard_user_id),
            swarm_id="tiktok_content",
            task_id="tiktok_account",
            error=str(exc),
        )
        return TikTokAccountSnapshotOut(
            oauth_configured=oauth_tiktok_configured,
            connector_ready=True,
            message=str(exc),
        )

    nickname_raw = info.get("creator_nickname") or info.get("creator_username")
    nickname = str(nickname_raw).strip() if nickname_raw else None
    max_dur_raw = info.get("max_video_post_duration_sec")
    max_dur = int(max_dur_raw) if isinstance(max_dur_raw, (int, float)) else None
    return TikTokAccountSnapshotOut(
        oauth_configured=oauth_tiktok_configured,
        connector_ready=True,
        creator_nickname=nickname,
        max_video_post_duration_sec=max_dur,
        message="",
    )


__all__ = [
    "TikTokAccountSnapshotOut",
    "build_tiktok_account_snapshot",
    "fetch_tiktok_creator_info",
]
