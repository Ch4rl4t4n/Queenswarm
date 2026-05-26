"""Multi-account social OAuth storage — resolve tokens per tenant/channel/account."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.meta_social_context import fetch_meta_page_accounts
from app.application.services.oauth_consent.providers import OAuthSurfaceSpec
from app.application.services.tiktok_social_context import fetch_tiktok_creator_info
from app.application.services.x_social_context import fetch_x_user_profile
from app.core.config import Settings, get_settings
from app.infrastructure.connectors.dynamic.schemas import DynamicConnectorSecretsInbound
from app.infrastructure.connectors.secure_vault import seal_dynamic_connector_blob, unseal_dynamic_connector_blob
from app.infrastructure.persistence.models.social_connected_account import SocialConnectedAccount
from app.infrastructure.persistence.models.tenant import Tenant

logger = structlog.get_logger(__name__)

SocialAccountChannel = Literal["instagram", "facebook", "twitter", "tiktok"]

SOCIAL_OAUTH_PROVIDER_KEYS: frozenset[str] = frozenset(
    {
        "instagram_graph",
        "facebook_graph",
        "twitter_api_v2",
        "tiktok_content",
    },
)

_PROVIDER_CONNECTOR_SLUG: dict[str, str] = {
    "instagram_graph": "instagram_graph",
    "facebook_graph": "facebook_graph",
    "twitter_api_v2": "twitter_api_v2",
    "tiktok_content": "tiktok_content",
}


class SocialConnectedAccountOut(BaseModel):
    """API-safe view of one tenant social account."""

    model_config = ConfigDict(extra="ignore")

    id: uuid.UUID
    channel: SocialAccountChannel
    label: str
    oauth_provider_key: str
    connector_slug: str
    external_user_id: str | None = None
    external_username: str | None = None
    profile_meta: dict[str, Any] = Field(default_factory=dict)
    is_default: bool = False
    status: str = "active"
    created_at: datetime


class SocialConnectedAccountsSnapshotOut(BaseModel):
    """Grouped connected accounts for Social Publish panel."""

    model_config = ConfigDict(extra="ignore")

    accounts: list[SocialConnectedAccountOut] = Field(default_factory=list)
    defaults: dict[str, str] = Field(default_factory=dict)


class SocialAccountPatchBody(BaseModel):
    """Patch label or default flag."""

    model_config = ConfigDict(extra="forbid")

    label: str | None = Field(default=None, min_length=1, max_length=256)
    is_default: bool | None = None


def _secrets_payload_from_inbound(secrets: DynamicConnectorSecretsInbound) -> dict[str, Any]:
    return secrets.to_sealed_payload()


def _secrets_dict_from_account(row: SocialConnectedAccount) -> dict[str, Any]:
    return unseal_dynamic_connector_blob(row.secrets_cipher)


def account_to_out(row: SocialConnectedAccount) -> SocialConnectedAccountOut:
    """Map ORM row to API model."""

    return SocialConnectedAccountOut(
        id=row.id,
        channel=row.channel,  # type: ignore[arg-type]
        label=row.label,
        oauth_provider_key=row.oauth_provider_key,
        connector_slug=row.connector_slug,
        external_user_id=row.external_user_id,
        external_username=row.external_username,
        profile_meta=dict(row.profile_meta or {}),
        is_default=bool(row.is_default),
        status=row.status,
        created_at=row.created_at,
    )


async def list_social_accounts(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    channel: SocialAccountChannel | None = None,
    active_only: bool = True,
) -> list[SocialConnectedAccount]:
    """List tenant social accounts, optionally filtered by channel."""

    if tenant_id is None:
        return []
    stmt = select(SocialConnectedAccount).where(SocialConnectedAccount.tenant_id == tenant_id)
    if channel is not None:
        stmt = stmt.where(SocialConnectedAccount.channel == channel)
    if active_only:
        stmt = stmt.where(SocialConnectedAccount.status == "active")
    stmt = stmt.order_by(SocialConnectedAccount.is_default.desc(), SocialConnectedAccount.created_at.asc())
    result = await session.scalars(stmt)
    return list(result.all())


async def get_social_account(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    account_id: uuid.UUID,
) -> SocialConnectedAccount | None:
    """Fetch one account scoped to tenant."""

    if tenant_id is None:
        return None
    return await session.scalar(
        select(SocialConnectedAccount).where(
            SocialConnectedAccount.id == account_id,
            SocialConnectedAccount.tenant_id == tenant_id,
            SocialConnectedAccount.status == "active",
        ),
    )


async def build_social_accounts_snapshot(
    session: AsyncSession,
    *,
    tenant: Tenant | None,
) -> SocialConnectedAccountsSnapshotOut:
    """Return all connected accounts + channel default ids from tenant settings."""

    tenant_id = tenant.id if tenant is not None else None
    rows = await list_social_accounts(session, tenant_id=tenant_id)
    defaults: dict[str, str] = {}
    operator = dict(tenant.operator_settings or {}) if tenant is not None else {}
    raw_defaults = operator.get("social_publish_defaults")
    if isinstance(raw_defaults, dict):
        for key, value in raw_defaults.items():
            text = str(value or "").strip()
            if text:
                defaults[str(key).strip().lower()] = text
    for row in rows:
        if row.is_default:
            defaults.setdefault(row.channel, str(row.id))
    return SocialConnectedAccountsSnapshotOut(
        accounts=[account_to_out(row) for row in rows],
        defaults=defaults,
    )


def _tenant_default_account_id(tenant: Tenant | None, channel: str) -> uuid.UUID | None:
    if tenant is None:
        return None
    operator = dict(tenant.operator_settings or {})
    raw = operator.get("social_publish_defaults")
    if not isinstance(raw, dict):
        return None
    value = raw.get(channel)
    if value is None:
        return None
    try:
        return uuid.UUID(str(value).strip())
    except ValueError:
        return None


async def resolve_social_account_for_publish(
    session: AsyncSession,
    *,
    tenant: Tenant | None,
    channel: SocialAccountChannel,
    account_id: uuid.UUID | None = None,
    structured: dict[str, Any] | None = None,
) -> SocialConnectedAccount | None:
    """Resolve account from explicit id, publish pack, tenant default, or channel default row."""

    tenant_id = tenant.id if tenant is not None else None
    candidates: list[uuid.UUID] = []

    if account_id is not None:
        candidates.append(account_id)

    if structured is not None:
        pack_id = str(structured.get("social_account_id") or "").strip()
        if pack_id:
            try:
                candidates.append(uuid.UUID(pack_id))
            except ValueError:
                pass

    tenant_default = _tenant_default_account_id(tenant, channel)
    if tenant_default is not None:
        candidates.append(tenant_default)

    seen: set[uuid.UUID] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        row = await get_social_account(session, tenant_id=tenant_id, account_id=candidate)
        if row is not None and row.channel == channel:
            return row

    rows = await list_social_accounts(session, tenant_id=tenant_id, channel=channel)
    default_row = next((row for row in rows if row.is_default), None)
    if default_row is not None:
        return default_row
    return rows[0] if rows else None


def publish_context_from_account(row: SocialConnectedAccount) -> dict[str, str]:
    """Map stored profile_meta into social publish context keys."""

    meta = dict(row.profile_meta or {})
    ctx: dict[str, str] = {}
    for key in (
        "ig_user_id",
        "page_id",
        "gmail_user_id",
        "newsletter_to",
        "resend_from",
    ):
        value = meta.get(key)
        if value is not None and str(value).strip():
            ctx[key] = str(value).strip()
    return ctx


async def set_channel_default(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    account_id: uuid.UUID,
) -> SocialConnectedAccount | None:
    """Mark one account as default for its channel within the tenant."""

    row = await get_social_account(session, tenant_id=tenant_id, account_id=account_id)
    if row is None:
        return None
    await session.execute(
        update(SocialConnectedAccount)
        .where(
            SocialConnectedAccount.tenant_id == tenant_id,
            SocialConnectedAccount.channel == row.channel,
            SocialConnectedAccount.id != row.id,
        )
        .values(is_default=False),
    )
    row.is_default = True
    await session.flush()
    return row


async def patch_social_account(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    account_id: uuid.UUID,
    body: SocialAccountPatchBody,
) -> SocialConnectedAccount | None:
    """Update label and/or default flag."""

    row = await get_social_account(session, tenant_id=tenant_id, account_id=account_id)
    if row is None:
        return None
    if body.label is not None:
        row.label = body.label.strip()
    if body.is_default is True:
        await set_channel_default(session, tenant_id=tenant_id, account_id=row.id)
    elif body.is_default is False:
        row.is_default = False
    await session.flush()
    return row


async def revoke_social_account(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    account_id: uuid.UUID,
) -> bool:
    """Soft-revoke account — keeps row for audit."""

    row = await get_social_account(session, tenant_id=tenant_id, account_id=account_id)
    if row is None:
        return False
    row.status = "revoked"
    row.is_default = False
    await session.flush()
    return True


class _AccountSeed(BaseModel):
    """Internal seed for upserting one connected account."""

    model_config = ConfigDict(extra="forbid")

    channel: SocialAccountChannel
    account_key: str
    label: str
    external_user_id: str | None = None
    external_username: str | None = None
    profile_meta: dict[str, Any] = Field(default_factory=dict)


async def _discover_account_seeds(
    *,
    provider_key: str,
    access_token: str,
) -> list[_AccountSeed]:
    """Discover one or more logical accounts after OAuth token exchange."""

    if provider_key == "twitter_api_v2":
        user_id, username = await fetch_x_user_profile(access_token=access_token)
        return [
            _AccountSeed(
                channel="twitter",
                account_key=f"x:{user_id}",
                label=f"@{username}" if username else user_id,
                external_user_id=user_id,
                external_username=username or None,
            ),
        ]

    if provider_key in {"instagram_graph", "facebook_graph"}:
        pages = await fetch_meta_page_accounts(access_token=access_token)
        seeds: list[_AccountSeed] = []
        if provider_key == "instagram_graph":
            for page in pages:
                if not page.ig_user_id:
                    continue
                label = f"@{page.ig_username}" if page.ig_username else page.page_name
                seeds.append(
                    _AccountSeed(
                        channel="instagram",
                        account_key=f"ig:{page.ig_user_id}",
                        label=label,
                        external_user_id=page.ig_user_id,
                        external_username=page.ig_username,
                        profile_meta={
                            "ig_user_id": page.ig_user_id,
                            "page_id": page.page_id,
                            "page_name": page.page_name,
                        },
                    ),
                )
            if not seeds and pages:
                page = pages[0]
                seeds.append(
                    _AccountSeed(
                        channel="instagram",
                        account_key=f"page:{page.page_id}",
                        label=page.page_name,
                        profile_meta={"page_id": page.page_id, "page_name": page.page_name},
                    ),
                )
            if not seeds:
                seeds.append(
                    _AccountSeed(
                        channel="instagram",
                        account_key="meta:unknown",
                        label="Meta account",
                    ),
                )
            return seeds

        for page in pages:
            seeds.append(
                _AccountSeed(
                    channel="facebook",
                    account_key=f"page:{page.page_id}",
                    label=page.page_name,
                    external_user_id=page.page_id,
                    profile_meta={"page_id": page.page_id, "page_name": page.page_name},
                ),
            )
        if not seeds:
            seeds.append(
                _AccountSeed(
                    channel="facebook",
                    account_key="meta:unknown",
                    label="Meta account",
                ),
            )
        return seeds

    if provider_key == "tiktok_content":
        info = await fetch_tiktok_creator_info(access_token=access_token)
        nickname_raw = info.get("creator_nickname") or info.get("creator_username")
        nickname = str(nickname_raw).strip() if nickname_raw else None
        key = f"tiktok:{nickname or 'creator'}"
        return [
            _AccountSeed(
                channel="tiktok",
                account_key=key,
                label=nickname or "TikTok creator",
                external_username=nickname,
            ),
        ]

    return []


async def upsert_accounts_from_oauth(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    spec: OAuthSurfaceSpec,
    secrets: DynamicConnectorSecretsInbound,
    access_token: str,
    settings: Settings | None = None,
) -> list[SocialConnectedAccount]:
    """Create or refresh tenant social account rows after OAuth — never overwrites other accounts."""

    provider_key = spec.provider_key.strip().lower()
    if provider_key not in SOCIAL_OAUTH_PROVIDER_KEYS:
        return []

    connector_slug = _PROVIDER_CONNECTOR_SLUG.get(provider_key, provider_key)
    cipher = seal_dynamic_connector_blob(_secrets_payload_from_inbound(secrets), settings=settings)

    try:
        seeds = await _discover_account_seeds(provider_key=provider_key, access_token=access_token)
    except ValueError as exc:
        logger.warning(
            "social_connected_accounts.discover_failed",
            agent_id=str(dashboard_user_id),
            swarm_id=provider_key,
            task_id="oauth-upsert",
            error=str(exc),
        )
        seeds = [
            _AccountSeed(
                channel=_fallback_channel_for_provider(provider_key),
                account_key=f"{provider_key}:token",
                label=spec.label,
            ),
        ]

    saved: list[SocialConnectedAccount] = []
    for seed in seeds:
        existing = await session.scalar(
            select(SocialConnectedAccount).where(
                SocialConnectedAccount.tenant_id == tenant_id,
                SocialConnectedAccount.channel == seed.channel,
                SocialConnectedAccount.account_key == seed.account_key,
            ),
        )
        if existing is None:
            existing_rows = await list_social_accounts(session, tenant_id=tenant_id, channel=seed.channel)
            row = SocialConnectedAccount(
                tenant_id=tenant_id,
                dashboard_user_id=dashboard_user_id,
                channel=seed.channel,
                account_key=seed.account_key,
                label=seed.label,
                oauth_provider_key=provider_key,
                connector_slug=connector_slug,
                external_user_id=seed.external_user_id,
                external_username=seed.external_username,
                profile_meta=seed.profile_meta,
                secrets_cipher=cipher,
                is_default=not existing_rows,
                status="active",
            )
            session.add(row)
            await session.flush()
        else:
            existing.dashboard_user_id = dashboard_user_id
            existing.label = seed.label
            existing.oauth_provider_key = provider_key
            existing.connector_slug = connector_slug
            existing.external_user_id = seed.external_user_id
            existing.external_username = seed.external_username
            existing.profile_meta = seed.profile_meta
            existing.secrets_cipher = cipher
            existing.status = "active"
            existing.updated_at = datetime.now(tz=UTC)
            row = existing
            await session.flush()
        saved.append(row)

    logger.info(
        "social_connected_accounts.upserted",
        agent_id=str(dashboard_user_id),
        swarm_id=provider_key,
        task_id=str(tenant_id),
        count=len(saved),
    )
    return saved


def _fallback_channel_for_provider(provider_key: str) -> SocialAccountChannel:
    mapping: dict[str, SocialAccountChannel] = {
        "instagram_graph": "instagram",
        "facebook_graph": "facebook",
        "twitter_api_v2": "twitter",
        "tiktok_content": "tiktok",
    }
    return mapping.get(provider_key, "twitter")


def load_account_secrets(row: SocialConnectedAccount) -> dict[str, Any]:
    """Return decrypted OAuth secrets for connector invoke."""

    return _secrets_dict_from_account(row)


__all__ = [
    "SocialAccountPatchBody",
    "SocialConnectedAccountOut",
    "SocialConnectedAccountsSnapshotOut",
    "SOCIAL_OAUTH_PROVIDER_KEYS",
    "build_social_accounts_snapshot",
    "get_social_account",
    "list_social_accounts",
    "load_account_secrets",
    "patch_social_account",
    "publish_context_from_account",
    "resolve_social_account_for_publish",
    "revoke_social_account",
    "set_channel_default",
    "upsert_accounts_from_oauth",
]
