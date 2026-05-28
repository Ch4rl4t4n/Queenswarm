"""Structured API error payload helpers for operator routes."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status


def api_error(
    *,
    status_code: int,
    code: str,
    message: str,
    details: Any | None = None,
) -> HTTPException:
    """Build a consistent HTTPException detail payload.

    Args:
        status_code: HTTP status code returned to the caller.
        code: Stable machine-readable error code.
        message: Human-readable message suitable for UI display.
        details: Optional structured context for troubleshooting.

    Returns:
        HTTPException: FastAPI exception with normalized detail schema.
    """

    payload: dict[str, Any] = {"code": code.strip(), "message": message}
    if details is not None:
        payload["details"] = details
    return HTTPException(status_code=status_code, detail=payload)


def forbidden_error(*, code: str, message: str, details: Any | None = None) -> HTTPException:
    """Build a normalized 403 error payload."""

    return api_error(status_code=status.HTTP_403_FORBIDDEN, code=code, message=message, details=details)


def unprocessable_error(*, code: str, message: str, details: Any | None = None) -> HTTPException:
    """Build a normalized 422 error payload."""

    return api_error(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, code=code, message=message, details=details)


def bad_request_error(*, code: str, message: str, details: Any | None = None) -> HTTPException:
    """Build a normalized 400 error payload."""

    return api_error(status_code=status.HTTP_400_BAD_REQUEST, code=code, message=message, details=details)

