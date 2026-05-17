"""Fernet-encrypted credential blobs persisted in Postgres (connector vault).

Keys default to deriving from ``SECRET_KEY`` unless ``CONNECTOR_VAULT_FERNET_KEY``
is set (recommended for production rotations).
"""

from __future__ import annotations

import json
import uuid
from base64 import urlsafe_b64encode
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.connectors.base import ConnectorAuthEnvelope
from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.connector_vault_entry import ConnectorVaultEntry

logger = get_logger(__name__)


class CredentialPayload(BaseModel):
    """JSON payload serialized before AES-Fernet sealing."""

    model_config = {"extra": "ignore"}

    kind: str
    oauth2_access_token: str | None = Field(default=None, max_length=16_384)
    oauth2_refresh_token: str | None = Field(default=None, max_length=16_384)
    oauth2_token_endpoint: str | None = Field(default=None, max_length=2048)
    oauth2_client_id: str | None = Field(default=None, max_length=512)
    oauth2_client_secret: str | None = Field(default=None, max_length=4096)
    api_key: str | None = Field(default=None, max_length=4096)
    scopes: tuple[str, ...] = ()

    @field_validator("kind")
    @classmethod
    def _kind_ok(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if cleaned not in {"oauth2", "api_key"}:
            msg = "kind must be oauth2 or api_key"
            raise ValueError(msg)
        return cleaned

    def to_envelope(self) -> ConnectorAuthEnvelope:
        """Map stored JSON into the outbound auth envelope."""

        return ConnectorAuthEnvelope(
            kind=self.kind,
            oauth2_access_token=self.oauth2_access_token,
            oauth2_refresh_token=self.oauth2_refresh_token,
            oauth2_token_endpoint=self.oauth2_token_endpoint,
            oauth2_client_id=self.oauth2_client_id,
            oauth2_client_secret=self.oauth2_client_secret,
            api_key=self.api_key,
            scopes=self.scopes,
        )


def build_connector_vault_cipher(settings: Settings | None = None) -> Fernet:
    """Build a Fernet instance from configured or derived secrets."""

    resolved = settings if settings is not None else get_settings()
    raw = (resolved.connector_vault_fernet_key or "").strip()
    if raw:
        return Fernet(raw.encode("ascii"))
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"qs.connector.vault.v1",
        info=b"aead",
    )
    material = hkdf.derive(resolved.secret_key.encode("utf-8"))
    encoded = urlsafe_b64encode(material)
    return Fernet(encoded)


async def vault_upsert_credential(
    db: AsyncSession,
    *,
    slug: str,
    user_id: uuid.UUID,
    payload: CredentialPayload,
    label: str | None = None,
) -> ConnectorVaultEntry:
    """Seal ``payload`` and upsert ``slug`` keyed row for dashboard ``user_id``."""

    cipher = build_connector_vault_cipher(get_settings())
    token = cipher.encrypt(json.dumps(payload.model_dump(mode="json")).encode("utf-8"))
    enc_blob = token.decode("ascii")

    cleaned_slug = slug.strip().lower()
    result = await db.execute(select(ConnectorVaultEntry).where(ConnectorVaultEntry.slug == cleaned_slug))
    existing = result.scalar_one_or_none()
    if existing is None:
        row = ConnectorVaultEntry(
            slug=cleaned_slug,
            credential_kind=payload.kind,
            encrypted_payload=enc_blob,
            dashboard_user_id=user_id,
            label=(label.strip()[:256] if isinstance(label, str) and label.strip() else None),
        )
        db.add(row)
        await db.commit()
        await db.refresh(row)
        logger.info(
            "connector.vault_inserted",
            agent_id=str(user_id),
            swarm_id=cleaned_slug,
            task_id="vault-upsert",
        )
        return row

    existing.credential_kind = payload.kind
    existing.encrypted_payload = enc_blob
    existing.dashboard_user_id = user_id
    if isinstance(label, str) and label.strip():
        existing.label = label.strip()[:256]
    await db.commit()
    await db.refresh(existing)
    logger.info(
        "connector.vault_updated",
        agent_id=str(user_id),
        swarm_id=cleaned_slug,
        task_id="vault-upsert",
    )
    return existing


async def vault_load_envelope(
    db: AsyncSession,
    *,
    slug: str,
    user_id: uuid.UUID,
) -> ConnectorAuthEnvelope | None:
    """Decrypt connector row when ``dashboard_user_id`` matches."""

    cleaned = slug.strip().lower()
    result = await db.execute(select(ConnectorVaultEntry).where(ConnectorVaultEntry.slug == cleaned))
    row = result.scalar_one_or_none()
    if row is None or row.dashboard_user_id != user_id:
        return None
    cipher = build_connector_vault_cipher(get_settings())
    try:
        raw = cipher.decrypt(row.encrypted_payload.encode("ascii"))
    except InvalidToken as exc:
        logger.warning(
            "connector.vault_decrypt_failed",
            agent_id=str(user_id),
            swarm_id=cleaned,
            task_id="vault-load",
            error=str(exc),
        )
        return None
    data: dict[str, Any] = json.loads(raw.decode("utf-8"))
    payload = CredentialPayload.model_validate(data)
    return payload.to_envelope()


def seal_dynamic_connector_blob(data: dict[str, Any], *, settings: Settings | None = None) -> str:
    """Encrypt arbitrary JSON blobs for dynamic connector rows (AES-Fernet).

    Separate from vault row upserts so operators can persist org-scoped MCP secrets without
    clashing ``connector_vault_entries.slug`` cardinality.

    Args:
        data: JSON-serialisable dict (validated upstream); never logged by callers.

    Returns:
        ASCII ciphertext suitable for :class:`~app.models.dynamic_connector.DynamicConnector.secrets_cipher`.
    """

    cipher = build_connector_vault_cipher(settings if settings is not None else get_settings())
    token = cipher.encrypt(json.dumps(data, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    return token.decode("ascii")


def unseal_dynamic_connector_blob(blob: str, *, settings: Settings | None = None) -> dict[str, Any]:
    """Decrypt operator connector blobs stored beside dynamic connector manifests."""

    cipher = build_connector_vault_cipher(settings if settings is not None else get_settings())
    raw = cipher.decrypt(blob.strip().encode("ascii"))
    return json.loads(raw.decode("utf-8"))


async def vault_delete(db: AsyncSession, *, slug: str, user_id: uuid.UUID) -> bool:
    """Delete vault row scoped to dashboard user."""

    cleaned = slug.strip().lower()
    result = await db.execute(
        select(ConnectorVaultEntry).where(
            ConnectorVaultEntry.slug == cleaned,
            ConnectorVaultEntry.dashboard_user_id == user_id,
        )
    )
    row = result.scalar_one_or_none()
    if row is None:
        return False
    await db.delete(row)
    await db.commit()
    return True


__all__ = [
    "CredentialPayload",
    "build_connector_vault_cipher",
    "seal_dynamic_connector_blob",
    "unseal_dynamic_connector_blob",
    "vault_delete",
    "vault_load_envelope",
    "vault_upsert_credential",
]
