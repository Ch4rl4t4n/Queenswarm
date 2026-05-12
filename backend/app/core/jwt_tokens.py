"""HS256 swarm + dashboard JWT helpers (Bee-Hive API + Neon cockpit operators)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt

from app.core.config import settings

_DASHBOARD_SUBJECT_PREFIX = "dash:"


def create_access_token(
    *,
    subject: str,
    expires_minutes: int | None = None,
    scope: str | None = None,
) -> tuple[str, int]:
    """Mint OAuth-style swarm operator tokens surfaced by ``POST /auth/token``.

    Args:
        subject: Stable ``sub`` claim (hive operator id or machine principal).
        expires_minutes: Optional override window; defaults to ``access_token_expire_minutes``.
        scope: Optional OAuth-style space-separated scopes embedded in the token.

    Returns:
        Tuple of ``(jwt, expires_in_seconds)``.
    """

    ttl_min = expires_minutes if expires_minutes is not None else settings.access_token_expire_minutes
    expire_at = datetime.now(tz=UTC) + timedelta(minutes=ttl_min)
    payload: dict[str, str | int] = {"sub": subject, "exp": int(expire_at.timestamp())}
    if scope is not None:
        cleaned = scope.strip()
        if cleaned:
            payload["scope"] = cleaned
    encoded = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    token = encoded.decode("utf-8") if isinstance(encoded, bytes) else str(encoded)
    return token, int(timedelta(minutes=ttl_min).total_seconds())


def _encode(payload: dict[str, Any]) -> str:
    """Encode a JWT using the configured hive_secret."""

    encoded = jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)
    return encoded.decode("utf-8") if isinstance(encoded, bytes) else str(encoded)


def dashboard_access_subject(user_id: uuid.UUID) -> str:
    """Prefix dashboard subjects so scanners can discriminate cockpit tokens."""

    return f"{_DASHBOARD_SUBJECT_PREFIX}{user_id}"


def parse_dashboard_user_subject(sub: str) -> uuid.UUID | None:
    """Parse ``dash:<uuid>`` (or legacy bare UUID strings) emitted by cockpit flows."""

    cleaned = sub.strip()
    lowered = cleaned.removeprefix(_DASHBOARD_SUBJECT_PREFIX).strip()
    try:
        return uuid.UUID(lowered)
    except ValueError:
        return None


def decode_jwt_optional_typ(raw_token: str) -> dict[str, Any]:
    """Decode JWT using the hive HS256 secret and return all registered claims."""

    return jwt.decode(
        raw_token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"verify_aud": False},
    )


def create_dashboard_access_token(
    *,
    user_id: uuid.UUID,
    email: str,
    scopes: str,
) -> tuple[str, int]:
    """Mint Neon dashboard access tokens routed through ``/auth/login``.

    Args:
        user_id: Primary key for ``dashboard_users``.
        email: Canonical operator email surfaced to clients.
        scopes: Space-separated scope string embedded for UI feature gating.

    Returns:
        ``(jwt, ttl_seconds)``
    """

    ttl_min = settings.access_token_expire_minutes
    expire_at = datetime.now(tz=UTC) + timedelta(minutes=ttl_min)
    payload: dict[str, Any] = {
        "sub": dashboard_access_subject(user_id),
        "email": email,
        "scope": scopes,
        "typ": "dashboard_access",
        "exp": int(expire_at.timestamp()),
    }
    token = _encode(payload)
    return token, int(timedelta(minutes=ttl_min).total_seconds())


def create_pre_2fa_token(*, user_id: uuid.UUID, email: str) -> tuple[str, int]:
    """Return a lightweight JWT bridging password auth and successful TOTP."""

    ttl_min = 30
    expire_at = datetime.now(tz=UTC) + timedelta(minutes=ttl_min)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "email": email,
        "typ": "pre_2fa",
        "exp": int(expire_at.timestamp()),
    }
    token = _encode(payload)
    return token, int(timedelta(minutes=ttl_min).total_seconds())


__all__ = [
    "create_access_token",
    "create_dashboard_access_token",
    "create_pre_2fa_token",
    "dashboard_access_subject",
    "decode_jwt_optional_typ",
    "parse_dashboard_user_subject",
]
