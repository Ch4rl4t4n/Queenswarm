"""Tool marketplace and dynamic registry services for connectors/plugins."""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.application.services.plugin_hub import plugin_manifest
from app.application.services.lsp.lsp_mcp_bridge import lsp_bridge_registry_rows
from app.infrastructure.connectors.dynamic.hub import DynamicConnectorHub
from app.infrastructure.connectors.dynamic.schemas import DynamicConnectorCreateBody, DynamicConnectorPublic
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService
from app.infrastructure.connectors.phase3.catalog import get_phase3_template, iter_phase3_templates
from app.infrastructure.connectors.phase3.marketplace_meta import marketplace_meta_for
from app.infrastructure.plugins.manager import discover_plugins

_MARKETPLACE_FEATURED_TEMPLATE_IDS = frozenset(
    {"venice_mcp", "monid_mcp", "composio_router", "apify_store"},
)


def _tokenize(text: str) -> set[str]:
    return {m.group(0).lower() for m in re.finditer(r"[a-zA-Z0-9_]{3,}", text)}


def _score_goal(goal_tokens: set[str], *, name: str, description: str) -> float:
    if not goal_tokens:
        return 0.0
    hay = _tokenize(f"{name} {description}")
    if not hay:
        return 0.0
    overlap = len(goal_tokens.intersection(hay))
    return min(1.0, overlap / max(1.0, len(goal_tokens)))


def _tier_rank(tier: str | None) -> int:
    """Rank cost/latency tiers for aggregation (higher = more expensive/slower)."""

    mapping = {"low": 0, "medium": 1, "high": 2, "fast": 0, "balanced": 1, "slow": 2}
    return mapping.get(str(tier or "").strip().lower(), 0)


def _aggregate_tier(tiers: list[str], *, kind: str) -> str | None:
    """Pick dominant tier from tool hints."""

    if not tiers:
        return None
    order = ("low", "medium", "high") if kind == "cost" else ("fast", "balanced", "slow")
    best_idx = max(_tier_rank(t) for t in tiers)
    return order[min(best_idx, len(order) - 1)]


def _tool_hint_fields(tool: dict[str, Any]) -> dict[str, str | None]:
    """Extract optional cost/latency hints from a manifest tool row."""

    cost = str(tool.get("cost_tier") or "").strip().lower() or None
    latency = str(tool.get("latency_tier") or "").strip().lower() or None
    out: dict[str, str | None] = {}
    if cost in {"low", "medium", "high"}:
        out["cost_tier"] = cost
    if latency in {"fast", "balanced", "slow"}:
        out["latency_tier"] = latency
    return out


def _template_hint_summary(tools: tuple[dict[str, Any], ...]) -> dict[str, Any]:
    """Summarize cost/speed hints for marketplace cards."""

    tool_hints: list[dict[str, str]] = []
    cost_tiers: list[str] = []
    latency_tiers: list[str] = []
    for tool in tools:
        hints = _tool_hint_fields(tool)
        name = str(tool.get("name") or "").strip()
        if name and hints:
            tool_hints.append({"name": name, **{k: v for k, v in hints.items() if v}})
        if hints.get("cost_tier"):
            cost_tiers.append(str(hints["cost_tier"]))
        if hints.get("latency_tier"):
            latency_tiers.append(str(hints["latency_tier"]))
    return {
        "cost_tier": _aggregate_tier(cost_tiers, kind="cost"),
        "latency_tier": _aggregate_tier(latency_tiers, kind="latency"),
        "tool_hints": tool_hints,
    }


