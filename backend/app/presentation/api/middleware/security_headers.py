"""Global security header middleware for API hardening."""

from __future__ import annotations

from typing import ClassVar

from starlette import status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.common.http.security_headers import apply_no_store_cache_headers
from app.core.config import settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Apply no-store + defense-in-depth headers with optional strict production checks."""

    NO_STORE_PREFIXES: ClassVar[tuple[str, ...]] = (
        "/api/v1/auth",
        "/api/v1/oauth",
        "/api/v1/connectors/oauth",
    )
    NO_STORE_EXACT_PATHS: ClassVar[frozenset[str]] = frozenset()
    MUTATING_METHODS: ClassVar[frozenset[str]] = frozenset({"POST", "PUT", "PATCH", "DELETE"})

    @classmethod
    def _requires_no_store(cls, path: str) -> bool:
        if path in cls.NO_STORE_EXACT_PATHS:
            return True
        return any(path.startswith(prefix) for prefix in cls.NO_STORE_PREFIXES)

    @staticmethod
    def _normalize_origin(origin: str) -> str:
        return origin.rstrip("/").strip().lower()

    @classmethod
    def _is_origin_allowed(cls, origin: str) -> bool:
        allowed = {cls._normalize_origin(str(item)) for item in settings.cors_origins}
        return cls._normalize_origin(origin) in allowed

    @classmethod
    def _content_security_policy(cls) -> str:
        if settings.production_security_mode:
            return (
                "default-src 'self'; "
                "base-uri 'self'; "
                "frame-ancestors 'none'; "
                "form-action 'self'; "
                "img-src 'self' data: https:; "
                "font-src 'self' data:; "
                "style-src 'self' 'unsafe-inline'; "
                "script-src 'self' 'unsafe-inline'; "
                "connect-src 'self' https: wss:; "
                "object-src 'none'; "
                "upgrade-insecure-requests"
            )
        return (
            "default-src 'self'; "
            "base-uri 'self'; "
            "frame-ancestors 'none'; "
            "img-src 'self' data: https:; "
            "style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "connect-src 'self' https: http: ws: wss:; "
            "object-src 'none'"
        )

    @classmethod
    def _apply_security_headers(cls, response: Response) -> None:
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.headers.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        response.headers.setdefault("Content-Security-Policy", cls._content_security_policy())
        if settings.production_security_mode:
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains; preload")

    async def dispatch(self, request: Request, call_next) -> Response:  # noqa: ANN001
        if (
            settings.production_security_mode
            and request.scope.get("type") == "http"
            and request.method.upper() in self.MUTATING_METHODS
            and request.url.path.startswith("/api/v1/")
        ):
            origin = request.headers.get("origin")
            if origin and not self._is_origin_allowed(origin):
                blocked = JSONResponse(
                    status_code=status.HTTP_403_FORBIDDEN,
                    content={"detail": "Request origin is not allowed."},
                )
                self._apply_security_headers(blocked)
                if self._requires_no_store(request.url.path):
                    apply_no_store_cache_headers(blocked)
                return blocked

        response = await call_next(request)
        self._apply_security_headers(response)
        if request.scope.get("type") == "http" and self._requires_no_store(request.url.path):
            apply_no_store_cache_headers(response)
        return response

