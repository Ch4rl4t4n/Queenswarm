"""Track L DA7 — Analytics connector profiles (GA4 · Sheets · warehouse MCP)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.analytics_workspace_service import AnalyticsConnectorSlotOut
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService, _secrets_configured
from app.infrastructure.connectors.phase3.catalog import get_phase3_template
from app.infrastructure.connectors.phase3.marketplace_meta import marketplace_meta_for
from app.infrastructure.persistence.models.dynamic_connector import DynamicConnector

_logger = get_logger(__name__)

ConnectorProfileStatus = Literal[
    "active",
    "needs_credentials",
    "ready_to_test",
    "inactive",
    "not_installed",
]


@dataclass(frozen=True, slots=True)
class AnalyticsConnectorProfileSpec:
    """Static analytics connector profile definition."""

    id: str
    label: str
    template_id: str | None
    expected_slugs: tuple[str, ...]
    mode: str
    skill_slug: str
    tools: tuple[str, ...]
    configure_href: str
    detail: str


ANALYTICS_CONNECTOR_SPECS: tuple[AnalyticsConnectorProfileSpec, ...] = (
    AnalyticsConnectorProfileSpec(
        id="ga4",
        label="GA4 Data API",
        template_id="ga4_data_api",
        expected_slugs=("ga4_data", "ga4_data_api"),
        mode="read_only",
        skill_slug="ga4-analytics-playbook",
        tools=("get_metadata", "run_report", "run_realtime_report"),
        configure_href="/integrations?tab=hub&hubSection=templates&highlight=ga4_data_api",
        detail="OAuth analytics.readonly — property ID required for runReport.",
    ),
    AnalyticsConnectorProfileSpec(
        id="google_sheets",
        label="Google Sheets read",
        template_id=None,
        expected_slugs=("google_sheets_read", "sheets_mcp", "google_sheets"),
        mode="read_only",
        skill_slug="business-analytics-playbook",
        tools=("read_range", "list_sheets"),
        configure_href="/integrations?tab=hub&hubSection=roster",
        detail="MCP read scope for spreadsheet metrics — never mutate workbook structure.",
    ),
    AnalyticsConnectorProfileSpec(
        id="warehouse_mcp",
        label="Warehouse MCP slot",
        template_id=None,
        expected_slugs=("warehouse_mcp", "databricks_mcp", "snowflake_mcp"),
        mode="read_only",
        skill_slug="business-analytics-playbook",
        tools=("run_query",),
        configure_href="/integrations?tab=hub&hubSection=templates",
        detail="Databricks/Snowflake read-only SQL slot — SELECT-only guardrails.",
    ),
    AnalyticsConnectorProfileSpec(
        id="notion_export",
        label="Notion export staging",
        template_id="notion_workspace",
        expected_slugs=("notion_workspace",),
        mode="simulate_first",
        skill_slug="business-analytics-playbook",
        tools=("create_page",),
        configure_href="/integrations?tab=hub&hubSection=templates&highlight=notion_workspace",
        detail="Simulate-first page payload after critic rubric ≥4/5.",
    ),
)


class AnalyticsConnectorProfileOut(BaseModel):
    """One analytics connector profile row."""

    model_config = ConfigDict(extra="forbid")

    id: str
    label: str
    mode: str
    ready: bool
    status: ConnectorProfileStatus
    connector_slug: str | None = None
    template_id: str | None = None
    skill_slug: str
    tools: list[str] = Field(default_factory=list)
    property_hint: str = ""
    configure_href: str
    test_href: str | None = None
    detail: str = ""
    last_tested_at: str | None = None
    doc_url: str | None = None


class AnalyticsConnectorProfileSnapshotOut(BaseModel):
    """Connector profile snapshot for analytics workspace."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    generated_at: datetime
    profiles: list[AnalyticsConnectorProfileOut] = Field(default_factory=list)
    ready_count: int = 0
    operator_hint: str = ""


def _connection_status(row: DynamicConnector, *, secrets_ok: bool) -> ConnectorProfileStatus:
    if row.is_active and secrets_ok:
        return "active"
    if not secrets_ok:
        return "needs_credentials"
    if secrets_ok and not row.is_active:
        return "ready_to_test"
    return "inactive"


def _property_hint_from_secrets(secrets: dict[str, object]) -> str:
    for key in ("ga4_property_id", "property_id", "default_property_id", "analytics_property_id"):
        raw = secrets.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()[:64]
    return ""


