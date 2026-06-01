"""Resolve Tavily/Serper keys from operator vault with env fallback."""

from __future__ import annotations

import os
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.operator_external_api_crypto import decrypt_credentials_blob
from app.infrastructure.persistence.models.operator_external_api import OperatorExternalApi

ResearchProvider = Literal["tavily", "serper"]

_RESEARCH_LABEL = "Research search"
_ENV_BY_PROVIDER: dict[ResearchProvider, str] = {
    "tavily": "TAVILY_API_KEY",
    "serper": "SERPER_API_KEY",
}


def _env_key(provider: ResearchProvider) -> str:
    return os.getenv(_ENV_BY_PROVIDER[provider], "").strip()


def _extract_api_key(credentials: dict[str, object]) -> str:
    for field in ("api_key", "bearer_token", "key"):
        raw = credentials.get(field)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return ""


async def resolve_research_keys(session: AsyncSession) -> dict[str, str]:
    """Load research search keys — vault rows override env when present."""

    keys: dict[str, str] = {}
    for provider in _ENV_BY_PROVIDER:
        env_val = _env_key(provider)  # type: ignore[arg-type]
        if env_val:
            keys[provider] = env_val

    stmt = (
        select(OperatorExternalApi)
        .where(OperatorExternalApi.provider.in_(tuple(_ENV_BY_PROVIDER.keys())))
        .where(OperatorExternalApi.is_active.is_(True))
        .order_by(OperatorExternalApi.updated_at.desc())
    )
    rows = list((await session.scalars(stmt)).all())
    for row in rows:
        provider = row.provider
        if provider not in _ENV_BY_PROVIDER:
            continue
        try:
            creds = decrypt_credentials_blob(row.ciphertext)
        except (ValueError, UnicodeError):
            continue
        if not isinstance(creds, dict):
            continue
        api_key = _extract_api_key(creds)
        if api_key:
            keys[provider] = api_key

    return keys


async def research_key_status(session: AsyncSession) -> dict[str, dict[str, object]]:
    """Masked configuration status for settings UI."""

    resolved = await resolve_research_keys(session)
    out: dict[str, dict[str, object]] = {}
    for provider in _ENV_BY_PROVIDER:
        secret = resolved.get(provider, "")
        out[provider] = {
            "configured": bool(secret),
            "masked": _mask_secret(secret) if secret else None,
        }
    return out


def _mask_secret(secret: str) -> str:
    trimmed = secret.strip()
    if len(trimmed) < 4:
        return "••••"
    return f"••••{trimmed[-4:]}"


__all__ = [
    "ResearchProvider",
    "_RESEARCH_LABEL",
    "research_key_status",
    "resolve_research_keys",
]
