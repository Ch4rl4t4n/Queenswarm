"""Model Context Protocol (MCP) server exposing Phase 2.5 external integration tools.

Primary transport: **stdio** (``python -m app.external.mcp_server``) for IDE / Claude Desktop compatibility.

Optional transport: **Streamable HTTP** mounted under ``/mcp/external`` when
``EXTERNAL_MCP_STREAMABLE_HTTP_ENABLED=true`` on the FastAPI process (terminate TLS at the edge).
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from app.core.config import get_settings
from app.core.database import async_session
from app.domain.external.gateway import execute_external_invocation

mcp_integration = FastMCP(
    "queenswarm-external-integration",
    instructions=(
        "Queenswarm Universal External Project Integration Layer — invoke guarded trading, "
        "ordering, or generic simulation lanes with scoped qs_ep_ API keys."
    ),
)


@mcp_integration.tool()
async def external_invoke(
    project_slug: str,
    action: str,
    api_key: str,
    payload: dict[str, Any] | None = None,
) -> str:
    """Mirror ``POST /api/v1/external/{project_slug}/run`` inside MCP hosts.

    Args:
        project_slug: Registered integration slug (``external_projects.slug``).
        action: Manager capability such as ``quote``, ``execute_trade``, ``preview_cart``.
        api_key: Plain ``qs_ep_<uuid>.<secret>`` credential (transmit only over trusted transports).
        payload: Arbitrary JSON object forwarded to specialist managers.

    Returns:
        JSON-encoded envelope containing ``audit_id``, timing, cost heuristic, and ``result`` payload.
    """

    cfg = get_settings()
    data = payload if isinstance(payload, dict) else {}
    async with async_session() as session:
        bundle = await execute_external_invocation(
            session,
            cfg=cfg,
            credential=api_key.strip(),
            project_slug=project_slug.strip(),
            action=action.strip(),
            payload=data,
            channel="mcp",
        )
    return json.dumps(bundle, default=str)


@mcp_integration.tool()
async def external_capabilities() -> str:
    """Return discovery metadata for REST/WebSocket mirrors (easy-mode alignment)."""

    meta = {
        "rest_run": "POST /api/v1/external/{project_slug}/run",
        "websocket": "/api/v1/external/{project_slug}/ws?token=qs_ep_…",
        "scopes": ["run", "mcp:call", "trading:live", "*"],
        "managers": ["trading", "food_ordering", "generic"],
        "human_in_the_loop": "Live trading requires human_approval_confirmed + ticket plus trading:live scope.",
    }
    return json.dumps(meta, indent=2)


def streamable_http_app() -> Any:
    """ASGI app consumed by ``FastAPI.mount`` when Streamable HTTP is enabled."""

    return mcp_integration.streamable_http_app()


def main() -> None:
    """Entrypoint for stdio MCP supervisors (Docker sidecars, desktop hosts)."""

    asyncio.run(mcp_integration.run_stdio_async())


if __name__ == "__main__":
    main()


__all__ = ["external_capabilities", "external_invoke", "main", "mcp_integration", "streamable_http_app"]
