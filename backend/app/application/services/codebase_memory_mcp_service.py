"""POS-I5 / H7 — Internal codebase-memory MCP for Tech SCV lane (HiveMind + repo health)."""

from __future__ import annotations

import json
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.harness_tech_health import build_tech_health_report
from app.core.chroma_client import HIVE_MIND_COLLECTION, semantic_search
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService

_logger = get_logger(__name__)

CODEBASE_MEMORY_MCP_SLUG = "codebase_memory"
CODEBASE_MEMORY_BUILTIN_KIND = "codebase_memory"
CODEBASE_MEMORY_BASE_URL = "internal://codebase-memory"

CODEBASE_MEMORY_MANAGERS: tuple[str, ...] = (
    "execution_operations",
    "review_quality",
    "research_intelligence",
)

CODEBASE_MEMORY_MANIFEST: dict[str, Any] = {
    "tools": [
        {
            "name": "search_hive_mind",
            "description": "Semantic search HiveMind embeddings for Tech SCV / maintainer context.",
            "path": "/search",
            "method": "POST",
            "allowed_manager_slugs": list(CODEBASE_MEMORY_MANAGERS),
        },
        {
            "name": "tech_health_snapshot",
            "description": "Read-only repo tech health signals (deps, maintainer docs, perf tests).",
            "path": "/tech-health",
            "method": "GET",
            "allowed_manager_slugs": list(CODEBASE_MEMORY_MANAGERS),
        },
    ],
}


async def invoke_codebase_memory_tool(
    *,
    tool_name: str,
    arguments: dict[str, Any],
) -> str:
    """Execute internal codebase-memory MCP tool without outbound HTTP."""

    if not settings.codebase_memory_mcp_enabled:
        return "dynamic_invoke_error: codebase_memory_mcp disabled"

    normalized = tool_name.strip().lower()
    if normalized == "search_hive_mind":
        query = str(arguments.get("q") or arguments.get("query") or "").strip()
        if len(query) < 2:
            return "codebase_memory_error: query must be at least 2 characters"
        limit_raw = arguments.get("limit", 6)
        try:
            limit = max(1, min(int(limit_raw), settings.hive_mind_max_query_hits_vector))
        except (TypeError, ValueError):
            limit = 6
        hits = await semantic_search(query, HIVE_MIND_COLLECTION, n_results=limit)
        items: list[dict[str, Any]] = []
        for row in hits:
            meta = dict(row.get("metadata") or {})
            if meta.get("dashboard_user_id"):
                meta["dashboard_user_id"] = "***"
            items.append(
                {
                    "id": row.get("id"),
                    "document": (row.get("document") or "")[:2048],
                    "metadata": meta,
                    "distance": row.get("distance"),
                },
            )
        payload = {"query": query, "items": items, "count": len(items)}
        _logger.info(
            "codebase_memory_mcp.search_hive_mind",
            agent_id="codebase_memory_mcp",
            swarm_id=CODEBASE_MEMORY_MCP_SLUG,
            task_id="search",
            hit_count=len(items),
        )
        return json.dumps(payload, ensure_ascii=False)

    if normalized == "tech_health_snapshot":
        report = build_tech_health_report()
        _logger.info(
            "codebase_memory_mcp.tech_health_snapshot",
            agent_id="codebase_memory_mcp",
            swarm_id=CODEBASE_MEMORY_MCP_SLUG,
            task_id="tech_health",
            health_score=report.get("health_score"),
        )
        return json.dumps(report, ensure_ascii=False)

    return f"dynamic_invoke_error: tool `{tool_name}` missing from codebase_memory manifest"


async def ensure_codebase_memory_connector(session: AsyncSession) -> bool:
    """Idempotently seed builtin codebase-memory MCP connector row."""

    if not settings.codebase_memory_mcp_enabled:
        return False

    svc = DynamicConnectorService()
    existing = await svc.fetch_by_slug(session, slug=CODEBASE_MEMORY_MCP_SLUG)
    if existing is not None:
        if not existing.is_active:
            existing.is_active = True
            await session.flush()
        return True

    from app.infrastructure.connectors.dynamic.hub import invalidate_registry_cache
    from app.infrastructure.persistence.models.dynamic_connector import DynamicConnector

    row = DynamicConnector(
        slug=CODEBASE_MEMORY_MCP_SLUG,
        display_name="Codebase Memory MCP",
        base_url=CODEBASE_MEMORY_BASE_URL,
        auth_type="none",
        secrets_cipher=None,
        mcp_manifest=dict(CODEBASE_MEMORY_MANIFEST),
        allowed_manager_slugs=list(CODEBASE_MEMORY_MANAGERS),
        is_active=True,
        is_builtin=True,
        builtin_kind=CODEBASE_MEMORY_BUILTIN_KIND,
        last_tested_at=None,
        dashboard_user_id=None,
    )
    session.add(row)
    await session.flush()
    await invalidate_registry_cache()
    return True


async def compose_codebase_memory_mcp_readiness(
    session: AsyncSession,
) -> dict[str, Any]:
    """Readiness snapshot for Execution Studio Tech SCV lane."""

    enabled = settings.codebase_memory_mcp_enabled
    svc = DynamicConnectorService()
    row = await svc.fetch_by_slug(session, slug=CODEBASE_MEMORY_MCP_SLUG)
    installed = row is not None and bool(row.is_active)
    tools = [str(item.get("name") or "") for item in (CODEBASE_MEMORY_MANIFEST.get("tools") or []) if isinstance(item, dict)]
    return {
        "enabled": enabled,
        "connector_slug": CODEBASE_MEMORY_MCP_SLUG,
        "installed": installed,
        "ready": enabled and installed,
        "tools": tools,
        "manager_slugs": list(CODEBASE_MEMORY_MANAGERS),
        "operator_hint": (
            "Tech SCV agents may mcp_invoke codebase_memory for HiveMind search + repo health."
            if enabled and installed
            else "Run migration or enable codebase_memory_mcp to seed internal connector."
        ),
    }


__all__ = [
    "CODEBASE_MEMORY_BUILTIN_KIND",
    "CODEBASE_MEMORY_MANAGERS",
    "CODEBASE_MEMORY_MANIFEST",
    "CODEBASE_MEMORY_MCP_SLUG",
    "compose_codebase_memory_mcp_readiness",
    "ensure_codebase_memory_connector",
    "invoke_codebase_memory_tool",
]
