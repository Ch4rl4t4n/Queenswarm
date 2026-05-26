"""X (Twitter) API v2 helpers — verify OAuth token and resolve @username."""

from __future__ import annotations

import uuid

import httpx
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService

logger = get_logger(__name__)


class XAccountSnapshotOut(BaseModel):
    """Authenticated X user after OAuth Connect."""

    model_config = ConfigDict(extra="ignore")

    oauth_configured: bool = False
    connector_ready: bool = False
    user_id: str | None = None
    username: str | None = None
    message: str = ""


def _connector_token_ok(auth_type: str, secrets: dict) -> bool:
    if auth_type == "oauth2":
        return bool(str(secrets.get("oauth2_access_token") or secrets.get("access_token") or "").strip())
    return False


async def _read_x_access_token(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
) -> str | None:
    svc = DynamicConnectorService()
    row = await svc.fetch_by_slug(session, slug="twitter_api_v2")
    if row is None:
        return None
    secrets = svc._secrets_dict(row)  # noqa: SLF001
    if not _connector_token_ok(str(row.auth_type or ""), secrets):
        return None
    token = str(secrets.get("oauth2_access_token") or secrets.get("access_token") or "").strip()
    return token or None


async def fetch_x_user_profile(*, access_token: str) -> tuple[str, str]:
    """Return (user_id, username) from GET /2/users/me."""

    headers = {"Authorization": f"Bearer {access_token.strip()}"}
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            "https://api.twitter.com/2/users/me",
            headers=headers,
            params={"user.fields": "username"},
        )
    if resp.status_code >= 400:
        msg = f"x_users_me_http_{resp.status_code}"
        raise ValueError(msg)
    payload = resp.json()
    if not isinstance(payload, dict):
        msg = "x_users_me_invalid_response"
        raise ValueError(msg)
    data = payload.get("data")
    if not isinstance(data, dict):
        msg = "x_users_me_missing_data"
        raise ValueError(msg)
    user_id = str(data.get("id") or "").strip()
    username = str(data.get("username") or "").strip()
    if not user_id:
        msg = "x_users_me_missing_user_id"
        raise ValueError(msg)
    return user_id, username


async def build_x_account_snapshot(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    oauth_x_configured: bool,
) -> XAccountSnapshotOut:
    """Load X profile when twitter_api_v2 connector has OAuth token."""

    token = await _read_x_access_token(session, dashboard_user_id=dashboard_user_id)
    if token is None:
        return XAccountSnapshotOut(
            oauth_configured=oauth_x_configured,
            connector_ready=False,
            message="Install X connector and complete OAuth in Connector Hub.",
        )
    try:
        user_id, username = await fetch_x_user_profile(access_token=token)
    except ValueError as exc:
        logger.warning(
            "x_social_context.fetch_failed",
            agent_id=str(dashboard_user_id),
            swarm_id="twitter_api_v2",
            task_id="x_account",
            error=str(exc),
        )
        return XAccountSnapshotOut(
            oauth_configured=oauth_x_configured,
            connector_ready=True,
            message=str(exc),
        )
    return XAccountSnapshotOut(
        oauth_configured=oauth_x_configured,
        connector_ready=True,
        user_id=user_id,
        username=username,
        message="",
    )


__all__ = ["XAccountSnapshotOut", "build_x_account_snapshot", "fetch_x_user_profile"]
