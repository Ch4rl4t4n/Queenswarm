"""Live + fallback snapshot for MCP Ops Studio workspace cards."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.tool_gap_signal import list_tool_gaps
from app.application.services.tool_marketplace import marketplace_catalog
from app.core.config import settings
from app.infrastructure.connectors.dynamic.hub import DynamicConnectorHub, manifest_tool_default
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService
from app.infrastructure.connectors.phase3.marketplace_meta import marketplace_meta_for


class McpCatalogRowOut(BaseModel):
    """Catalog provider row for MCP discovery section."""

    model_config = ConfigDict(extra="ignore")

    provider: str
    trust_tier: Literal["verified", "community"]
    tool_count: int = 0
    auth_mode: Literal["oauth", "api_key"]
    template_id: str | None = None
    installed: bool = False
    integrations_href: str | None = None


class McpInstallRowOut(BaseModel):
    """Recommended install row (not yet installed featured templates)."""

    model_config = ConfigDict(extra="ignore")

    provider: str
    requested_by: str = "system"
    stage: Literal["policy_review", "pending_approval"] = "pending_approval"
    template_id: str | None = None
    integrations_href: str | None = None


class McpHealthRowOut(BaseModel):
    """Runtime health diagnostics row."""

    model_config = ConfigDict(extra="ignore")

    provider: str
    status: Literal["healthy", "degraded", "cold"]
    checked_at: str
    connector_slug: str | None = None
    failed_calls: int = 0
    total_calls: int = 0


class McpToolGapRowOut(BaseModel):
    """Actionable gap detected from failed MCP invocations."""

    model_config = ConfigDict(extra="ignore")

    kind: str
    connector_slug: str
    tool_name: str
    message: str
    occurrences: int = 1
    suggested_template_id: str | None = None
    integrations_href: str | None = None


class McpOpsStudioSnapshotOut(BaseModel):
    """Unified read model for MCP Ops Studio sections."""

    model_config = ConfigDict(extra="ignore")

    generated_at: datetime
    source: Literal["live", "read_only_mock"] = "live"
    catalog: list[McpCatalogRowOut] = Field(default_factory=list)
    install: list[McpInstallRowOut] = Field(default_factory=list)
    health: list[McpHealthRowOut] = Field(default_factory=list)
    tool_gaps: list[McpToolGapRowOut] = Field(default_factory=list)


def _mock_snapshot() -> McpOpsStudioSnapshotOut:
    """Legacy read-only mock when live snapshot is disabled."""

    return McpOpsStudioSnapshotOut(
        generated_at=datetime.now(tz=UTC),
        source="read_only_mock",
        catalog=[
            McpCatalogRowOut(provider="GitHub MCP", trust_tier="verified", tool_count=8, auth_mode="oauth"),
            McpCatalogRowOut(provider="Notion MCP", trust_tier="community", tool_count=5, auth_mode="api_key"),
        ],
        install=[
            McpInstallRowOut(provider="Linear MCP", requested_by="operator", stage="policy_review"),
        ],
        health=[],
        tool_gaps=[],
    )


def _auth_mode_from_template(auth_type: str) -> Literal["oauth", "api_key"]:
    lowered = auth_type.strip().lower()
    if "oauth" in lowered:
        return "oauth"
    return "api_key"


async def _health_for_installed(
    *,
    slug: str,
    display_name: str,
    manifest: dict[str, Any] | None,
) -> McpHealthRowOut:
    """Derive health from Redis per-tool counters (cold when no traffic)."""

    manifest_row = manifest if isinstance(manifest, dict) else manifest_tool_default()
    tools = manifest_row.get("tools")
    tool_names: list[str] = []
    if isinstance(tools, list):
        for tool in tools:
            if isinstance(tool, dict):
                name = str(tool.get("name") or "").strip().lower()
                if name:
                    tool_names.append(name)
    if not tool_names:
        tool_names = ["invoke"]

    total_calls = 0
    failed_calls = 0
    for name in tool_names[:8]:
        metrics = await DynamicConnectorHub.read_tool_metrics(slug, name)
        total_calls += int(metrics.get("total_calls") or 0)
        failed_calls += int(metrics.get("failed_calls") or 0)

    if total_calls == 0:
        status: Literal["healthy", "degraded", "cold"] = "cold"
    elif failed_calls >= 3 and failed_calls / max(total_calls, 1) >= 0.5:
        status = "degraded"
    else:
        status = "healthy"

    return McpHealthRowOut(
        provider=display_name,
        status=status,
        checked_at=datetime.now(tz=UTC).isoformat(),
        connector_slug=slug,
        failed_calls=failed_calls,
        total_calls=total_calls,
    )


async def compose_mcp_ops_studio_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
) -> McpOpsStudioSnapshotOut:
    """Compose MCP Ops snapshot from marketplace catalog, metrics, and tool gaps."""

    if not settings.mcp_ops_studio_live_snapshot_enabled:
        return _mock_snapshot()

    catalog_payload = await marketplace_catalog(session, dashboard_user_id=dashboard_user_id)
    templates = list(catalog_payload.get("phase3_templates") or [])
    connector_svc = DynamicConnectorService()

    catalog_rows: list[McpCatalogRowOut] = []
    install_rows: list[McpInstallRowOut] = []
    health_rows: list[McpHealthRowOut] = []

    for row in templates:
        if not isinstance(row, dict):
            continue
        template_id = str(row.get("id") or "")
        title = str(row.get("title") or template_id)
        installed = bool(row.get("installed"))
        meta = marketplace_meta_for(template_id) if template_id else {}
        trust = str(meta.get("trust_tier") or "community")
        trust_tier: Literal["verified", "community"] = "verified" if trust == "verified" else "community"
        href = f"/integrations?tab=hub&hubSection=marketplace&template={template_id}" if template_id else None

        catalog_rows.append(
            McpCatalogRowOut(
                provider=title,
                trust_tier=trust_tier,
                tool_count=int(row.get("tool_count") or 0),
                auth_mode=_auth_mode_from_template(str(row.get("auth_type") or "api_key")),
                template_id=template_id or None,
                installed=installed,
                integrations_href=href,
            ),
        )

        if not installed and bool(row.get("featured")):
            install_rows.append(
                McpInstallRowOut(
                    provider=title,
                    requested_by="marketplace",
                    stage="pending_approval",
                    template_id=template_id or None,
                    integrations_href=href,
                ),
            )

        if installed:
            slug = str(row.get("slug") or "").strip().lower()
            if slug:
                installed_row = await connector_svc.fetch_by_slug(session, slug=slug)
                manifest = (
                    dict(installed_row.mcp_manifest)
                    if installed_row is not None and isinstance(installed_row.mcp_manifest, dict)
                    else None
                )
                health_rows.append(
                    await _health_for_installed(
                        slug=slug,
                        display_name=title,
                        manifest=manifest,
                    ),
                )

    catalog_rows.sort(key=lambda item: (item.installed, -item.tool_count, item.provider.lower()))
    install_rows = install_rows[:8]
    health_rows.sort(key=lambda item: (item.status != "degraded", item.provider.lower()))

    gap_rows = [
        McpToolGapRowOut(
            kind=str(row.get("kind") or "unknown"),
            connector_slug=str(row.get("connector_slug") or ""),
            tool_name=str(row.get("tool_name") or "invoke"),
            message=str(row.get("message") or "")[:240],
            occurrences=int(row.get("occurrences") or 1),
            suggested_template_id=str(row.get("suggested_template_id") or "") or None,
            integrations_href=str(row.get("integrations_href") or "") or None,
        )
        for row in await list_tool_gaps(tenant_id=tenant_id, limit=12)
    ]

    return McpOpsStudioSnapshotOut(
        generated_at=datetime.now(tz=UTC),
        source="live",
        catalog=catalog_rows[:24],
        install=install_rows,
        health=health_rows[:16],
        tool_gaps=gap_rows,
    )


__all__ = ["McpOpsStudioSnapshotOut", "compose_mcp_ops_studio_snapshot"]
