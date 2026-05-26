"""Meta Graph helpers — resolve Instagram / Facebook Page ids for social publish."""

from __future__ import annotations

import uuid
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService

logger = get_logger(__name__)


def _connector_token_ok(auth_type: str, secrets: dict[str, Any]) -> bool:
    if auth_type == "oauth2":
        return bool(str(secrets.get("oauth2_access_token") or secrets.get("access_token") or "").strip())
    return False

_GRAPH_BASE = "https://graph.facebook.com/v21.0"


class MetaPageAccountOut(BaseModel):
    """One Facebook Page linked to the operator Meta OAuth token."""

    model_config = ConfigDict(extra="ignore")

    page_id: str
    page_name: str
    ig_user_id: str | None = None
    ig_username: str | None = None


class MetaAccountsSnapshotOut(BaseModel):
    """Pages + Instagram business accounts discoverable from Meta OAuth."""

    model_config = ConfigDict(extra="ignore")

    oauth_configured: bool = False
    connector_ready: bool = False
    pages: list[MetaPageAccountOut] = Field(default_factory=list)
    default_ig_user_id: str | None = None
    default_page_id: str | None = None
    message: str = ""


async def _read_meta_access_token(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    connector_slug: str = "instagram_graph",
) -> str | None:
    """Return sealed Meta user access token from Dynamic Hub row."""

    svc = DynamicConnectorService()
    row = await svc.fetch_by_slug(session, slug=connector_slug)
    if row is None:
        return None
    secrets = svc._secrets_dict(row)  # noqa: SLF001
    if not _connector_token_ok(str(row.auth_type or ""), secrets):
        return None
    token = str(secrets.get("oauth2_access_token") or secrets.get("access_token") or "").strip()
    return token or None


async def fetch_meta_page_accounts(*, access_token: str) -> list[MetaPageAccountOut]:
    """List Pages and linked Instagram business accounts via Graph API."""

    params = {
        "fields": "id,name,instagram_business_account{id,username}",
        "access_token": access_token.strip(),
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{_GRAPH_BASE}/me/accounts", params=params)
    if resp.status_code >= 400:
        msg = f"meta_accounts_http_{resp.status_code}"
        raise ValueError(msg)
    payload = resp.json()
    if not isinstance(payload, dict):
        msg = "meta_accounts_invalid_response"
        raise ValueError(msg)
    data = payload.get("data")
    if not isinstance(data, list):
        return []

    pages: list[MetaPageAccountOut] = []
    for row in data:
        if not isinstance(row, dict):
            continue
        page_id = str(row.get("id") or "").strip()
        if not page_id:
            continue
        page_name = str(row.get("name") or page_id)
        ig_block = row.get("instagram_business_account")
        ig_user_id: str | None = None
        ig_username: str | None = None
        if isinstance(ig_block, dict):
            ig_user_id = str(ig_block.get("id") or "").strip() or None
            ig_username = str(ig_block.get("username") or "").strip() or None
        pages.append(
            MetaPageAccountOut(
                page_id=page_id,
                page_name=page_name,
                ig_user_id=ig_user_id,
                ig_username=ig_username,
            ),
        )
    return pages


async def build_meta_accounts_snapshot(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    oauth_meta_configured: bool,
) -> MetaAccountsSnapshotOut:
    """Discover Meta pages/IG accounts when connector token is present."""

    token = await _read_meta_access_token(session, dashboard_user_id=dashboard_user_id)
    if token is None:
        return MetaAccountsSnapshotOut(
            oauth_configured=oauth_meta_configured,
            connector_ready=False,
            message="Install Instagram connector and complete Meta OAuth in Connector Hub.",
        )
    try:
        pages = await fetch_meta_page_accounts(access_token=token)
    except ValueError as exc:
        logger.warning(
            "meta_social_context.fetch_failed",
            agent_id=str(dashboard_user_id),
            swarm_id="instagram_graph",
            task_id="meta_accounts",
            error=str(exc),
        )
        return MetaAccountsSnapshotOut(
            oauth_configured=oauth_meta_configured,
            connector_ready=True,
            message=str(exc),
        )

    default_ig = next((p.ig_user_id for p in pages if p.ig_user_id), None)
    default_page = pages[0].page_id if pages else None
    return MetaAccountsSnapshotOut(
        oauth_configured=oauth_meta_configured,
        connector_ready=True,
        pages=pages,
        default_ig_user_id=default_ig,
        default_page_id=default_page,
        message="",
    )


async def enrich_meta_publish_context(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    channel: str,
    context: dict[str, str] | None,
) -> dict[str, str]:
    """Fill ig_user_id / page_id from Graph when operator omitted them."""

    merged: dict[str, str] = dict(context or {})
    if channel not in {"instagram", "facebook"}:
        return merged
    if channel == "instagram" and merged.get("ig_user_id", "").strip():
        return merged
    if channel == "facebook" and merged.get("page_id", "").strip():
        return merged

    from app.core.config import settings

    snapshot = await build_meta_accounts_snapshot(
        session,
        dashboard_user_id=dashboard_user_id,
        oauth_meta_configured=bool(
            settings.oauth_meta_client_id.strip() and settings.oauth_meta_client_secret.strip()
        ),
    )
    if not snapshot.pages:
        return merged

    if channel == "instagram" and snapshot.default_ig_user_id:
        merged["ig_user_id"] = snapshot.default_ig_user_id
    if channel == "facebook" and snapshot.default_page_id:
        merged["page_id"] = snapshot.default_page_id
    return merged


__all__ = [
    "MetaAccountsSnapshotOut",
    "MetaPageAccountOut",
    "build_meta_accounts_snapshot",
    "enrich_meta_publish_context",
    "fetch_meta_page_accounts",
]
