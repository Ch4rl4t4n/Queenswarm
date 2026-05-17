"""Universal External Project Integration Layer (Phase 2.5 — MCP + REST/WS)."""

from __future__ import annotations

from app.domain.external.gateway import execute_external_invocation, integration_router

__all__ = ["execute_external_invocation", "integration_router"]
