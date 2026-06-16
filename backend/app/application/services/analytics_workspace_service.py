"""Track L — Analytics Workspace snapshot (DA3 + DA11)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings


class AnalyticsConnectorSlotOut(BaseModel):
    """Readiness row for one analytics data source."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    ready: bool
    mode: str = "read_only"
    detail: str


class AnalyticsPanelOut(BaseModel):
    """Lazy-load panel descriptor for Apps & Tools analytics module."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    lazy: bool = True
    status: str = "ready"


class AnalyticsWorkspaceActionOut(BaseModel):
    """Operator CTA from snapshot."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    href: str
    detail: str


class AnalyticsWorkspaceSnapshotOut(BaseModel):
    """Single cached read for `/analytics-workspace/snapshot`."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    generated_at: datetime
    capability_key: str = "apps.analytics.decision_report.v1"
    template_id: str = "business-analytics-report"
    skill_slugs: list[str] = Field(default_factory=list)
    swarm_template_built: bool = False
    panels: list[AnalyticsPanelOut] = Field(default_factory=list)
    connector_slots: list[AnalyticsConnectorSlotOut] = Field(default_factory=list)
    actions: list[AnalyticsWorkspaceActionOut] = Field(default_factory=list)
    operator_hint: str = ""


def _default_panels() -> list[AnalyticsPanelOut]:
    return [
        AnalyticsPanelOut(id="overview", label="Overview", lazy=False, status="ready"),
        AnalyticsPanelOut(id="question", label="Business question", lazy=True, status="ready"),
        AnalyticsPanelOut(id="report", label="Report artifact", lazy=True, status="ready"),
        AnalyticsPanelOut(id="lineage", label="Data lineage", lazy=True, status="ready"),
        AnalyticsPanelOut(id="export", label="Export inbox", lazy=True, status="ready"),
    ]


def _default_connectors() -> list[AnalyticsConnectorSlotOut]:
    return [
        AnalyticsConnectorSlotOut(
            id="ga4",
            label="GA4 Data API",
            ready=bool(settings.execution_studio_enabled),
            detail="Read-only via ga4-analytics-playbook.",
        ),
        AnalyticsConnectorSlotOut(
            id="google_sheets",
            label="Google Sheets read",
            ready=bool(settings.execution_studio_enabled),
            detail="Spreadsheet metrics via MCP read scope.",
        ),
        AnalyticsConnectorSlotOut(
            id="warehouse_mcp",
            label="Warehouse MCP slot",
            ready=False,
            detail="Databricks-ready read slot — configure in Integrations.",
        ),
        AnalyticsConnectorSlotOut(
            id="notion_export",
            label="Notion export staging",
            ready=bool(settings.execution_studio_enabled),
            detail="Simulate-first page payload after critic ≥4/5.",
        ),
    ]


def _default_actions(*, swarm_built: bool) -> list[AnalyticsWorkspaceActionOut]:
    return [
        AnalyticsWorkspaceActionOut(
            id="build_template",
            label="Build analytics swarm" if not swarm_built else "Open analytics swarm",
            href="/swarm-builder?template=business-analytics-report",
            detail="DA1 five-bee Codex pipeline preset.",
        ),
        AnalyticsWorkspaceActionOut(
            id="research_alias",
            label="Research Workspace",
            href="/apps-tools/research-workspace",
            detail="Qualitative briefing lane — complements metrics reports.",
        ),
        AnalyticsWorkspaceActionOut(
            id="foragers",
            label="Forager monitors",
            href="/foragers",
            detail="Goldmine delta alerts feed analyst context.",
        ),
    ]


async def compose_analytics_workspace_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> AnalyticsWorkspaceSnapshotOut:
    """Compose analytics workspace snapshot — single BE read for module shell."""

    _ = tenant_id
    if not settings.analytics_workspace_enabled:
        return AnalyticsWorkspaceSnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            operator_hint="Analytics workspace disabled — set ANALYTICS_WORKSPACE_ENABLED=true.",
        )

    swarm_built = False
    try:
        from app.application.services.virtual_company_swarm_builder import list_built_wizard_templates

        built = await list_built_wizard_templates(session)
        swarm_built = "business-analytics-report" in built
    except Exception:
        swarm_built = False

    return AnalyticsWorkspaceSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        skill_slugs=[
            "business-analytics-playbook",
            "ga4-analytics-playbook",
            "self-review-loop",
        ],
        swarm_template_built=swarm_built,
        panels=_default_panels(),
        connector_slots=_default_connectors(),
        actions=_default_actions(swarm_built=swarm_built),
        operator_hint=(
            "Dispatch business-analytics-report template → fetch read-only metrics → "
            "critic rubric ≥4/5 → export simulate."
        ),
    )


__all__ = [
    "AnalyticsConnectorSlotOut",
    "AnalyticsPanelOut",
    "AnalyticsWorkspaceActionOut",
    "AnalyticsWorkspaceSnapshotOut",
    "compose_analytics_workspace_snapshot",
]
