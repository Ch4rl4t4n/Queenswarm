"""Encode HS256 swarm access tokens (audited machine + operator callers)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from jose import jwt

from app.core.config import settings


def create_access_token(
    *,
    subject: str,
    expires_minutes: int | None = None,
    scope: str | None = None,
) -> tuple[str, int]:
    """Mint a JWT string plus ``expires_in`` seconds for OAuth-style responses.

    Args:
        subject: Stable ``sub`` claim (hive operator id or machine principal).
        expires_minutes: Optional override window; defaults to ``access_token_expire_minutes``.
        scope: Optional OAuth2-style space-separated scopes embedded in the token.

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
    if isinstance(encoded, bytes):
        token = encoded.decode("utf-8")
    else:
        token = str(encoded)
    return token, int(timedelta(minutes=ttl_min).total_seconds())


__all__ = ["create_access_token"]
