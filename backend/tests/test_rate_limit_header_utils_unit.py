"""Unit tests for shared Retry-After header normalization."""

from __future__ import annotations

from app.common.http.rate_limit import rate_limited_http_exception, retry_after_header, retry_after_seconds


def test_retry_after_seconds_has_floor_of_one() -> None:
    """Sub-second windows still produce at least 1 second backoff."""

    assert retry_after_seconds(0.1) == 1


def test_retry_after_seconds_truncates_fractional_seconds() -> None:
    """Window normalization should stay deterministic for integer headers."""

    assert retry_after_seconds(9.8) == 9


def test_retry_after_header_formats_seconds_as_string() -> None:
    """Header payload is ready for direct HTTP response usage."""

    assert retry_after_header(15.4) == {"Retry-After": "15"}


def test_rate_limited_http_exception_uses_retry_after_header() -> None:
    """Shared exception helper should keep payload and retry header in sync."""

    exc = rate_limited_http_exception("Too many requests.", window_sec=21.9)
    assert exc.status_code == 429
    assert exc.detail == "Too many requests."
    assert exc.headers == {"Retry-After": "21"}


def test_rate_limited_http_exception_allows_structured_detail_payload() -> None:
    """Shared helper should support dict payloads for API error contracts."""

    payload = {"code": "budget_exceeded", "detail": "Budget cap reached."}
    exc = rate_limited_http_exception(payload, window_sec=30.0)
    assert exc.status_code == 429
    assert exc.detail == payload
    assert exc.headers == {"Retry-After": "30"}