def _tool_rows_from_manifest(
    *,
    connector_slug: str,
    connector_display_name: str,
    manifest: dict[str, Any] | None,
    is_active: bool,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(manifest, dict):
        return out
    tools = manifest.get("tools")
    if not isinstance(tools, list):
        return out
    for tool in tools:
        if not isinstance(tool, dict):
            continue
        name = str(tool.get("name") or "").strip()
        if not name:
            continue
        out.append(
            {
                "connector_slug": connector_slug,
                "connector_display_name": connector_display_name,
                "tool_name": name,
                "description": str(tool.get("description") or ""),
                "method": str(tool.get("method") or "GET").upper(),
                "path": str(tool.get("path") or "/"),
                "required_permission": (
                    str(tool.get("required_permission") or "").strip().lower() or None
                ),
                "allowed_manager_slugs": [
                    str(item).strip().lower()
                    for item in (tool.get("allowed_manager_slugs") or [])
                    if str(item).strip()
                ],
                "rate_limit_per_minute": (
                    int(tool.get("rate_limit_per_minute"))
                    if isinstance(tool.get("rate_limit_per_minute"), int)
                    else None
                ),
                "is_active": bool(is_active),
                "source": "dynamic_connector",
                **_tool_hint_fields(tool),
            },
        )
    return out


async def tool_registry_snapshot(
    session: AsyncSession,
    *,
    manager_slug: str | None = None,
    goal: str | None = None,
    limit: int = 24,
) -> list[dict[str, Any]]:
    """Return connector tool rows discoverable by agents/supervisor."""

    snaps = await DynamicConnectorHub.snapshots(session)
    target_manager = (manager_slug or "").strip().lower()
    goal_tokens = _tokenize(goal or "")
    rows: list[dict[str, Any]] = []
    for snap in snaps:
        if not snap.is_active:
            continue
        entries = _tool_rows_from_manifest(
            connector_slug=snap.slug,
            connector_display_name=snap.display_name,
            manifest=snap.mcp_manifest,
            is_active=bool(snap.is_active),
        )
        for item in entries:
            allowed_mgr = item.get("allowed_manager_slugs") or []
            if target_manager and allowed_mgr and target_manager not in set(allowed_mgr):
                continue
            score = _score_goal(
                goal_tokens,
                name=f"{item['connector_slug']} {item['tool_name']}",
                description=str(item.get("description") or ""),
            )
            item["score"] = float(f"{score:.4f}")
            rows.append(item)

    rows.sort(
        key=lambda row: (
            -float(row.get("score") or 0.0),
            row["connector_slug"],
            row["tool_name"],
        ),
    )
    if settings.lsp_mcp_bridge_enabled:
        lsp_rows = lsp_bridge_registry_rows(goal=goal, limit=min(6, int(limit)))
        rows = lsp_rows + rows
        rows.sort(
            key=lambda row: (
                -float(row.get("score") or 0.0),
                row["connector_slug"],
                row["tool_name"],
            ),
        )
    return rows[: max(1, int(limit))]


async def marketplace_catalog(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
) -> dict[str, Any]:
    """Return foundation catalog for installable API ecosystem entries."""

    svc = DynamicConnectorService()
    visible = await svc.list_visible(session, dashboard_user_id=dashboard_user_id)
    by_slug = {row.slug.strip().lower(): row for row in visible}

    phase3: list[dict[str, Any]] = []
    for template in iter_phase3_templates():
        slug_key = template.suggested_slug.strip().lower()
        installed = by_slug.get(slug_key)
        hint_summary = _template_hint_summary(template.tools)
        meta = marketplace_meta_for(template.template_id)
        cost_tier = hint_summary.get("cost_tier") or meta.get("cost_tier") or "medium"
        latency_tier = hint_summary.get("latency_tier") or meta.get("latency_tier") or "balanced"
        phase3.append(
            {
                "source": "phase3_template",
                "id": template.template_id,
                "slug": template.suggested_slug,
                "title": template.title,
                "summary": template.summary,
                "category": template.category,
                "auth_type": template.auth_type,
                "tool_count": len(template.tools),
                "documentation_url": template.documentation_url,
                "service_homepage": meta.get("service_homepage") or template.documentation_url,
                "agent_usage": str(meta.get("agent_usage") or ""),
                "auth_header_name": meta.get("auth_header_name"),
                "suggested_manager_slugs": list(template.suggested_manager_slugs),
                "installed": installed is not None,
                "installed_connector_id": installed.id if installed is not None else None,
                "featured": template.template_id in _MARKETPLACE_FEATURED_TEMPLATE_IDS,
                "mcp_preset": template.template_id in _MARKETPLACE_FEATURED_TEMPLATE_IDS,
                "cost_tier": cost_tier,
                "latency_tier": latency_tier,
                "tool_hints": hint_summary.get("tool_hints") or [],
            },
        )

    plugin_rows = plugin_manifest().get("plugins", [])
    plugins_builtin = [
        {
            "source": "plugin_builtin",
            "id": str(row.get("id") or ""),
            "title": str(row.get("title") or row.get("id") or ""),
            "summary": str(row.get("description") or ""),
            "enabled": bool(row.get("enabled")),
        }
        for row in plugin_rows
        if isinstance(row, dict)
    ]
    plugins_user = [
        {
            "source": "plugin_user",
            "id": str(row.get("id") or ""),
            "title": str(row.get("name") or row.get("id") or ""),
            "summary": str(row.get("description") or ""),
            "enabled": str(row.get("status") or "") == "active",
            "filename": row.get("filename"),
            "size_bytes": row.get("size_bytes"),
        }
        for row in discover_plugins()
        if isinstance(row, dict)
    ]
    return {
        "phase3_templates": phase3,
        "plugins_builtin": plugins_builtin,
        "plugins_user": plugins_user,
    }


async def install_marketplace_entry(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    source: str,
    entry_id: str,
    slug_override: str | None = None,
    display_name_override: str | None = None,
) -> tuple[str, DynamicConnectorPublic | None]:
    """Install a marketplace entry (currently Phase 3 templates + existing rows)."""

    src = source.strip().lower()
    if src != "phase3_template":
        return "unsupported_source", None

    template = get_phase3_template(entry_id)
    connector_slug = (slug_override or template.suggested_slug).strip().lower()
    display_name = (display_name_override or template.title).strip()

    svc = DynamicConnectorService()
    existing = await svc.fetch_by_slug(session, slug=connector_slug)
    if existing is not None:
        # Existing projection without secrets.
        return "already_installed", DynamicConnectorPublic.model_validate(
            {
                "id": str(existing.id),
                "slug": existing.slug,
                "display_name": existing.display_name,
                "base_url": existing.base_url,
                "auth_type": existing.auth_type,
                "mcp_manifest": dict(existing.mcp_manifest) if isinstance(existing.mcp_manifest, dict) else None,
                "allowed_manager_slugs": list(existing.allowed_manager_slugs or []),
                "is_active": bool(existing.is_active),
                "is_builtin": bool(existing.is_builtin),
                "builtin_kind": existing.builtin_kind,
                "last_tested_at": existing.last_tested_at.isoformat() if existing.last_tested_at else None,
            },
        )

    body = DynamicConnectorCreateBody(
        slug=connector_slug,
        display_name=display_name,
        base_url=template.base_url,
        auth_type=template.auth_type,  # type: ignore[arg-type]
        allowed_manager_slugs=list(template.suggested_manager_slugs),
        mcp_manifest={"tools": [dict(tool) for tool in template.tools]},
        secrets=None,
    )
    created = await svc.create_row(
        session,
        dashboard_user_id=dashboard_user_id,
        body=body,
    )
    return "installed", created


async def tool_hub_overview(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    manager_slug: str | None = None,
    goal: str | None = None,
    limit: int = 48,
) -> dict[str, Any]:
    """Unified Tool Hub snapshot — registry rows + featured MCP presets + totals."""

    catalog = await marketplace_catalog(session, dashboard_user_id=dashboard_user_id)
    registry = await tool_registry_snapshot(
        session,
        manager_slug=manager_slug,
        goal=goal,
        limit=limit,
    )
    templates = catalog.get("phase3_templates")
    phase3_rows = [row for row in templates if isinstance(row, dict)] if isinstance(templates, list) else []
    featured = [row for row in phase3_rows if bool(row.get("featured"))]
    venice = next((row for row in phase3_rows if row.get("id") == "venice_mcp"), None)
    active_connectors = sum(1 for row in phase3_rows if bool(row.get("installed")))
    return {
        "registry": registry,
        "featured_presets": featured,
        "venice_preset": venice,
        "totals": {
            "installed_tools": len(registry),
            "active_presets": active_connectors,
            "featured_count": len(featured),
        },
        "goal": (goal or "").strip() or None,
        "manager_slug": (manager_slug or "").strip().lower() or None,
    }


__all__ = [
    "install_marketplace_entry",
    "marketplace_catalog",
    "tool_hub_overview",
    "tool_registry_snapshot",
]
