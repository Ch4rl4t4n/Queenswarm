"""Resolve dashboard API keys from Authorization, X-Api-Key, or legacy query."""

from __future__ import annotations

from starlette.requests import Request


def extract_external_api_key(
    request: Request,
    *,
    query_api_key: str | None = None,
    header_api_key: str | None = None,
) -> tuple[str, str] | None:
    """Return ``(raw_key, source)`` where source is ``bearer``, ``x-api-key``, or ``query``.

    Priority: ``Authorization: Bearer`` → ``X-Api-Key`` → ``?api_key=`` (deprecated).
    """

    auth_header = request.headers.get("authorization", "").strip()
    if auth_header.lower().startswith("bearer "):
        bearer = auth_header[7:].strip()
        if bearer:
            return bearer, "bearer"

    if header_api_key is not None and header_api_key.strip():
        return header_api_key.strip(), "x-api-key"

    if query_api_key is not None and query_api_key.strip():
        return query_api_key.strip(), "query"

    return None
