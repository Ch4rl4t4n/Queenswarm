"""Unit tests for middleware 429 response contract."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock

import pytest
from redis.exceptions import RedisError
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.presentation.api.middleware import rate_limit as rate_limit_middleware
from app.presentation.api.middleware.rate_limit import _rate_limited_response, _retry_after_headers, RateLimitMiddleware


def _request(
    *,
    path: str,
    method: str = "GET",
    client_host: str = "203.0.113.10",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> Request:
    """Build minimal HTTP request for middleware dispatch testing."""

    scope: dict[str, object] = {
        "type": "http",
        "asgi": {"spec_version": "2.3", "version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "path": path,
        "raw_path": path.encode("utf-8"),
        "root_path": "",
        "scheme": "https",
        "query_string": b"",
        "headers": headers or [],
        "state": {},
        "client": (client_host, 44321),
    }
    return Request(scope)


def test_retry_after_headers_when_window_fractional_rounds_down_with_floor_one() -> None:
    """Retry-After header is always integer seconds and at least one."""

    assert _retry_after_headers(0.25) == {"Retry-After": "1"}
    assert _retry_after_headers(5.9) == {"Retry-After": "5"}


def test_rate_limited_response_when_built_includes_retry_after_and_detail() -> None:
    """Standardized response carries both JSON detail and Retry-After."""

    response = _rate_limited_response("Rate limit exceeded. Retry later.", window_sec=12.0)
    assert response.status_code == 429
    assert response.headers.get("Retry-After") == "12"
    assert b"Rate limit exceeded. Retry later." in response.body


@pytest.mark.asyncio
async def test_rate_limit_middleware_when_global_limit_blocked_sets_retry_after_max_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Global limiter should emit Retry-After based on burst/sustain max window."""

    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_burst_window_sec", 2.0)
    monkeypatch.setattr(settings, "rate_limit_sustain_window_sec", 15.0)
    monkeypatch.setattr(
        rate_limit_middleware,
        "sliding_window_reserve",
        AsyncMock(side_effect=[False, True]),
    )

    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)
    request = _request(path="/api/v1/workflows")

    async def call_next(_: Request) -> Response:
        return Response(status_code=200)

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 429
    assert response.headers.get("Retry-After") == "15"


@pytest.mark.asyncio
async def test_rate_limit_middleware_when_agent_run_limited_sets_agent_window_retry_after(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Agent run limiter should use dedicated run window in Retry-After."""

    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_agent_run_window_sec", 42.0)
    monkeypatch.setattr(
        rate_limit_middleware,
        "sliding_window_reserve",
        AsyncMock(side_effect=[True, True, False]),
    )

    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)
    request = _request(path="/api/v1/agents/bee-1/run", method="POST")

    async def call_next(_: Request) -> Response:
        return Response(status_code=200)

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 429
    assert response.headers.get("Retry-After") == "42"


@pytest.mark.asyncio
async def test_rate_limit_middleware_when_task_create_limited_sets_task_window_retry_after(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Task creation limiter should use dedicated create window in Retry-After."""

    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_task_create_window_sec", 33.0)
    monkeypatch.setattr(
        rate_limit_middleware,
        "sliding_window_reserve",
        AsyncMock(side_effect=[True, True, False]),
    )

    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)
    request = _request(path="/api/v1/tasks", method="POST")

    async def call_next(_: Request) -> Response:
        return Response(status_code=200)

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 429
    assert response.headers.get("Retry-After") == "33"


@pytest.mark.asyncio
async def test_rate_limit_middleware_when_user_endpoint_limited_sets_user_window_retry_after(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Authenticated user limiter emits Retry-After using user windows."""

    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_user_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_user_sustain_window_sec", 22.0)
    monkeypatch.setattr(settings, "rate_limit_user_endpoint_window_sec", 45.0)
    monkeypatch.setattr(
        rate_limit_middleware,
        "decode_jwt_optional_typ",
        lambda _token, verify_exp=False: {"sub": "dash:00000000-0000-4000-8000-000000000001"},
    )
    monkeypatch.setattr(
        rate_limit_middleware,
        "sliding_window_reserve",
        AsyncMock(side_effect=[True, False]),
    )

    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)
    request = _request(path="/api/v1/agents", method="GET")
    request.scope["headers"] = [(b"authorization", b"Bearer test-token")]

    async def call_next(_: Request) -> Response:
        return Response(status_code=200)

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 429
    assert response.headers.get("Retry-After") == "45"


@pytest.mark.asyncio
async def test_rate_limit_middleware_when_authenticated_skips_peer_limits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Bearer-authenticated dashboard traffic uses user limits only (no IP burst/sustain)."""

    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_user_enabled", True)
    reserve = AsyncMock(return_value=True)
    monkeypatch.setattr(rate_limit_middleware, "sliding_window_reserve", reserve)
    monkeypatch.setattr(
        rate_limit_middleware,
        "decode_jwt_optional_typ",
        lambda _token, verify_exp=False: {"sub": "dash:00000000-0000-4000-8000-000000000001"},
    )

    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)
    request = _request(path="/api/v1/agents", method="GET")
    request.scope["headers"] = [(b"authorization", b"Bearer test-token")]

    async def call_next(_: Request) -> Response:
        return Response(status_code=200)

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200
    assert reserve.call_count == 2


@pytest.mark.asyncio
async def test_rate_limit_middleware_when_redis_fails_and_production_mode_blocks_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Production hardening must fail closed when Redis limiter is unavailable."""

    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "production_security_mode", True)

    async def raise_redis(*args: object, **kwargs: object) -> bool:  # noqa: ARG002
        raise RedisError("redis unavailable")

    monkeypatch.setattr(rate_limit_middleware, "sliding_window_reserve", raise_redis)

    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)
    request = _request(path="/api/v1/workflows")

    async def call_next(_: Request) -> Response:
        return Response(status_code=200)

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 503
    assert response.headers.get("Retry-After") == "60"


@pytest.mark.asyncio
async def test_rate_limit_middleware_skips_peer_limits_for_internal_relay(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Next.js proxy traffic from Docker must not share one public IP burst bucket."""

    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "production_security_mode", True)
    reserve = AsyncMock(return_value=True)
    monkeypatch.setattr(rate_limit_middleware, "sliding_window_reserve", reserve)

    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)
    request = _request(path="/api/v1/dashboard/cockpit", client_host="172.18.0.10")

    async def call_next(_: Request) -> Response:
        return Response(status_code=200)

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200
    assert not any(
        call.args[0].endswith(":burst:172.18.0.10") or call.args[0].endswith(":sustain:172.18.0.10")
        for call in reserve.await_args_list
    )


@pytest.mark.asyncio
async def test_rate_limit_middleware_skips_peer_limits_when_bearer_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Authenticated dashboard traffic uses per-token buckets, not shared client IP."""

    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "production_security_mode", True)
    reserve = AsyncMock(return_value=True)
    monkeypatch.setattr(rate_limit_middleware, "sliding_window_reserve", reserve)

    middleware = RateLimitMiddleware(app=lambda scope, receive, send: None)
    request = _request(
        path="/api/v1/auth/me",
        headers=[(b"authorization", b"Bearer not-a-valid-jwt-but-present")],
    )

    async def call_next(_: Request) -> Response:
        return Response(status_code=200)

    response = await middleware.dispatch(request, call_next)
    assert response.status_code == 200
    assert not any(":burst:" in call.args[0] for call in reserve.await_args_list)
