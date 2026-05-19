"""Dashboard-stored Stripe secrets with env fallback (encrypted Postgres vault)."""

from __future__ import annotations

from cryptography.fernet import InvalidToken
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.symmetric_fernet import hive_fernet
from app.infrastructure.persistence.models.hive_stripe_secret import HiveStripeSecret

logger = get_logger(__name__)

_STRIPE_ROW_ID = 1
_cache: dict[str, str] = {}


def mask_stripe_material(raw: str) -> str:
    """Return last-four mask for operator UI."""

    trimmed = raw.strip()
    if len(trimmed) < 4:
        return "••••••••"
    return "••••••••" + trimmed[-4:]


def validate_stripe_secret_key(plaintext: str) -> str:
    """Normalize and validate Stripe secret or restricted key."""

    cleaned = plaintext.strip()
    if not (cleaned.startswith("sk_") or cleaned.startswith("rk_")):
        msg = "Stripe secret key must start with sk_ or rk_."
        raise ValueError(msg)
    if len(cleaned) < 20:
        msg = "Stripe secret key is too short."
        raise ValueError(msg)
    return cleaned


def validate_stripe_webhook_secret(plaintext: str) -> str:
    """Normalize and validate Stripe webhook signing secret."""

    cleaned = plaintext.strip()
    if not cleaned.startswith("whsec_"):
        msg = "Stripe webhook secret must start with whsec_."
        raise ValueError(msg)
    if len(cleaned) < 20:
        msg = "Stripe webhook secret is too short."
        raise ValueError(msg)
    return cleaned


def _decrypt_field(ciphertext: str | None, *, field: str) -> str | None:
    if not ciphertext:
        return None
    try:
        return hive_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8").strip()
    except (InvalidToken, ValueError, UnicodeError) as exc:
        logger.warning(
            "stripe_runtime_credentials.decrypt_failed",
            agent_id="hive_config",
            swarm_id="",
            task_id="",
            field=field,
            error=str(exc),
        )
        return None


async def refresh_stripe_secret_cache(session: AsyncSession) -> None:
    """Load ciphertext row from Postgres into the in-memory cache."""

    global _cache
    row = await session.get(HiveStripeSecret, _STRIPE_ROW_ID)
    loaded: dict[str, str] = {}
    if row is not None:
        secret = _decrypt_field(row.secret_key_ciphertext, field="secret_key")
        webhook = _decrypt_field(row.webhook_secret_ciphertext, field="webhook_secret")
        if secret:
            loaded["secret_key"] = secret
        if webhook:
            loaded["webhook_secret"] = webhook
    _cache = loaded


def stripe_effective_secret_key() -> str:
    """Return configured Stripe secret key (vault overrides env)."""

    cached = (_cache.get("secret_key") or "").strip()
    if cached:
        return cached
    return (settings.stripe_secret_key or "").strip()


def stripe_effective_webhook_secret() -> str:
    """Return configured Stripe webhook secret (vault overrides env)."""

    cached = (_cache.get("webhook_secret") or "").strip()
    if cached:
        return cached
    return (settings.stripe_webhook_secret or "").strip()


def stripe_secret_key_source() -> str:
    """Return ``vault``, ``env``, or ``none`` for operator diagnostics."""

    if (_cache.get("secret_key") or "").strip():
        return "vault"
    if (settings.stripe_secret_key or "").strip():
        return "env"
    return "none"


def stripe_webhook_secret_source() -> str:
    """Return ``vault``, ``env``, or ``none`` for webhook secret origin."""

    if (_cache.get("webhook_secret") or "").strip():
        return "vault"
    if (settings.stripe_webhook_secret or "").strip():
        return "env"
    return "none"


async def _ensure_row(session: AsyncSession) -> HiveStripeSecret:
    row = await session.get(HiveStripeSecret, _STRIPE_ROW_ID)
    if row is None:
        row = HiveStripeSecret(id=_STRIPE_ROW_ID)
        session.add(row)
        await session.flush()
    return row


async def persist_stripe_secrets(
    session: AsyncSession,
    *,
    secret_key: str | None = None,
    webhook_secret: str | None = None,
    clear_secret_key: bool = False,
    clear_webhook_secret: bool = False,
) -> None:
    """Encrypt and upsert Stripe secrets, then refresh the in-memory cache."""

    row = await _ensure_row(session)
    fernet = hive_fernet()

    if clear_secret_key:
        row.secret_key_ciphertext = None
        _cache.pop("secret_key", None)
    elif secret_key is not None:
        normalized = validate_stripe_secret_key(secret_key)
        row.secret_key_ciphertext = fernet.encrypt(normalized.encode("utf-8")).decode("utf-8")
        _cache["secret_key"] = normalized

    if clear_webhook_secret:
        row.webhook_secret_ciphertext = None
        _cache.pop("webhook_secret", None)
    elif webhook_secret is not None:
        normalized = validate_stripe_webhook_secret(webhook_secret)
        row.webhook_secret_ciphertext = fernet.encrypt(normalized.encode("utf-8")).decode("utf-8")
        _cache["webhook_secret"] = normalized

    await session.flush()
    logger.info(
        "stripe_runtime_credentials.persisted",
        agent_id="hive_config",
        swarm_id="",
        task_id="",
        secret_key_updated=secret_key is not None or clear_secret_key,
        webhook_secret_updated=webhook_secret is not None or clear_webhook_secret,
    )


async def clear_stripe_vault(session: AsyncSession) -> None:
    """Remove vault material and fall back to env-based settings."""

    row = await session.get(HiveStripeSecret, _STRIPE_ROW_ID)
    if row is not None:
        await session.delete(row)
    await session.flush()
    global _cache
    _cache = {}
    logger.info(
        "stripe_runtime_credentials.cleared",
        agent_id="hive_config",
        swarm_id="",
        task_id="",
    )


__all__ = [
    "clear_stripe_vault",
    "mask_stripe_material",
    "persist_stripe_secrets",
    "refresh_stripe_secret_cache",
    "stripe_effective_secret_key",
    "stripe_effective_webhook_secret",
    "stripe_secret_key_source",
    "stripe_webhook_secret_source",
    "validate_stripe_secret_key",
    "validate_stripe_webhook_secret",
]
