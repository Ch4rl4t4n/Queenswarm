"""Bind request-scoped context for structured logs and trace failures."""

from __future__ import annotations

import uuid
import secrets

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.jwt_tokens import decode_jwt_optional_typ
from app.core.metrics import observe_http_request_metric


def _extract_bearer_payload(request: Request) -> dict[str, object]:
    """Best-effort decode bearer payload for tenant/user context binding."""

    raw = request.headers.get("authorization", "").strip()
    if not raw.lower().startswith("bearer "):
        return {}
    token = raw[7:].strip()
    if not token:
        return {}
    try:
        decoded = decode_jwt_optional_typ(token)
        return decoded if isinstance(decoded, dict) else {}
    except Exception:  # noqa: BLE001 - middleware should degrade open on decode errors
        return {}


def _resolve_trace_ids(request: Request) -> tuple[str, str]:
    """Resolve OpenTelemetry-style trace/span ids from ``traceparent`` or synthesize new ones."""

    traceparent = request.headers.get("traceparent", "").strip()
    if traceparent:
        parts = traceparent.split("-")
        if len(parts) == 4 and len(parts[1]) == 32 and len(parts[2]) == 16:
            trace_id = parts[1].lower()
            span_id = parts[2].lower()
            return trace_id, span_id
    return secrets.token_hex(16), secrets.token_hex(8)


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach request_id/method/path to structlog contextvars for each HTTP request."""

    async def dispatch(self, request: Request, call_next):  # noqa: ANN001
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        correlation_id = request.headers.get("x-correlation-id") or request_id
        bearer = _extract_bearer_payload(request)
        tenant_id = str(bearer.get("tenant_id")).strip() if bearer.get("tenant_id") else ""
        subject = str(bearer.get("sub")).strip() if bearer.get("sub") else ""
        trace_id, span_id = _resolve_trace_ids(request)

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            correlation_id=correlation_id,
            request_method=request.method.upper(),
            request_path=request.url.path,
            tenant_id=tenant_id or None,
            subject=subject or None,
            trace_id=trace_id,
            span_id=span_id,
        )
        try:
            response: Response = await call_next(request)
            observe_http_request_metric(
                tenant_id=tenant_id or None,
                user_subject=subject or None,
                method=request.method.upper(),
                path=request.url.path,
                status_code=response.status_code,
            )
        finally:
            structlog.contextvars.clear_contextvars()
        response.headers.setdefault("X-Request-ID", request_id)
        response.headers.setdefault("X-Correlation-ID", correlation_id)
        response.headers.setdefault("Traceparent", f"00-{trace_id}-{span_id}-01")
        return response


__all__ = ["RequestContextMiddleware"]
