"""Dashoard-stored LLM secrets: Fernet-encrypted in Postgres, cached + mirrored to process env."""

from __future__ import annotations

import os
from typing import Final

from cryptography.fernet import InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.symmetric_fernet import hive_fernet
from app.models.hive_llm_secret import HiveLlmSecret

logger = get_logger(__name__)

_ALLOWED: Final[frozenset[str]] = frozenset({"grok", "anthropic", "openai"})

_cache: dict[str, str] = {}


def get_cached_llm_key(provider: str) -> str | None:
    """Return plaintext override for ``provider`` if loaded into memory."""

    raw = _cache.get(provider)
    if raw is None:
        return None
    stripped = raw.strip()
    return stripped if stripped else None


def apply_llm_cache_to_environ() -> None:
    """Mirror effective credentials into ``os.environ`` for LiteLLM (this process only)."""

    g_v = get_cached_llm_key("grok")
    g_e = (settings.grok_api_key or "").strip()
    if g_v:
        os.environ["XAI_API_KEY"] = g_v
        os.environ["GROK_API_KEY"] = g_v
    elif g_e:
        os.environ["XAI_API_KEY"] = g_e
        os.environ.setdefault("GROK_API_KEY", g_e)
    else:
        os.environ.pop("XAI_API_KEY", None)
        os.environ.pop("GROK_API_KEY", None)

    a_v = get_cached_llm_key("anthropic")
    a_e = (settings.anthropic_api_key or "").strip()
    if a_v:
        os.environ["ANTHROPIC_API_KEY"] = a_v
    elif a_e:
        os.environ["ANTHROPIC_API_KEY"] = a_e
    else:
        os.environ.pop("ANTHROPIC_API_KEY", None)

    o_v = get_cached_llm_key("openai")
    o_e = (str(settings.openai_api_key).strip() if settings.openai_api_key else "")
    if o_v:
        os.environ["OPENAI_API_KEY"] = o_v
    elif o_e:
        os.environ["OPENAI_API_KEY"] = o_e
    else:
        os.environ.pop("OPENAI_API_KEY", None)


async def refresh_llm_secret_cache(session: AsyncSession) -> None:
    """Load ciphertext rows from Postgres into the in-memory cache."""

    global _cache
    stmt = select(HiveLlmSecret)
    rows = list((await session.scalars(stmt)).all())
    loaded: dict[str, str] = {}
    f = hive_fernet()
    for row in rows:
        try:
            loaded[row.provider] = f.decrypt(row.ciphertext.encode("utf-8")).decode("utf-8")
        except (InvalidToken, ValueError, UnicodeError) as exc:
            logger.warning(
                "llm_runtime_credentials.decrypt_failed",
                agent_id="hive_config",
                swarm_id="",
                task_id="",
                provider=row.provider,
                error=str(exc),
            )
    _cache = loaded
    apply_llm_cache_to_environ()


async def persist_llm_provider_secret(session: AsyncSession, *, provider: str, plaintext: str) -> None:
    """Encrypt and upsert a provider secret, then refresh env mirrors for this worker."""

    if provider not in _ALLOWED:
        msg = f"Unknown LLM provider bucket: {provider}"
        raise ValueError(msg)
    cleaned = plaintext.strip()
    if len(cleaned) < 12:
        msg = "API key too short."
        raise ValueError(msg)
    token = hive_fernet().encrypt(cleaned.encode("utf-8")).decode("utf-8")
    row = await session.get(HiveLlmSecret, provider)
    if row is None:
        session.add(HiveLlmSecret(provider=provider, ciphertext=token))
    else:
        row.ciphertext = token
    await session.flush()
    _cache[provider] = cleaned
    apply_llm_cache_to_environ()
    logger.info(
        "llm_runtime_credentials.provider_persisted",
        agent_id="hive_config",
        swarm_id="",
        task_id="",
        provider=provider,
    )


async def delete_llm_provider_secret(session: AsyncSession, *, provider: str) -> None:
    """Remove vault material for ``provider`` and fall back to env-based settings."""

    if provider not in _ALLOWED:
        msg = f"Unknown LLM provider bucket: {provider}"
        raise ValueError(msg)
    row = await session.get(HiveLlmSecret, provider)
    if row is not None:
        await session.delete(row)
    await session.flush()
    _cache.pop(provider, None)
    apply_llm_cache_to_environ()
    logger.info(
        "llm_runtime_credentials.provider_cleared",
        agent_id="hive_config",
        swarm_id="",
        task_id="",
        provider=provider,
    )


def provider_effective_grok() -> str:
    """Return non-empty Grok / xAI material when configured."""

    return (get_cached_llm_key("grok") or (settings.grok_api_key or "")).strip()


def provider_effective_anthropic() -> str:
    """Return non-empty Anthropic material when configured."""

    return (get_cached_llm_key("anthropic") or (settings.anthropic_api_key or "")).strip()


def provider_effective_openai() -> str:
    """Return non-empty OpenAI material when configured."""

    v = get_cached_llm_key("openai")
    if v:
        return v.strip()
    if settings.openai_api_key:
        return str(settings.openai_api_key).strip()
    return ""


__all__ = [
    "apply_llm_cache_to_environ",
    "delete_llm_provider_secret",
    "get_cached_llm_key",
    "persist_llm_provider_secret",
    "provider_effective_anthropic",
    "provider_effective_grok",
    "provider_effective_openai",
    "refresh_llm_secret_cache",
]
