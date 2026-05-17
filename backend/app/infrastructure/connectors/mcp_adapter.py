"""MCP adapter — Postgres-backed manifests + JWT-sealed swarm tool calls."""

from __future__ import annotations

from typing import Any, ClassVar

from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.connectors.base import BaseConnector, ConnectorAuthEnvelope
from app.infrastructure.connectors.dynamic.hub import DynamicConnectorHub, load_active_snapshots


class MCPAdapter(BaseConnector):
    """MCP façade: placeholders now enrich orchestrator payloads via Postgres manifests."""

    slug: ClassVar[str] = "mcp_placeholder"

    async def ping(self, auth: ConnectorAuthEnvelope) -> bool:
        """Return ``True`` when either OAuth bearer or api key resolves."""

        return bool(auth.bearer_header())

    async def list_tool_slots(self, auth: ConnectorAuthEnvelope) -> list[dict[str, Any]]:
        """Static placeholder — dashboards query ``/connectors/catalog`` instead."""

        _ = auth
        return []

    @staticmethod
    async def dynamic_tool_catalog(session: AsyncSession | None) -> list[dict[str, Any]]:
        """Return flattened MCP tool descriptors for Ballroom + dashboard prompts."""

        rows = await DynamicConnectorHub.snapshots(session)
        catalog: list[dict[str, Any]] = []
        for snap in rows:
            mf = snap.mcp_manifest if isinstance(snap.mcp_manifest, dict) else {}
            for tool_blob in mf.get("tools") or []:
                if not isinstance(tool_blob, dict):
                    continue
                name_txt = str(tool_blob.get("name") or "").strip()
                if not name_txt:
                    continue
                catalog.append(
                    {
                        "connector_slug": snap.slug,
                        "tool": name_txt,
                        "description": str(tool_blob.get("description") or ""),
                        "method": str(tool_blob.get("method") or "GET"),
                    },
                )
        return catalog


__all__ = ["MCPAdapter"]
