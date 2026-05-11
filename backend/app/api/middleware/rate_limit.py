"""Per-IP sliding-window rate limits backed by Redis (hive policy defaults)."""

from __future__ import annotations

from typing import ClassVar

from redis.exceptions import RedisError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.logging import get_logger
from app.core.redis_client import sliding_window_reserve

logger = get_logger(__name__)

_RATE_KEY_PREFIX = "queenswarm:rl"


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
        "/favicon.ico",
    })

    async def dispatch(self, request: Request, call_next) -> Response:  # noqa: ANN001
        """Short-circuit with 429 when both Redis-backed windows disagree."""

        if request.scope["type"] != "http":
            return await call_next(request)

        path = request.url.path
        if path in self.EXEMPT_PATHS or path.startswith("/static"):
            return await call_next(request)

        if not settings.rate_limit_enabled:
            return await call_next(request)

        client = request.client
        ip_label = client.host if client else "unknown"
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
            rl_log.warning("rate_limit.redis_degraded_allowing", error=str(exc), peer=ip_label)
            return await call_next(request)

        if not burst_ok or not sustain_ok:
            rl_log.info("rate_limit.blocked", peer=ip_label, path=path)
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Retry later."},
            )

        return await call_next(request)
