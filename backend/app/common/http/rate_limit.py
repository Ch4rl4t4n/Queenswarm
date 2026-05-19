"""Shared helpers for HTTP throttling/backoff semantics."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from app.core.config import settings


def retry_after_seconds(window_sec: float) -> int:
    """Normalize a limiter window to integer Retry-After seconds."""

    return int(max(1, window_sec))


def retry_after_header(window_sec: float) -> dict[str, str]:
    """Build RFC-compatible Retry-After header payload."""

    return {"Retry-After": str(retry_after_seconds(window_sec))}


def rate_limited_http_exception(detail: Any, *, window_sec: float) -> HTTPException:
    """Return standardized 429 exception with Retry-After header."""

    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=detail,
        headers=retry_after_header(window_sec),
    )


def rate_limit_redis_fail_closed() -> bool:
    """Return True when Redis outages must block traffic instead of degrading open."""

    return settings.production_security_mode


def rate_limit_unavailable_http_exception(*, window_sec: float = 60.0) -> HTTPException:
    """Return standardized 503 when the Redis-backed limiter is unavailable."""

    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Rate limit service unavailable. Retry later.",
        headers=retry_after_header(window_sec),
    )
