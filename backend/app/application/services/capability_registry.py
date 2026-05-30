"""Capability registry for Agentic OS and Apps/Tools split."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import settings

CapabilityRiskTier = Literal["read", "write", "publish", "financial"]
CapabilitySurface = Literal["agentic_os", "apps_tools", "integrations", "knowledge"]
CapabilityStatus = Literal["live", "beta", "planned"]
WorkspaceLayer = Literal["agentic_os", "apps_tools"]


class CapabilityContractOut(BaseModel):
    """Typed capability contract for swarm-to-module routing."""

    model_config = ConfigDict(extra="ignore")

    capability_key: str
    label: str
    owner_module: str
    surface: CapabilitySurface
    summary: str
    status: CapabilityStatus = "live"
    version: str = "v1"
    risk_tier: CapabilityRiskTier
    requires_approval: bool
    input_schema_ref: str
    output_schema_ref: str
    enabled: bool
    sla_hint_sec: int | None = None
    dependency_keys: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)


class CapabilityWorkspaceOut(BaseModel):
    """Workspace/module row owning one or more capabilities."""

    model_config = ConfigDict(extra="ignore")

    module_key: str
    label: str
    layer: WorkspaceLayer
    summary: str
    status: CapabilityStatus = "live"
    enabled: bool
    capability_keys: list[str] = Field(default_factory=list)


class CapabilityRegistrySnapshotOut(BaseModel):
    """Registry snapshot for UI and capability-based routing."""

    model_config = ConfigDict(extra="ignore")

    generated_at: datetime
    registry_version: str = "v1"
    workspaces: list[CapabilityWorkspaceOut] = Field(default_factory=list)
    capabilities: list[CapabilityContractOut] = Field(default_factory=list)


def _capability_catalog() -> list[CapabilityContractOut]:
    """Static capability catalog; runtime-safe and read-only."""

    return [
        CapabilityContractOut(
            capability_key="swarm.orchestrate.v1",
            label="Swarm orchestration",
            owner_module="agentic_os_core",
            surface="agentic_os",
            summary="Plan, route, and execute multi-step swarm workflows.",
            status="live",
            risk_tier="write",
            requires_approval=False,
            input_schema_ref="schemas/swarm.orchestrate.input.v1.json",
            output_schema_ref="schemas/swarm.orchestrate.output.v1.json",
            enabled=bool(settings.operator_control_plane_enabled and settings.agent_os_enabled),
            sla_hint_sec=90,
            tags=["swarm", "orchestration", "core"],
        ),
        CapabilityContractOut(
            capability_key="knowledge.hivemind.query.v1",
            label="HiveMind query",
            owner_module="agentic_os_core",
            surface="knowledge",
            summary="Retrieve verified context from HiveMind and recipes.",
            status="live",
            risk_tier="read",
            requires_approval=False,
            input_schema_ref="schemas/knowledge.hivemind.query.input.v1.json",
            output_schema_ref="schemas/knowledge.hivemind.query.output.v1.json",
            enabled=bool(settings.hive_mind_enabled),
            sla_hint_sec=20,
            tags=["knowledge", "hivemind", "retrieval"],
        ),
        CapabilityContractOut(
            capability_key="integrations.connector.invoke.v1",
            label="Connector invoke",
            owner_module="integration_runtime",
            surface="integrations",
            summary="Invoke connectors/plugins through governed execution lanes.",
            status="live",
            risk_tier="write",
            requires_approval=True,
            input_schema_ref="schemas/integrations.connector.invoke.input.v1.json",
            output_schema_ref="schemas/integrations.connector.invoke.output.v1.json",
            enabled=bool(settings.execution_studio_enabled),
            dependency_keys=["knowledge.hivemind.query.v1"],
            tags=["integrations", "connectors", "tools"],
        ),
        CapabilityContractOut(
            capability_key="apps.marketing.publish_pipeline.v1",
            label="Marketing publish pipeline",
            owner_module="marketing_automation",
            surface="apps_tools",
            summary="Generate and orchestrate multi-channel publish packs.",
            status="live",
            risk_tier="publish",
            requires_approval=True,
            input_schema_ref="schemas/apps.marketing.publish_pipeline.input.v1.json",
            output_schema_ref="schemas/apps.marketing.publish_pipeline.output.v1.json",
            enabled=bool(settings.social_publish_enabled and settings.publish_queue_enabled),
            dependency_keys=["integrations.connector.invoke.v1"],
            sla_hint_sec=180,
            tags=["apps", "marketing", "publish"],
        ),
        CapabilityContractOut(
            capability_key="apps.marketing.omni_publish.compose.v1",
            label="Marketing omni publish compose",
            owner_module="marketing_automation",
            surface="apps_tools",
            summary="Upload once and generate channel-adapted publish variants with governed defaults.",
            status="planned",
            risk_tier="publish",
            requires_approval=True,
            input_schema_ref="schemas/apps.marketing.omni_publish.compose.input.v1.json",
            output_schema_ref="schemas/apps.marketing.omni_publish.compose.output.v1.json",
            enabled=bool(settings.social_publish_enabled and settings.publish_queue_enabled),
            dependency_keys=["apps.marketing.publish_pipeline.v1", "integrations.connector.invoke.v1"],
            sla_hint_sec=180,
            tags=["apps", "marketing", "omni-publish"],
        ),
        CapabilityContractOut(
            capability_key="apps.marketing.omni_publish.schedule.v1",
            label="Marketing omni publish schedule",
            owner_module="marketing_automation",
            surface="apps_tools",
            summary="Schedule one publish intent across channels with timezone-safe rollout windows.",
            status="planned",
            risk_tier="publish",
            requires_approval=True,
            input_schema_ref="schemas/apps.marketing.omni_publish.schedule.input.v1.json",
            output_schema_ref="schemas/apps.marketing.omni_publish.schedule.output.v1.json",
            enabled=bool(settings.social_publish_enabled and settings.publish_queue_enabled),
            dependency_keys=["apps.marketing.publish_pipeline.v1", "integrations.connector.invoke.v1"],
            sla_hint_sec=180,
            tags=["apps", "marketing", "omni-publish", "scheduling"],
        ),
        CapabilityContractOut(
            capability_key="apps.marketing.omni_publish.receipts.v1",
            label="Marketing omni publish receipts",
            owner_module="marketing_automation",
            surface="apps_tools",
            summary="Collect normalized channel delivery receipts and expose audit-ready status summaries.",
            status="planned",
            risk_tier="read",
            requires_approval=False,
            input_schema_ref="schemas/apps.marketing.omni_publish.receipts.input.v1.json",
            output_schema_ref="schemas/apps.marketing.omni_publish.receipts.output.v1.json",
            enabled=bool(settings.social_publish_enabled and settings.publish_queue_enabled),
            dependency_keys=["integrations.connector.invoke.v1", "knowledge.hivemind.query.v1"],
            sla_hint_sec=90,
            tags=["apps", "marketing", "omni-publish", "receipts"],
        ),
        CapabilityContractOut(
            capability_key="apps.mcp.catalog.discover.v1",
            label="MCP catalog discover",
            owner_module="mcp_ops_studio",
            surface="apps_tools",
            summary="Read-only discovery of MCP providers, trust metadata, and installability signals.",
            status="planned",
            risk_tier="read",
            requires_approval=False,
            input_schema_ref="schemas/apps.mcp.catalog.discover.input.v1.json",
            output_schema_ref="schemas/apps.mcp.catalog.discover.output.v1.json",
            enabled=bool(settings.execution_studio_enabled),
            dependency_keys=["knowledge.hivemind.query.v1"],
            sla_hint_sec=45,
            tags=["apps", "mcp", "catalog", "discovery"],
        ),
        CapabilityContractOut(
            capability_key="apps.mcp.catalog.install.v1",
            label="MCP catalog install",
            owner_module="mcp_ops_studio",
            surface="apps_tools",
            summary="Governed one-click MCP install with approval checkpoints and audit trails.",
            status="planned",
            risk_tier="write",
            requires_approval=True,
            input_schema_ref="schemas/apps.mcp.catalog.install.input.v1.json",
            output_schema_ref="schemas/apps.mcp.catalog.install.output.v1.json",
            enabled=bool(settings.execution_studio_enabled),
            dependency_keys=["integrations.connector.invoke.v1"],
            sla_hint_sec=90,
            tags=["apps", "mcp", "catalog", "install"],
        ),
        CapabilityContractOut(
            capability_key="apps.mcp.catalog.healthcheck.v1",
            label="MCP catalog healthcheck",
            owner_module="mcp_ops_studio",
            surface="apps_tools",
            summary="Probe MCP tool availability, auth state, and runtime health for operator diagnostics.",
            status="planned",
            risk_tier="read",
            requires_approval=False,
            input_schema_ref="schemas/apps.mcp.catalog.healthcheck.input.v1.json",
            output_schema_ref="schemas/apps.mcp.catalog.healthcheck.output.v1.json",
            enabled=bool(settings.execution_studio_enabled),
            dependency_keys=["integrations.connector.invoke.v1"],
            sla_hint_sec=60,
            tags=["apps", "mcp", "catalog", "health"],
        ),
        CapabilityContractOut(
            capability_key="apps.mcp.catalog.lifecycle.v1",
            label="MCP catalog lifecycle",
            owner_module="mcp_ops_studio",
            surface="apps_tools",
            summary="Version pin, update, and rollback lifecycle operations for installed MCP providers.",
            status="planned",
            risk_tier="write",
            requires_approval=True,
            input_schema_ref="schemas/apps.mcp.catalog.lifecycle.input.v1.json",
            output_schema_ref="schemas/apps.mcp.catalog.lifecycle.output.v1.json",
            enabled=bool(settings.execution_studio_enabled),
            dependency_keys=["integrations.connector.invoke.v1"],
            sla_hint_sec=120,
            tags=["apps", "mcp", "catalog", "lifecycle"],
        ),
        CapabilityContractOut(
            capability_key="apps.content.factory.v1",
            label="Content factory build",
            owner_module="content_factory",
            surface="apps_tools",
            summary="Run content generation workflows for validated content outputs.",
            status="beta",
            risk_tier="write",
            requires_approval=True,
            input_schema_ref="schemas/apps.content.factory.input.v1.json",
            output_schema_ref="schemas/apps.content.factory.output.v1.json",
            enabled=bool(settings.micro_saas_factory_enabled or settings.publish_performance_enabled),
            dependency_keys=["knowledge.hivemind.query.v1", "integrations.connector.invoke.v1"],
            sla_hint_sec=240,
            tags=["apps", "content", "factory"],
        ),
        CapabilityContractOut(
            capability_key="apps.trading.execution.v1",
            label="Trading automation execution",
            owner_module="trading_automation",
            surface="apps_tools",
            summary="Execute trading plans with governance, risk and audit controls.",
            status="beta",
            risk_tier="financial",
            requires_approval=True,
            input_schema_ref="schemas/apps.trading.execution.input.v1.json",
            output_schema_ref="schemas/apps.trading.execution.output.v1.json",
            enabled=bool(settings.trading_cockpit_enabled),
            dependency_keys=["integrations.connector.invoke.v1"],
            sla_hint_sec=120,
            tags=["apps", "trading", "financial"],
        ),
        CapabilityContractOut(
            capability_key="apps.polymarket.intel.v1",
            label="Polymarket intelligence",
            owner_module="polymarket_intel",
            surface="apps_tools",
            summary="Gather market intelligence for prediction market workflows.",
            status="live",
            risk_tier="read",
            requires_approval=False,
            input_schema_ref="schemas/apps.polymarket.intel.input.v1.json",
            output_schema_ref="schemas/apps.polymarket.intel.output.v1.json",
            enabled=bool(settings.prediction_markets_enabled),
            dependency_keys=["knowledge.hivemind.query.v1"],
            sla_hint_sec=60,
            tags=["apps", "polymarket", "intel"],
        ),
        CapabilityContractOut(
            capability_key="apps.research.briefing.v1",
            label="Research bee briefing",
            owner_module="research_workspace",
            surface="apps_tools",
            summary="URL/PDF/text to structured research brief with optional persistence.",
            status="live",
            risk_tier="write",
            requires_approval=True,
            input_schema_ref="schemas/apps.research.briefing.input.v1.json",
            output_schema_ref="schemas/apps.research.briefing.output.v1.json",
            enabled=bool(settings.research_bee_enabled),
            dependency_keys=["knowledge.hivemind.query.v1"],
            sla_hint_sec=90,
            tags=["apps", "research", "briefing"],
        ),
        CapabilityContractOut(
            capability_key="apps.browser.automation.v1",
            label="Browser automation lane",
            owner_module="browser_automation",
            surface="apps_tools",
            summary="Governed browser automation with approvals and audit trail.",
            status="beta",
            risk_tier="write",
            requires_approval=True,
            input_schema_ref="schemas/apps.browser.automation.input.v1.json",
            output_schema_ref="schemas/apps.browser.automation.output.v1.json",
            enabled=bool(settings.browser_harness_enabled),
            dependency_keys=["integrations.connector.invoke.v1"],
            sla_hint_sec=120,
            tags=["apps", "browser", "automation"],
        ),
        CapabilityContractOut(
            capability_key="apps.live_lane.execution.v1",
            label="Live lane execution",
            owner_module="live_lane",
            surface="apps_tools",
            summary="Guarded live execution lane for approved high-risk actions.",
            status="beta",
            risk_tier="financial",
            requires_approval=True,
            input_schema_ref="schemas/apps.live_lane.execution.input.v1.json",
            output_schema_ref="schemas/apps.live_lane.execution.output.v1.json",
            enabled=bool(settings.live_lane_snapshot_enabled),
            dependency_keys=["apps.trading.execution.v1"],
            sla_hint_sec=90,
            tags=["apps", "live-lane", "governance"],
        ),
        CapabilityContractOut(
            capability_key="apps.ecommerce.shopify_sync.v1",
            label="Shopify catalog & orders",
            owner_module="ecommerce_workspace",
            surface="apps_tools",
            summary="Read/sync Shopify products and orders with operator-gated mutations.",
            status="beta",
            risk_tier="write",
            requires_approval=True,
            input_schema_ref="schemas/apps.ecommerce.shopify.input.v1.json",
            output_schema_ref="schemas/apps.ecommerce.shopify.output.v1.json",
            enabled=bool(settings.execution_studio_enabled),
            dependency_keys=["integrations.connector.invoke.v1"],
            sla_hint_sec=60,
            tags=["apps", "ecommerce", "shopify"],
        ),
        CapabilityContractOut(
            capability_key="apps.ecommerce.stripe_checkout.v1",
            label="Stripe checkout & webhooks",
            owner_module="ecommerce_workspace",
            surface="apps_tools",
            summary="Checkout Sessions, PaymentIntents, and verified webhook ingest.",
            status="beta",
            risk_tier="financial",
            requires_approval=True,
            input_schema_ref="schemas/apps.ecommerce.stripe.input.v1.json",
            output_schema_ref="schemas/apps.ecommerce.stripe.output.v1.json",
            enabled=bool(settings.execution_studio_enabled or settings.commerce_webhooks_enabled),
            dependency_keys=["integrations.connector.invoke.v1"],
            sla_hint_sec=90,
            tags=["apps", "ecommerce", "stripe", "payments"],
        ),
        CapabilityContractOut(
            capability_key="apps.marketing.ga4_analytics.v1",
            label="GA4 analytics reports",
            owner_module="marketing_automation",
            surface="apps_tools",
            summary="GA4 runReport and realtime metrics for campaign and e-shop attribution.",
            status="beta",
            risk_tier="read",
            requires_approval=False,
            input_schema_ref="schemas/apps.marketing.ga4.input.v1.json",
            output_schema_ref="schemas/apps.marketing.ga4.output.v1.json",
            enabled=bool(settings.execution_studio_enabled),
            dependency_keys=["integrations.connector.invoke.v1"],
            sla_hint_sec=60,
            tags=["apps", "marketing", "ga4", "analytics"],
        ),
    ]


def _workspace_catalog(capabilities: list[CapabilityContractOut]) -> list[CapabilityWorkspaceOut]:
    """Compose workspaces from capability ownership."""

    grouped: dict[str, list[str]] = {}
    for row in capabilities:
        grouped.setdefault(row.owner_module, []).append(row.capability_key)

    workspaces: list[CapabilityWorkspaceOut] = [
        CapabilityWorkspaceOut(
            module_key="agentic_os_core",
            label="Agentic OS Core",
            layer="agentic_os",
            summary="Swarm orchestration, governance, and core HiveMind coordination.",
            status="live",
            enabled=bool(settings.operator_control_plane_enabled and settings.agent_os_enabled),
            capability_keys=grouped.get("agentic_os_core", []),
        ),
        CapabilityWorkspaceOut(
            module_key="integration_runtime",
            label="Integration Runtime",
            layer="agentic_os",
            summary="Connector and plugin execution contracts used by swarms and apps.",
            status="live",
            enabled=bool(settings.execution_studio_enabled),
            capability_keys=grouped.get("integration_runtime", []),
        ),
        CapabilityWorkspaceOut(
            module_key="marketing_automation",
            label="Marketing Automation",
            layer="apps_tools",
            summary="Campaign publishing and distribution workflows.",
            status="live",
            enabled=bool(settings.social_publish_enabled and settings.publish_queue_enabled),
            capability_keys=grouped.get("marketing_automation", []),
        ),
        CapabilityWorkspaceOut(
            module_key="mcp_ops_studio",
            label="MCP Ops Studio",
            layer="apps_tools",
            summary="MCP provider catalog discovery, install governance, health, and lifecycle controls.",
            status="planned",
            enabled=bool(settings.execution_studio_enabled),
            capability_keys=grouped.get("mcp_ops_studio", []),
        ),
        CapabilityWorkspaceOut(
            module_key="content_factory",
            label="Content Factory",
            layer="apps_tools",
            summary="Content generation and performance optimization workflows.",
            status="beta",
            enabled=bool(settings.micro_saas_factory_enabled or settings.publish_performance_enabled),
            capability_keys=grouped.get("content_factory", []),
        ),
        CapabilityWorkspaceOut(
            module_key="trading_automation",
            label="Trading Automation",
            layer="apps_tools",
            summary="Trading execution workflows with risk and governance.",
            status="beta",
            enabled=bool(settings.trading_cockpit_enabled),
            capability_keys=grouped.get("trading_automation", []),
        ),
        CapabilityWorkspaceOut(
            module_key="polymarket_intel",
            label="Polymarket Intel",
            layer="apps_tools",
            summary="Prediction market intelligence and signal gathering.",
            status="live",
            enabled=bool(settings.prediction_markets_enabled),
            capability_keys=grouped.get("polymarket_intel", []),
        ),
        CapabilityWorkspaceOut(
            module_key="research_workspace",
            label="Research Workspace",
            layer="apps_tools",
            summary="Research brief generation from web/docs/transcripts.",
            status="live",
            enabled=bool(settings.research_bee_enabled),
            capability_keys=grouped.get("research_workspace", []),
        ),
        CapabilityWorkspaceOut(
            module_key="browser_automation",
            label="Browser Automation",
            layer="apps_tools",
            summary="Governed browser harness and action approvals.",
            status="beta",
            enabled=bool(settings.browser_harness_enabled),
            capability_keys=grouped.get("browser_automation", []),
        ),
        CapabilityWorkspaceOut(
            module_key="live_lane",
            label="Live Lane",
            layer="apps_tools",
            summary="Final approval lane for high-risk live operations.",
            status="beta",
            enabled=bool(settings.live_lane_snapshot_enabled),
            capability_keys=grouped.get("live_lane", []),
        ),
        CapabilityWorkspaceOut(
            module_key="ecommerce_workspace",
            label="E-commerce Ops",
            layer="apps_tools",
            summary="Shopify catalog, orders, and Stripe payment workflows.",
            status="beta",
            enabled=bool(settings.execution_studio_enabled),
            capability_keys=grouped.get("ecommerce_workspace", []),
        ),
    ]
    return workspaces


def compose_capability_registry_snapshot(*, include_disabled: bool = False) -> CapabilityRegistrySnapshotOut:
    """Return read-only capability registry snapshot."""

    capabilities = _capability_catalog()
    workspaces = _workspace_catalog(capabilities)
    if include_disabled:
        return CapabilityRegistrySnapshotOut(
            generated_at=datetime.now(tz=UTC),
            workspaces=workspaces,
            capabilities=capabilities,
        )

    enabled_capabilities = [row for row in capabilities if row.enabled]
    enabled_keys = {row.capability_key for row in enabled_capabilities}
    enabled_workspaces: list[CapabilityWorkspaceOut] = []
    for workspace in workspaces:
        filtered_keys = [key for key in workspace.capability_keys if key in enabled_keys]
        if not workspace.enabled and not filtered_keys:
            continue
        enabled_workspaces.append(
            workspace.model_copy(update={"capability_keys": filtered_keys}),
        )
    return CapabilityRegistrySnapshotOut(
        generated_at=datetime.now(tz=UTC),
        workspaces=enabled_workspaces,
        capabilities=enabled_capabilities,
    )


__all__ = [
    "CapabilityContractOut",
    "CapabilityRegistrySnapshotOut",
    "CapabilityWorkspaceOut",
    "compose_capability_registry_snapshot",
]
