"""Unit tests for external pull-feed API key resolution."""

from __future__ import annotations

from starlette.requests import Request

from app.presentation.api.external_api_key import extract_external_api_key


def _request(*, headers: list[tuple[bytes, bytes]] | None = None) -> Request:
    scope: dict[str, object] = {
        "type": "http",
        "asgi": {"spec_version": "2.3", "version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "path": "/api/v1/external/results",
        "raw_path": b"/api/v1/external/results",
        "root_path": "",
        "scheme": "https",
        "query_string": b"",
        "headers": headers or [],
        "state": {},
        "client": ("203.0.113.10", 44321),
    }
    return Request(scope)


def test_extract_external_api_key_prefers_bearer_over_query() -> None:
    request = _request(headers=[(b"authorization", b"Bearer qs_kw_bearer")])
    resolved = extract_external_api_key(request, query_api_key="qs_kw_query")
    assert resolved == ("qs_kw_bearer", "bearer")


def test_extract_external_api_key_accepts_x_api_key_header() -> None:
    request = _request()
    resolved = extract_external_api_key(request, header_api_key="qs_kw_header")
    assert resolved == ("qs_kw_header", "x-api-key")


def test_extract_external_api_key_falls_back_to_query() -> None:
    request = _request()
    resolved = extract_external_api_key(request, query_api_key="qs_kw_legacy")
    assert resolved == ("qs_kw_legacy", "query")


def test_extract_external_api_key_when_missing_returns_none() -> None:
    request = _request()
    assert extract_external_api_key(request) is None
