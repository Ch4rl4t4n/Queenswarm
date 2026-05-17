"""Shared helpers for HTTP throttling/backoff semantics."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status


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
