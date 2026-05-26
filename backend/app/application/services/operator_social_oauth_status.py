"""Social OAuth readiness for Operator Hub — env + connector status (no secrets)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.social_publish import SOCIAL_OAUTH_CHANNEL_IDS, build_social_publish_snapshot
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant

_SOCIAL_ENV_KEYS: dict[str, tuple[str, str, str]] = {
    "instagram": ("OAUTH_META_CLIENT_ID", "OAUTH_META_CLIENT_SECRET", "https://developers.facebook.com/apps/"),
    "facebook": ("OAUTH_META_CLIENT_ID", "OAUTH_META_CLIENT_SECRET", "https://developers.facebook.com/apps/"),
    "twitter": ("OAUTH_X_CLIENT_ID", "OAUTH_X_CLIENT_SECRET", "https://developer.x.com/en/portal/dashboard"),
    "tiktok": ("OAUTH_TIKTOK_CLIENT_KEY", "OAUTH_TIKTOK_CLIENT_SECRET", "https://developers.tiktok.com"),
}


class OperatorOAuthChannelOut(BaseModel):
    """One social channel row for operator settings."""

    model_config = ConfigDict(extra="ignore")

    channel: str
    label: str
    env_configured: bool
    installed: bool
    active: bool
    credentials_ok: bool
    env_id_key: str | None = None
    env_secret_key: str | None = None
    console_url: str | None = None


class OperatorSocialOAuthStatusOut(BaseModel):
    """Read-only OAuth + publish readiness snapshot."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    live_publish_enabled: bool = False
    env_configured_count: int = 0
    active_channel_count: int = 0
    ready_items_count: int = 0
    simulate_count: int = 0
    channels: list[OperatorOAuthChannelOut] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    prep_scripts: dict[str, str] = Field(default_factory=dict)


def _env_configured_for_channel(channel: str) -> bool:
    """Return whether server env has OAuth keys for a social channel."""

    if channel in {"instagram", "facebook"}:
        return bool(settings.oauth_meta_client_id.strip() and settings.oauth_meta_client_secret.strip())
    if channel == "twitter":
        return bool(settings.oauth_x_client_id.strip() and settings.oauth_x_client_secret.strip())
    if channel == "tiktok":
        return bool(settings.oauth_tiktok_client_key.strip() and settings.oauth_tiktok_client_secret.strip())
    return False


async def compose_operator_social_oauth_status(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
) -> OperatorSocialOAuthStatusOut:
    """Build social OAuth readiness — keys present + connector connected."""

    if not settings.social_publish_enabled:
        return OperatorSocialOAuthStatusOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
        )

    snapshot = await build_social_publish_snapshot(
        session,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
        limit=20,
    )

    channels: list[OperatorOAuthChannelOut] = []
    env_ok = 0
    active_count = 0

    for row in snapshot.channels:
        if row.channel not in SOCIAL_OAUTH_CHANNEL_IDS:
            continue
        env_configured = _env_configured_for_channel(row.channel)
        if env_configured:
            env_ok += 1
        if row.active:
            active_count += 1
        meta = _SOCIAL_ENV_KEYS.get(row.channel, (None, None, None))
        channels.append(
            OperatorOAuthChannelOut(
                channel=row.channel,
                label=row.label,
                env_configured=env_configured,
                installed=bool(row.installed),
                active=bool(row.active),
                credentials_ok=bool(row.credentials_ok),
                env_id_key=meta[0],
                env_secret_key=meta[1],
                console_url=meta[2],
            ),
        )

    audit_count = int(snapshot.audit.count if snapshot.audit else 0)
    blockers: list[str] = []
    if env_ok == 0:
        blockers.append("No OAuth vendor keys in server env — fill .env.prod.oauth and redeploy.")
    elif active_count == 0:
        blockers.append("OAuth keys set but no channel connected — Marketplace → Install → Hub → Connect.")
    if not settings.social_publish_live_enabled:
        blockers.append("SOCIAL_PUBLISH_LIVE_ENABLED=false — simulate OK; live blocked until operator enables.")
    if not snapshot.ready_items:
        blockers.append("No approved publish packs — run operator-publish-lane-prep.sh or approve in Publish Queue.")

    return OperatorSocialOAuthStatusOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        live_publish_enabled=bool(settings.social_publish_live_enabled),
        env_configured_count=env_ok,
        active_channel_count=active_count,
        ready_items_count=len(snapshot.ready_items),
        simulate_count=audit_count,
        channels=channels,
        blockers=blockers,
        prep_scripts={
            "oauth_status": "scripts/operator-social-oauth-status.sh",
            "oauth_redeploy": "scripts/operator-oauth-redeploy.sh",
            "publish_prep": "scripts/operator-publish-lane-prep.sh",
            "simulate_gate": "scripts/operator-publish-simulate-gate.sh",
            "live_prep": "scripts/operator-live-publish-prep.sh",
            "live_gate": "scripts/operator-live-publish-gate.sh",
        },
    )


__all__ = [
    "OperatorOAuthChannelOut",
    "OperatorSocialOAuthStatusOut",
    "compose_operator_social_oauth_status",
]
