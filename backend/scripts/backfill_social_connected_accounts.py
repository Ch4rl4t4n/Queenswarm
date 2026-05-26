#!/usr/bin/env python3
"""One-shot backfill: migrate legacy Dynamic Hub OAuth tokens into social_connected_accounts."""

from __future__ import annotations

import asyncio
import uuid

import structlog
from sqlalchemy import select

from app.application.services.oauth_consent.providers import OAUTH_SURFACES
from app.application.services.social_connected_accounts import (
    SOCIAL_OAUTH_PROVIDER_KEYS,
    upsert_accounts_from_oauth,
)
from app.core.database import async_session
from app.infrastructure.connectors.dynamic.schemas import DynamicConnectorSecretsInbound
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService
from app.infrastructure.persistence.models.dashboard_user import DashboardUser
from app.infrastructure.persistence.models.tenant import Tenant

logger = structlog.get_logger(__name__)

_PROVIDER_SLUG: dict[str, str] = {
    "instagram_graph": "instagram_graph",
    "facebook_graph": "facebook_graph",
    "twitter_api_v2": "twitter_api_v2",
    "tiktok_content": "tiktok_content",
}


async def backfill_social_accounts_from_connectors(*, tenant_id: uuid.UUID | None = None) -> int:
    """Import tokens from global connector rows into per-tenant social accounts."""

    created = 0
    async with async_session() as session:
        svc = DynamicConnectorService()
        tenants: list[Tenant] = []
        if tenant_id is not None:
            tenant = await session.get(Tenant, tenant_id)
            if tenant is not None:
                tenants = [tenant]
        else:
            result = await session.scalars(select(Tenant))
            tenants = list(result.all())

        for tenant in tenants:
            admin = await session.scalar(
                select(DashboardUser).where(DashboardUser.active_tenant_id == tenant.id).limit(1),
            )
            if admin is None:
                continue
            for provider_key in SOCIAL_OAUTH_PROVIDER_KEYS:
                slug = _PROVIDER_SLUG.get(provider_key, provider_key)
                row = await svc.fetch_by_slug(session, slug=slug)
                if row is None:
                    continue
                secrets = svc._secrets_dict(row)  # noqa: SLF001
                token = str(secrets.get("oauth2_access_token") or secrets.get("access_token") or "").strip()
                if not token:
                    continue
                spec = OAUTH_SURFACES.get(provider_key)
                if spec is None:
                    continue
                inbound = DynamicConnectorSecretsInbound(
                    oauth2_access_token=token,
                    oauth2_refresh_token=secrets.get("oauth2_refresh_token"),
                    oauth2_token_endpoint=str(secrets.get("oauth2_token_endpoint") or spec.token_url),
                    oauth2_client_id=secrets.get("oauth2_client_id"),
                    oauth2_client_secret=secrets.get("oauth2_client_secret"),
                )
                saved = await upsert_accounts_from_oauth(
                    session,
                    tenant_id=tenant.id,
                    dashboard_user_id=admin.id,
                    spec=spec,
                    secrets=inbound,
                    access_token=token,
                )
                created += len(saved)
                logger.info(
                    "backfill_social_accounts.imported",
                    agent_id=str(admin.id),
                    swarm_id=provider_key,
                    task_id=str(tenant.id),
                    count=len(saved),
                )
        await session.commit()
    return created


async def _main() -> None:
    count = await backfill_social_accounts_from_connectors()
    print(f"backfill_complete accounts_upserted={count}")


if __name__ == "__main__":
    asyncio.run(_main())
