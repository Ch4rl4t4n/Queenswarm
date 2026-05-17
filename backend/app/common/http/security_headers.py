"""Shared security-related HTTP header helpers."""

from __future__ import annotations

from starlette.responses import Response


def no_store_cache_headers() -> dict[str, str]:
    """Return cache-busting headers for sensitive responses."""

    return {
        "Cache-Control": "no-store",
        "Pragma": "no-cache",
        "Expires": "0",
    }


def apply_no_store_cache_headers(response: Response) -> None:
    """Prevent token-bearing responses from being cached."""

    response.headers.update(no_store_cache_headers())
