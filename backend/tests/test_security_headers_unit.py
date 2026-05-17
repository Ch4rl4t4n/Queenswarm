"""Unit tests for shared HTTP security header helpers."""

from __future__ import annotations

from starlette.responses import Response

from app.common.http.security_headers import apply_no_store_cache_headers, no_store_cache_headers


def test_apply_no_store_cache_headers_sets_expected_directives() -> None:
    """No-store helper should set cache prevention headers consistently."""

    response = Response()
    apply_no_store_cache_headers(response)

    assert response.headers.get("Cache-Control") == "no-store"
    assert response.headers.get("Pragma") == "no-cache"
    assert response.headers.get("Expires") == "0"


def test_no_store_cache_headers_returns_expected_mapping() -> None:
    """Header helper should provide deterministic no-store mapping."""

    headers = no_store_cache_headers()
    assert headers == {
        "Cache-Control": "no-store",
        "Pragma": "no-cache",
        "Expires": "0",
    }
