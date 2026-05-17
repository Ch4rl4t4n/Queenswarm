"""Unit tests for OAuth callback peer-IP resolution policy."""

from __future__ import annotations

from starlette.requests import Request

from app.core.config import settings
from app.presentation.api.routers.oauth_consent import _callback_client_host


def _request(
    *,
    headers: list[tuple[bytes, bytes]],
    client: tuple[str, int] | None = ("10.1.1.5", 44321),
) -> Request:
    scope: dict[str, object] = {
        "type": "http",
        "asgi": {"spec_version": "2.3", "version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "path": "/api/v1/oauth/callback",
        "raw_path": b"/api/v1/oauth/callback",
        "root_path": "",
        "scheme": "https",
        "query_string": b"",
        "headers": headers,
        "state": {},
    }
    if client is not None:
        scope["client"] = client
    return Request(scope)


def test_oauth_callback_host_uses_xff_chain_with_trusted_hops(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_trust_forwarded_headers", True)
    monkeypatch.setattr(settings, "trusted_proxy_hops", 2)

    req = _request(headers=[(b"x-forwarded-for", b"203.0.113.9, 10.0.0.2, 10.0.0.3")])
    assert _callback_client_host(req) == "203.0.113.9"


def test_oauth_callback_host_uses_x_real_ip_when_xff_missing(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_trust_forwarded_headers", True)
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)

    req = _request(headers=[(b"x-real-ip", b"198.51.100.11")])
    assert _callback_client_host(req) == "198.51.100.11"


def test_oauth_callback_host_ignores_forwarded_headers_when_trust_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "rate_limit_trust_forwarded_headers", False)

    req = _request(
        headers=[(b"x-forwarded-for", b"203.0.113.9"), (b"x-real-ip", b"198.51.100.11")],
        client=("192.0.2.70", 50123),
    )
    assert _callback_client_host(req) == "192.0.2.70"
