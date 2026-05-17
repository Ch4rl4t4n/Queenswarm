"""Backward-compatible entrypoint for ``python -m app.external.mcp_server``.

Delegates to :mod:`app.domain.external.mcp_server` so Compose sidecars and docs
keep a short module path while the layered layout owns the implementation.
"""

from __future__ import annotations

from app.domain.external.mcp_server import *  # noqa: F403

__all__ = ["external_capabilities", "external_invoke", "main", "mcp_integration", "streamable_http_app"]
