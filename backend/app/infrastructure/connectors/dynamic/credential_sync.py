"""Sync OAuth/API secrets from connector vault into Dynamic Hub rows before invoke."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.connectors.dynamic.schemas import DynamicConnectorSecretsInbound
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService
from app.infrastructure.connectors.secure_vault import seal_dynamic_connector_blob, vault_load_envelope
from app.infrastructure.persistence.models.dynamic_connector import DynamicConnector
from app.core.logging import get_logger

logger = get_logger(__name__)


def _merged_oauth_payload(
    current: dict[str, Any],
    *,
    access_token: str | None,
    refresh_token: str | None,
    token_endpoint: str | None,
    client_id: str | None,
    client_secret: str | None,
) -> dict[str, Any]:
    """Merge vault OAuth fields into hub secret blob without dropping unrelated keys."""

    merged = dict(current)
    if access_token:
        merged["oauth2_access_token"] = access_token
    if refresh_token:
        merged["oauth2_refresh_token"] = refresh_token
    if token_endpoint:
        merged["oauth2_token_endpoint"] = token_endpoint
    if client_id:
        merged["oauth2_client_id"] = client_id
    if client_secret:
        merged["oauth2_client_secret"] = client_secret
    return merged


async def hydrate_connector_secrets_from_vault(
    session: AsyncSession,
    row: DynamicConnector,
    *,
    dashboard_user_id: uuid.UUID,
) -> bool:
    """Copy fresher vault credentials into the hub row when available.

    Args:
        session: Async SQLAlchemy session.
        row: Dynamic connector ORM row to hydrate.
        dashboard_user_id: Operator owning the vault entry.

    Returns:
        True when hub ciphertext was updated.
    """

    if row.dashboard_user_id is not None and row.dashboard_user_id != dashboard_user_id:
        return False

    envelope = await vault_load_envelope(session, slug=row.slug.strip().lower(), user_id=dashboard_user_id)
    if envelope is None:
        return False

    svc = DynamicConnectorService()
    current = svc._secrets_dict(row)  # noqa: SLF001

    if envelope.kind == "oauth2":
        access = envelope.oauth2_access_token
        if not isinstance(access, str) or not access.strip():
            return False
        merged = _merged_oauth_payload(
            current,
            access_token=access.strip(),
            refresh_token=envelope.oauth2_refresh_token,
            token_endpoint=envelope.oauth2_token_endpoint,
            client_id=envelope.oauth2_client_id,
            client_secret=envelope.oauth2_client_secret,
        )
    elif envelope.kind == "api_key":
        key = envelope.api_key
        if not isinstance(key, str) or not key.strip():
            return False
        merged = dict(current)
        merged["api_key"] = key.strip()
    else:
        return False

    if merged == current:
        return False

    row.secrets_cipher = seal_dynamic_connector_blob(merged)
    await session.flush()
    logger.info(
        "execution_studio.vault_hydrated",
        agent_id=str(dashboard_user_id),
        swarm_id=row.slug,
        task_id="credential-sync",
    )
    return True


async def persist_hub_secrets_from_inbound(
    session: AsyncSession,
    row: DynamicConnector,
    *,
    secrets: DynamicConnectorSecretsInbound,
) -> None:
    """Seal inbound secrets onto hub row (shared by OAuth callback + refresh sync)."""

    row.secrets_cipher = seal_dynamic_connector_blob(secrets.to_sealed_payload())
    await session.flush()


def hub_secrets_from_vault_envelope(envelope: Any) -> DynamicConnectorSecretsInbound | None:
    """Map vault envelope into hub inbound secrets for dual-write."""

    if envelope.kind == "oauth2":
        access = envelope.oauth2_access_token
        if not isinstance(access, str) or not access.strip():
            return None
        return DynamicConnectorSecretsInbound(
            oauth2_access_token=access.strip(),
            oauth2_refresh_token=envelope.oauth2_refresh_token,
            oauth2_token_endpoint=envelope.oauth2_token_endpoint,
            oauth2_client_id=envelope.oauth2_client_id,
            oauth2_client_secret=envelope.oauth2_client_secret,
        )
    if envelope.kind == "api_key":
        key = envelope.api_key
        if not isinstance(key, str) or not key.strip():
            return None
        return DynamicConnectorSecretsInbound(api_key=key.strip())
    return None


__all__ = [
    "hydrate_connector_secrets_from_vault",
    "hub_secrets_from_vault_envelope",
    "persist_hub_secrets_from_inbound",
]
