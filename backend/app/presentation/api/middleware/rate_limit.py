"""Per-IP sliding-window rate limits backed by Redis (hive policy defaults)."""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
from typing import Annotated, Any, ClassVar

from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.common.http.rate_limit import (
    rate_limit_redis_fail_closed,
    rate_limit_unavailable_http_exception,
    retry_after_header,
)
from app.core.config import settings
from app.core.jwt_tokens import decode_jwt_optional_typ
from app.core.logging import get_logger
from app.core.metrics import observe_rate_limit_block
from app.core.redis_client import increment_minute_counter, sliding_window_reserve

logger = get_logger(__name__)

_RATE_KEY_PREFIX = "queenswarm:rl"


def _normalize_candidate_ip(raw: str) -> str:
    """Normalize candidate peer value into canonical key-safe label."""

    value = raw.strip().strip('"').strip("'")
    if not value:
        return "unknown"

    # IPv6-with-port often arrives as ``[2001:db8::1]:443``.
    if value.startswith("[") and "]" in value:
        value = value[1 : value.index("]")]
    # Some proxies emit ``198.51.100.10:443`` for IPv4 peers.
    elif value.count(":") == 1 and value.rsplit(":", 1)[1].isdigit():
        value = value.rsplit(":", 1)[0]

    try:
        return ipaddress.ip_address(value).compressed
    except ValueError:
        digest = hmac.new(
            settings.secret_key.encode("utf-8"),
            raw.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()[:24]
        return f"opaque-hmac:{digest}"


def _subject_rate_bucket(raw_subject: str) -> str:
    """Return deterministic non-plaintext bucket for authenticated principals."""

    digest = hmac.new(
        settings.secret_key.encode("utf-8"),
        raw_subject.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"hmac-sha256:{digest}"


def _extract_bearer_subject(request: Request) -> str | None:
    """Decode bearer token subject for optional authenticated user throttles."""

    raw = request.headers.get("authorization", "").strip()
    if not raw.lower().startswith("bearer "):
        return None
    token = raw[7:].strip()
    if not token:
        return None
    try:
        payload = decode_jwt_optional_typ(token)
    except Exception:  # noqa: BLE001 - limiter path must fail open on token parse errors
        return None
    subject = payload.get("sub")
    if not isinstance(subject, str):
        return None
    trimmed = subject.strip()
    return trimmed if trimmed else None


def _endpoint_rate_bucket(*, method: str, path: str) -> str:
    """Return canonical endpoint bucket label without leaking full route text."""

    normalized = f"{method.upper()}:{path.rstrip('/') or '/'}"
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()  # noqa: S324 - non-crypto bucket id only
    return f"sha1:{digest}"


def peer_ip_for_rate_limit(request: Request) -> str:
    """Resolve logical client IP for rate limits with explicit proxy trust controls.

    When forwarded headers are trusted, ``trusted_proxy_hops`` controls which IP is chosen
    from ``X-Forwarded-For`` by counting trusted proxies from the right side of the chain.
    For example, with ``trusted_proxy_hops=1`` and ``X-Forwarded-For: client, proxy``,
    the resolved peer is ``client``.

    Args:
        request: Incoming ASGI request.

    Returns:
        Best-effort peer label (never empty; ``unknown`` if no socket client).
    """

    if settings.rate_limit_trust_forwarded_headers:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            chain = [part.strip() for part in xff.split(",") if part.strip()]
            if chain:
                trusted_hops = max(1, int(settings.trusted_proxy_hops))
                client_index = max(0, len(chain) - trusted_hops - 1)
                return _normalize_candidate_ip(chain[client_index])
        xri = request.headers.get("x-real-ip")
        if xri:
            trimmed = xri.strip()
            if trimmed:
                return _normalize_candidate_ip(trimmed)
    client = request.client
    if client and isinstance(client.host, str):
        return _normalize_candidate_ip(client.host)
    return "unknown"


def _is_agent_run_post(path: str, method: str) -> bool:
    """Return ``True`` for ``POST …/agents/{id}/run`` style routes."""

    if method.upper() != "POST":
        return False
    parts = path.rstrip("/").split("/")
    if len(parts) < 2:
        return False
    return parts[-1] == "run" and "agents" in parts


def _is_api_task_create_post(path: str, method: str) -> bool:
    """Return ``True`` for backlog creation endpoints."""

    if method.upper() != "POST":
        return False
    return path.rstrip("/").endswith("/tasks")


def _retry_after_headers(window_sec: float) -> dict[str, str]:
    """Return HTTP header payload for predictable client backoff on 429."""

    return retry_after_header(window_sec)


def _rate_limited_response(detail: str, *, window_sec: float) -> JSONResponse:
    """Build standard 429 response payload with `Retry-After`."""

    return JSONResponse(
        status_code=429,
        content={"detail": detail},
        headers=_retry_after_headers(window_sec),
    )


def _rate_limit_unavailable_response(*, window_sec: float = 60.0) -> JSONResponse:
    """Build standard 503 when Redis limiter is down and fail-closed policy applies."""

    return JSONResponse(
        status_code=503,
        content={"detail": "Rate limit service unavailable. Retry later."},
        headers=_retry_after_headers(window_sec),
    )


def _redis_limiter_degraded_response(
    rl_log: Any,
    *,
    exc: RedisError,
    peer: str,
    event: str,
    window_sec: float = 60.0,
    **extra: object,
) -> JSONResponse | None:
    """Return 503 when fail-closed; otherwise log and allow the request through."""

    if rate_limit_redis_fail_closed():
        rl_log.error(event, error=str(exc), peer=peer, fail_closed=True, **extra)
        return _rate_limit_unavailable_response(window_sec=window_sec)
    rl_log.warning(event, error=str(exc), peer=peer, **extra)
    return None


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Burst + sustained windows per client IP (hive defaults: 10/s burst, 100/min sustain)."""

    EXEMPT_PATHS: ClassVar[frozenset[str]] = frozenset({
        "/",
        "/health",
        "/health/ready",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/v1/health",
        "/api/v1/billing/stripe/webhook",
        "/favicon.ico",
    })

    async def dispatch(self, request: Request, call_next) -> Response:  # noqa: ANN001
        """Short-circuit with 429 when both Redis-backed windows disagree."""

        if request.scope["type"] != "http":
            return await call_next(request)

        path = request.url.path
        norm = path.rstrip("/") or "/"
        if (
            path in self.EXEMPT_PATHS
            or norm in self.EXEMPT_PATHS
            or path.startswith("/static")
            or path.startswith("/api/docs")
            or path.startswith("/api/openapi")
        ):
            return await call_next(request)

        if not settings.rate_limit_enabled:
            return await call_next(request)

        ip_label = peer_ip_for_rate_limit(request)
        rl_log = logger.bind(agent_id="rate_limit_gate", swarm_id="", task_id="")

        try:
            burst_ok = await sliding_window_reserve(
                f"{_RATE_KEY_PREFIX}:burst:{ip_label}",
                limit=settings.rate_limit_burst_max,
                window_sec=settings.rate_limit_burst_window_sec,
            )
            sustain_ok = await sliding_window_reserve(
                f"{_RATE_KEY_PREFIX}:sustain:{ip_label}",
                limit=settings.rate_limit_sustain_max,
                window_sec=settings.rate_limit_sustain_window_sec,
            )
        except RedisError as exc:
            blocked = _redis_limiter_degraded_response(
                rl_log,
                exc=exc,
                peer=ip_label,
                event="rate_limit.redis_degraded_allowing",
            )
            if blocked is not None:
                return blocked
            return await call_next(request)

        if not burst_ok or not sustain_ok:
            observe_rate_limit_block(scope="global")
            try:
                await increment_minute_counter("rate_limit_blocks", ttl_sec=7200)
            except Exception:  # noqa: BLE001 - telemetry side path must never block request handling
                pass
            rl_log.info("rate_limit.blocked", peer=ip_label, path=path)
            return _rate_limited_response(
                "Rate limit exceeded. Retry later.",
                window_sec=max(settings.rate_limit_burst_window_sec, settings.rate_limit_sustain_window_sec),
            )

        if _is_agent_run_post(path, request.method):
            try:
                run_ok = await sliding_window_reserve(
                    f"{_RATE_KEY_PREFIX}:agent_run:{ip_label}",
                    limit=settings.rate_limit_agent_run_max,
                    window_sec=settings.rate_limit_agent_run_window_sec,
                )
            except RedisError as exc:
                blocked = _redis_limiter_degraded_response(
                    rl_log,
                    exc=exc,
                    peer=ip_label,
                    event="rate_limit.redis_degraded_allowing",
                    window_sec=settings.rate_limit_agent_run_window_sec,
                )
                if blocked is not None:
                    return blocked
                return await call_next(request)
            if not run_ok:
                observe_rate_limit_block(scope="agent_run")
                try:
                    await increment_minute_counter("rate_limit_blocks", ttl_sec=7200)
                except Exception:  # noqa: BLE001
                    pass
                rl_log.info("rate_limit.agent_run_blocked", peer=ip_label, path=path)
                return _rate_limited_response(
                    "Agent run rate limit exceeded. Retry later.",
                    window_sec=settings.rate_limit_agent_run_window_sec,
                )

        elif _is_api_task_create_post(path, request.method):
            try:
                task_ok = await sliding_window_reserve(
                    f"{_RATE_KEY_PREFIX}:tasks_create:{ip_label}",
                    limit=settings.rate_limit_task_create_max,
                    window_sec=settings.rate_limit_task_create_window_sec,
                )
            except RedisError as exc:
                blocked = _redis_limiter_degraded_response(
                    rl_log,
                    exc=exc,
                    peer=ip_label,
                    event="rate_limit.redis_degraded_allowing",
                    window_sec=settings.rate_limit_task_create_window_sec,
                )
                if blocked is not None:
                    return blocked
                return await call_next(request)
            if not task_ok:
                observe_rate_limit_block(scope="task_create")
                try:
                    await increment_minute_counter("rate_limit_blocks", ttl_sec=7200)
                except Exception:  # noqa: BLE001
                    pass
                rl_log.info("rate_limit.tasks_create_blocked", peer=ip_label, path=path)
                return _rate_limited_response(
                    "Task creation rate limit exceeded. Retry later.",
                    window_sec=settings.rate_limit_task_create_window_sec,
                )

        if settings.rate_limit_user_enabled or settings.production_security_mode:
            subject = _extract_bearer_subject(request)
            if subject:
                sub_bucket = _subject_rate_bucket(subject)
                endpoint_bucket = _endpoint_rate_bucket(method=request.method, path=path)
                try:
                    user_ok = await sliding_window_reserve(
                        f"{_RATE_KEY_PREFIX}:user:{sub_bucket}",
                        limit=settings.rate_limit_user_sustain_max,
                        window_sec=settings.rate_limit_user_sustain_window_sec,
                    )
                    endpoint_ok = await sliding_window_reserve(
                        f"{_RATE_KEY_PREFIX}:user_endpoint:{sub_bucket}:{endpoint_bucket}",
                        limit=settings.rate_limit_user_endpoint_max,
                        window_sec=settings.rate_limit_user_endpoint_window_sec,
                    )
                except RedisError as exc:
                    blocked = _redis_limiter_degraded_response(
                        rl_log,
                        exc=exc,
                        peer=ip_label,
                        event="rate_limit.user_redis_degraded_allowing",
                        subject=sub_bucket,
                        window_sec=max(
                            settings.rate_limit_user_sustain_window_sec,
                            settings.rate_limit_user_endpoint_window_sec,
                        ),
                    )
                    if blocked is not None:
                        return blocked
                    return await call_next(request)
                if not user_ok or not endpoint_ok:
                    observe_rate_limit_block(scope="user")
                    try:
                        await increment_minute_counter("rate_limit_blocks", ttl_sec=7200)
                    except Exception:  # noqa: BLE001
                        pass
                    rl_log.info(
                        "rate_limit.user_blocked",
                        peer=ip_label,
                        path=path,
                        subject=sub_bucket,
                    )
                    return _rate_limited_response(
                        "User rate limit exceeded. Retry later.",
                        window_sec=max(
                            settings.rate_limit_user_sustain_window_sec,
                            settings.rate_limit_user_endpoint_window_sec,
                        ),
                    )

        return await call_next(request)
