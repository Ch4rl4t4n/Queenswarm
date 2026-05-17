"""Per-request tenant context used for row-level query isolation."""

from __future__ import annotations

import contextvars
import uuid

_tenant_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("qs_tenant_id", default=None)


def set_current_tenant_id(tenant_id: str | uuid.UUID | None) -> None:
    """Bind current tenant id for the active request/task context."""

    if tenant_id is None:
        _tenant_ctx.set(None)
        return
    _tenant_ctx.set(str(tenant_id).strip() or None)


def get_current_tenant_uuid() -> uuid.UUID | None:
    """Return current tenant UUID when context is present and valid."""

    raw = (_tenant_ctx.get() or "").strip()
    if not raw:
        return None
    try:
        return uuid.UUID(raw)
    except ValueError:
        return None


__all__ = ["get_current_tenant_uuid", "set_current_tenant_id"]