def _resolve_profile_row(
    spec: AnalyticsConnectorProfileSpec,
    *,
    slug_to_row: dict[str, DynamicConnector],
    svc: DynamicConnectorService,
) -> AnalyticsConnectorProfileOut:
    matched_slug: str | None = None
    matched_row: DynamicConnector | None = None
    for slug in spec.expected_slugs:
        row = slug_to_row.get(slug.lower())
        if row is not None:
            matched_slug = row.slug
            matched_row = row
            break

    doc_url: str | None = None
    if spec.template_id:
        template = get_phase3_template(spec.template_id)
        meta = marketplace_meta_for(spec.template_id)
        doc_url = (
            str(meta.get("service_homepage") or "")
            or (template.documentation_url if template else None)
            or None
        )

    if matched_row is None:
        return AnalyticsConnectorProfileOut(
            id=spec.id,
            label=spec.label,
            mode=spec.mode,
            ready=False,
            status="not_installed",
            template_id=spec.template_id,
            skill_slug=spec.skill_slug,
            tools=list(spec.tools),
            configure_href=spec.configure_href,
            detail=spec.detail,
            doc_url=doc_url,
        )

    secrets = svc._secrets_dict(matched_row)  # noqa: SLF001
    secrets_ok = _secrets_configured(matched_row.auth_type, secrets)
    status = _connection_status(matched_row, secrets_ok=secrets_ok)
    tested_at = matched_row.last_tested_at
    last_tested = tested_at.isoformat() if isinstance(tested_at, datetime) else None

    return AnalyticsConnectorProfileOut(
        id=spec.id,
        label=spec.label,
        mode=spec.mode,
        ready=status == "active",
        status=status,
        connector_slug=matched_slug,
        template_id=spec.template_id,
        skill_slug=spec.skill_slug,
        tools=list(spec.tools),
        property_hint=_property_hint_from_secrets(secrets),
        configure_href=f"/integrations?tab=hub&hubSection=roster&highlight={matched_slug}",
        test_href=f"/integrations?tab=hub&hubSection=roster&highlight={matched_slug}",
        detail=spec.detail,
        last_tested_at=last_tested,
        doc_url=doc_url,
    )


async def compose_analytics_connector_profile_snapshot(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
) -> AnalyticsConnectorProfileSnapshotOut:
    """Resolve live connector readiness for analytics fetch lane."""

    if not settings.analytics_connector_profile_enabled:
        return AnalyticsConnectorProfileSnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            operator_hint="Analytics connector profile disabled.",
        )

    svc = DynamicConnectorService()
    owned = list(
        (
            await session.scalars(
                select(DynamicConnector).where(DynamicConnector.dashboard_user_id == dashboard_user_id),
            )
        ).all(),
    )
    slug_to_row = {row.slug.lower(): row for row in owned}

    profiles = [
        _resolve_profile_row(spec, slug_to_row=slug_to_row, svc=svc)
        for spec in ANALYTICS_CONNECTOR_SPECS
    ]
    ready_count = sum(1 for row in profiles if row.ready)
    _logger.info(
        "analytics_connector_profile.snapshot",
        agent_id="analytics_connector_profile",
        swarm_id=str(dashboard_user_id),
        ready_count=ready_count,
        profile_count=len(profiles),
    )
    return AnalyticsConnectorProfileSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        profiles=profiles,
        ready_count=ready_count,
        operator_hint=(
            "Read-only connectors only — configure GA4 + Sheets + warehouse MCP in Integrations, "
            "then dispatch business-analytics-report."
        ),
    )


def connector_slots_from_profiles(profiles: list[AnalyticsConnectorProfileOut]) -> list[AnalyticsConnectorSlotOut]:
    """Map profile snapshot into legacy connector slot rows for workspace shell."""

    return [
        AnalyticsConnectorSlotOut(
            id=profile.id,
            label=profile.label,
            ready=profile.ready,
            mode=profile.mode,
            detail=profile.detail if profile.ready else f"{profile.detail} Status: {profile.status}.",
        )
        for profile in profiles
    ]


__all__ = [
    "AnalyticsConnectorProfileOut",
    "AnalyticsConnectorProfileSnapshotOut",
    "ANALYTICS_CONNECTOR_SPECS",
    "compose_analytics_connector_profile_snapshot",
    "connector_slots_from_profiles",
]
