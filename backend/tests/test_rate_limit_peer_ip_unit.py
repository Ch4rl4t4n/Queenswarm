"""Unit tests for rate-limit peer IP resolution behind reverse proxies."""

from __future__ import annotations

from starlette.requests import Request

from app.core.config import settings
from app.presentation.api.middleware.rate_limit import peer_ip_for_rate_limit


def _request(
    *,
    headers: list[tuple[bytes, bytes]],
    client: tuple[str, int] | None = ("10.0.0.2", 12345),
) -> Request:
    """Build a minimal ASGI scope for ``Request`` construction."""

    scope: dict[str, object] = {
        "type": "http",
        "asgi": {"spec_version": "2.3", "version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "path": "/api/v1/tasks",
        "raw_path": b"/api/v1/tasks",
        "root_path": "",
        "scheme": "https",
        "query_string": b"",
        "headers": headers,
        "state": {},
    }
    if client is not None:
        scope["client"] = client
    return Request(scope)


def test_peer_ip_prefers_x_forwarded_for_first_hop(monkeypatch) -> None:
    """First address in ``X-Forwarded-For`` should win (public client)."""

    monkeypatch.setattr(settings, "rate_limit_trust_forwarded_headers", True)
    monkeypatch.setattr(settings, "trusted_proxy_hops", 1)
    req = _request(
        headers=[(b"x-forwarded-for", b"203.0.113.10, 10.0.0.1")],
    )
    assert peer_ip_for_rate_limit(req) == "203.0.113.10"


def test_peer_ip_uses_x_real_ip_when_xff_absent(monkeypatch) -> None:
    """Nginx often sends ``X-Real-IP`` alone."""

    monkeypatch.setattr(settings, "rate_limit_trust_forwarded_headers", True)
    req = _request(headers=[(b"x-real-ip", b"198.51.100.7")])
    assert peer_ip_for_rate_limit(req) == "198.51.100.7"


def test_peer_ip_uses_trusted_proxy_hops_from_xff_chain(monkeypatch) -> None:
    """Proxy hop count should pick the client left of trusted proxies."""

    monkeypatch.setattr(settings, "rate_limit_trust_forwarded_headers", True)
    monkeypatch.setattr(settings, "trusted_proxy_hops", 2)
    req = _request(headers=[(b"x-forwarded-for", b"198.51.100.1, 10.0.0.2, 10.0.0.3")])
    assert peer_ip_for_rate_limit(req) == "198.51.100.1"


def test_peer_ip_normalizes_ipv4_with_port(monkeypatch) -> None:
    """Proxy labels with host:port should normalize to bare IPv4."""

    monkeypatch.setattr(settings, "rate_limit_trust_forwarded_headers", True)
    req = _request(headers=[(b"x-forwarded-for", b"203.0.113.9:443, 10.0.0.1")])
    assert peer_ip_for_rate_limit(req) == "203.0.113.9"


def test_peer_ip_normalizes_bracket_ipv6_with_port(monkeypatch) -> None:
    """Bracketed IPv6 + port should resolve to canonical IPv6."""

    monkeypatch.setattr(settings, "rate_limit_trust_forwarded_headers", True)
    req = _request(headers=[(b"x-forwarded-for", b"[2001:db8::9]:443, 10.0.0.1")])
    assert peer_ip_for_rate_limit(req) == "2001:db8::9"


def test_peer_ip_hashes_invalid_forwarded_token(monkeypatch) -> None:
    """Untrusted token formats should be bucketed as opaque hashes."""

    monkeypatch.setattr(settings, "rate_limit_trust_forwarded_headers", True)
    req = _request(headers=[(b"x-forwarded-for", b"not-an-ip-token, 10.0.0.1")])
    resolved = peer_ip_for_rate_limit(req)
    assert resolved.startswith("opaque-hmac:")
    assert "not-an-ip-token" not in resolved


def test_peer_ip_ignores_forwarded_headers_when_trust_disabled(monkeypatch) -> None:
    """Spoofable forwarded headers must be ignored when trust is off."""

    monkeypatch.setattr(settings, "rate_limit_trust_forwarded_headers", False)
    req = _request(
        headers=[(b"x-forwarded-for", b"203.0.113.10, 10.0.0.1"), (b"x-real-ip", b"198.51.100.7")],
        client=("192.0.2.99", 4321),
    )
    assert peer_ip_for_rate_limit(req) == "192.0.2.99"


def test_peer_ip_falls_back_to_tcp_client(monkeypatch) -> None:
    """Local dev / internal probes without proxy headers."""

    monkeypatch.setattr(settings, "rate_limit_trust_forwarded_headers", True)
    req = _request(headers=[], client=("192.0.2.44", 9999))
    assert peer_ip_for_rate_limit(req) == "192.0.2.44"


def test_peer_ip_unknown_without_client(monkeypatch) -> None:
    """Edge ASGI stacks may omit ``client`` — degrade gracefully."""

    monkeypatch.setattr(settings, "rate_limit_trust_forwarded_headers", True)
    req = _request(headers=[], client=None)
    assert peer_ip_for_rate_limit(req) == "unknown"
