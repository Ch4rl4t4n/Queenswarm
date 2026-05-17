"""Tool marketplace and dynamic registry services for connectors/plugins."""

from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.plugin_hub import plugin_manifest
from app.infrastructure.connectors.dynamic.hub import DynamicConnectorHub
from app.infrastructure.connectors.dynamic.schemas import DynamicConnectorCreateBody, DynamicConnectorPublic
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService
from app.infrastructure.connectors.phase3.catalog import get_phase3_template, iter_phase3_templates
from app.infrastructure.plugins.manager import discover_plugins


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
                "suggested_manager_slugs": list(template.suggested_manager_slugs),
                "installed": installed is not None,
                "installed_connector_id": installed.id if installed is not None else None,
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


__all__ = [
    "install_marketplace_entry",
    "marketplace_catalog",
    "tool_registry_snapshot",
]
