"""Create, validate, or revoke persisted dashboard Bearer API keys."""

from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt_tokens import dashboard_subject
from app.core.logging import get_logger
from app.models.dashboard_api_key import DashboardApiKey
from app.models.dashboard_user import DashboardUser
from app.services.dashboard_crypto import hash_dashboard_password, verify_dashboard_password

logger = get_logger(__name__)

API_KEY_PREFIX = "qs_kw_"


class DashboardApiKeyError(Exception):
    """Raised when an API credential operation cannot complete."""


def build_plaintext_api_key(key_id: uuid.UUID) -> str:
    """Return the single-use secret string persisted as a bcrypt hash."""

    return f"{API_KEY_PREFIX}{key_id.hex}.{secrets.token_urlsafe(40)}"


def parse_api_key_token(raw: str) -> tuple[uuid.UUID, str] | None:
    """Split a bearer credential into `(key_uuid, entropy_suffix)` or ``None``."""

    if not raw.startswith(API_KEY_PREFIX):
        return None
    rest = raw[len(API_KEY_PREFIX) :]
    dot = rest.find(".")
    if dot < 0:
        return None
    hex_part = rest[:dot]
    suffix = rest[dot + 1 :]
    if len(hex_part) != 32 or len(suffix) < 16:
        return None
    try:
        parsed_id = uuid.UUID(hex=hex_part)
    except ValueError:
        return None
    return parsed_id, suffix


async def resolve_api_key_principal(db: AsyncSession, bearer: str) -> str | None:
    """Map a ``qs_kw_`` Bearer token to a ``dash:user:<uuid>`` subject when valid."""

    parsed = parse_api_key_token(bearer.strip())
    if parsed is None:
        return None
    key_uuid, _ = parsed
    try:
        row = await db.get(DashboardApiKey, key_uuid)
    except SQLAlchemyError:
        logger.exception(
            "dashboard_api_key.lookup_failed",
            agent_id=str(key_uuid),
            swarm_id="",
            task_id="",
        )
        return None
    if row is None or row.revoked_at is not None:
        return None
    if not verify_dashboard_password(bearer.strip(), row.secret_hash):
        return None
    user = await db.get(DashboardUser, row.user_id)
    if user is None or not user.is_active:
        return None
    return dashboard_subject(user.id)


async def create_dashboard_api_key(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    label: str | None,
) -> tuple[DashboardApiKey, str]:
    """Persist a bcrypt-hashed credential and return the row plus plaintext once."""

    key_id = uuid.uuid4()
    plaintext = build_plaintext_api_key(key_id)
    hashed = hash_dashboard_password(plaintext)
    row = DashboardApiKey(id=key_id, user_id=user_id, label=(label.strip()[:160] if label else None), secret_hash=hashed)
    db.add(row)
    try:
        await db.flush()
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.exception(
            "dashboard_api_key.persist_failed",
            agent_id=str(user_id),
            swarm_id="",
            task_id="",
        )
        raise DashboardApiKeyError("Could not persist API key.") from exc
    return row, plaintext


async def list_dashboard_api_keys(db: AsyncSession, *, user_id: uuid.UUID) -> list[DashboardApiKey]:
    """Return credentials that belong to ``user_id`` (including revoked for audit)."""

    stmt = (
        select(DashboardApiKey)
        .where(DashboardApiKey.user_id == user_id)
        .order_by(DashboardApiKey.created_at.desc())
    )
    scal = await db.scalars(stmt)
    return list(scal.all())


async def revoke_dashboard_api_key(db: AsyncSession, *, user_id: uuid.UUID, key_id: uuid.UUID) -> bool:
    """Mark a key revoked; raises ``DashboardApiKeyError`` when mismatched."""

    row = await db.get(DashboardApiKey, key_id)
    if row is None:
        raise DashboardApiKeyError("Unknown credential.")
    if row.user_id != user_id:
        raise DashboardApiKeyError("Credential scoped to another operator.")
    if row.revoked_at is not None:
        return False
    row.revoked_at = datetime.now(tz=UTC)
    row.updated_at = datetime.now(tz=UTC)
    try:
        await db.flush()
    except SQLAlchemyError as exc:
        await db.rollback()
        raise DashboardApiKeyError("Could not revoke credential.") from exc
    logger.info(
        "dashboard_api_key.revoked",
        agent_id=str(key_id),
        swarm_id=str(user_id),
        task_id="",
    )
    return True
