"""Unit tests for rate-limit peer IP resolution behind reverse proxies."""

from __future__ import annotations

from starlette.requests import Request

from app.api.middleware.rate_limit import peer_ip_for_rate_limit


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


def test_peer_ip_prefers_x_forwarded_for_first_hop() -> None:
    """First address in ``X-Forwarded-For`` should win (public client)."""

    req = _request(
        headers=[(b"x-forwarded-for", b"203.0.113.10, 10.0.0.1")],
    )
    assert peer_ip_for_rate_limit(req) == "203.0.113.10"


def test_peer_ip_uses_x_real_ip_when_xff_absent() -> None:
    """Nginx often sends ``X-Real-IP`` alone."""

    req = _request(headers=[(b"x-real-ip", b"198.51.100.7")])
    assert peer_ip_for_rate_limit(req) == "198.51.100.7"


def test_peer_ip_falls_back_to_tcp_client() -> None:
    """Local dev / internal probes without proxy headers."""

    req = _request(headers=[], client=("192.0.2.44", 9999))
    assert peer_ip_for_rate_limit(req) == "192.0.2.44"


def test_peer_ip_unknown_without_client() -> None:
    """Edge ASGI stacks may omit ``client`` — degrade gracefully."""

    req = _request(headers=[], client=None)
    assert peer_ip_for_rate_limit(req) == "unknown"
