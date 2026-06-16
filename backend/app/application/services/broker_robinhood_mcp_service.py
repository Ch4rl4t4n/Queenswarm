"""Track P RA1/RA2 — Robinhood Agentic MCP preset readiness and install checklist."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.broker_guardrails_service import get_broker_guardrails
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.connectors.dynamic.service import DynamicConnectorService
from app.infrastructure.connectors.phase3.catalog import get_phase3_template
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

ROBINHOOD_MCP_TEMPLATE_ID = "robinhood_agentic_mcp"
ROBINHOOD_MCP_SLUG = "robinhood_agentic"
ROBINHOOD_MCP_SERVER_URL = "https://agent.robinhood.com/mcp/trading"
ROBINHOOD_MCP_DOC_PATH = "docs/OPERATOR_ROBINHOOD_MCP_SETUP.md"

ProbeStatus = Literal["missing", "passed", "failed"]


class RobinhoodMcpStepOut(BaseModel):
    """One checklist row for Robinhood MCP install."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    done: bool
    detail: str


class RobinhoodMcpReadinessOut(BaseModel):
    """Robinhood Agentic MCP readiness for Trading Cockpit broker MCP tab."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    template_id: str = ROBINHOOD_MCP_TEMPLATE_ID
    connector_slug: str = ROBINHOOD_MCP_SLUG
    mcp_server_url: str = ROBINHOOD_MCP_SERVER_URL
    preset_available: bool = True
    connector_installed: bool = False
    oauth_ready: bool = False
    guardrails_ready: bool = False
    guardrails_kill_switch: bool = False
    progress_pct: int = 0
    ready: bool = False
    last_probe_at: datetime | None = None
    last_probe_status: ProbeStatus = "missing"
    last_probe_message: str = ""
    steps: list[RobinhoodMcpStepOut] = Field(default_factory=list)
    operator_hint: str = ""
    install_href: str = "/integrations?tab=marketplace&template=robinhood_agentic_mcp"
    vault_href: str = "/integrations?tab=vault&preset=robinhood_agentic"
    docs_href: str = ROBINHOOD_MCP_DOC_PATH
    workspace_href: str = "/apps-tools/trading-automation?section=mcp#broker-mcp"


def _oauth_sealed(payload: dict[str, Any]) -> bool:
    token = payload.get("oauth2_access_token")
    return isinstance(token, str) and bool(token.strip())


async def _connector_flags(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
) -> tuple[bool, bool, datetime | None]:
    """Return installed, oauth_ready, last_tested_at for Robinhood MCP connector."""

    svc = DynamicConnectorService()
    row = await svc.fetch_by_slug(session, slug=ROBINHOOD_MCP_SLUG)
    if row is None or not row.is_active:
        return False, False, None
    secrets = svc._secrets_dict(row)  # noqa: SLF001 — broker lane uses same vault probe as dynamic hub tests
    oauth_ready = _oauth_sealed(secrets)
    tested_at = row.last_tested_at if isinstance(row.last_tested_at, datetime) else None
    _ = dashboard_user_id
    return True, oauth_ready, tested_at


def _build_steps(
    *,
    connector_installed: bool,
    oauth_ready: bool,
    guardrails_ready: bool,
    kill_switch: bool,
    probe_done: bool,
    probe_detail: str,
) -> list[RobinhoodMcpStepOut]:
    return [
        RobinhoodMcpStepOut(
            id="install_preset",
            label="Install marketplace preset",
            done=connector_installed,
            detail=f"Integrations → Marketplace → Robinhood Agentic MCP (slug `{ROBINHOOD_MCP_SLUG}`).",
        ),
        RobinhoodMcpStepOut(
            id="oauth",
            label="Complete Robinhood OAuth",
            done=oauth_ready,
            detail="Seal OAuth access token in Connector Vault after Agentic account authorization.",
        ),
        RobinhoodMcpStepOut(
            id="guardrails",
            label="Configure broker guardrails",
            done=guardrails_ready and not kill_switch,
            detail="Set max order, daily cap, approve mode — shared with Polymarket lane (RA3).",
        ),
        RobinhoodMcpStepOut(
            id="probe",
            label="Run connection probe",
            done=probe_done,
            detail=probe_detail,
        ),
    ]


async def compose_robinhood_mcp_readiness(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
) -> RobinhoodMcpReadinessOut:
    """Build RA1/RA2 Robinhood MCP readiness snapshot."""

    now = datetime.now(tz=UTC)
    if not settings.trading_cockpit_enabled or not settings.robinhood_mcp_preset_enabled:
        return RobinhoodMcpReadinessOut(
            enabled=False,
            generated_at=now,
            operator_hint="Robinhood MCP preset disabled in deployment config.",
        )

    try:
        get_phase3_template(ROBINHOOD_MCP_TEMPLATE_ID)
        preset_available = True
    except ValueError:
        preset_available = False

    connector_installed, oauth_ready, last_tested = await _connector_flags(
        session,
        dashboard_user_id=dashboard_user_id,
    )

    guardrails_ready = False
    kill_switch = False
    if tenant is not None and settings.broker_guardrails_enabled:
        guardrails = await get_broker_guardrails(session, tenant_id=tenant_id)
        guardrails_ready = guardrails.enabled and "robinhood" in guardrails.venues
        kill_switch = guardrails.kill_switch

    bucket: dict[str, Any] = {}
    if tenant is not None:
        root = dict(tenant.operator_settings or {})
        raw = root.get("broker_robinhood_mcp")
        bucket = dict(raw) if isinstance(raw, dict) else {}

    last_probe_status: ProbeStatus = str(bucket.get("last_probe_status") or "missing")  # type: ignore[assignment]
    if last_probe_status not in {"missing", "passed", "failed"}:
        last_probe_status = "missing"
    last_probe_at_raw = bucket.get("last_probe_at")
    last_probe_at: datetime | None = None
    if isinstance(last_probe_at_raw, str) and last_probe_at_raw.strip():
        try:
            last_probe_at = datetime.fromisoformat(last_probe_at_raw.replace("Z", "+00:00"))
        except ValueError:
            last_probe_at = None
    elif last_tested is not None and last_probe_at is None and connector_installed and oauth_ready:
        last_probe_at = last_tested
        if last_probe_status == "missing":
            last_probe_status = "passed"

    probe_detail = str(bucket.get("last_probe_message") or "Test connector from Broker MCP tab — records last probe timestamp.")
    probe_done = last_probe_status == "passed"
    steps = _build_steps(
        connector_installed=connector_installed,
        oauth_ready=oauth_ready,
        guardrails_ready=guardrails_ready,
        kill_switch=kill_switch,
        probe_done=probe_done,
        probe_detail=probe_detail,
    )

    done_count = sum(1 for step in steps if step.done)
    progress_pct = int(round(100 * done_count / max(len(steps), 1)))
    ready = connector_installed and oauth_ready and guardrails_ready and not kill_switch and last_probe_status == "passed"

    if not preset_available:
        hint = "Robinhood MCP catalog template missing — redeploy backend with RA1 preset."
    elif kill_switch:
        hint = "Broker kill switch ON — resolve in Guardrails before Robinhood MCP live lane."
    elif ready:
        hint = "Robinhood Agentic MCP ready — route orders through HITL queue (RA5) before live."
    elif not connector_installed:
        hint = "Install Robinhood Agentic MCP preset from Marketplace, then complete OAuth."
    elif not oauth_ready:
        hint = "Connector installed — seal Robinhood OAuth token in Connector Vault."
    elif not guardrails_ready:
        hint = "Enable Robinhood venue in broker guardrails before live MCP orders."
    else:
        hint = "Run connection probe after OAuth — simulate-first before any live order."

    return RobinhoodMcpReadinessOut(
        enabled=True,
        generated_at=now,
        preset_available=preset_available,
        connector_installed=connector_installed,
        oauth_ready=oauth_ready,
        guardrails_ready=guardrails_ready,
        guardrails_kill_switch=kill_switch,
        progress_pct=progress_pct,
        ready=ready,
        last_probe_at=last_probe_at,
        last_probe_status=last_probe_status,
        last_probe_message=str(bucket.get("last_probe_message") or ""),
        steps=steps,
        operator_hint=hint,
    )


async def run_robinhood_mcp_probe(
    session: AsyncSession,
    *,
    tenant: Tenant,
    dashboard_user_id: uuid.UUID,
) -> dict[str, Any]:
    """Record a lightweight Robinhood MCP readiness probe (no live orders)."""

    readiness = await compose_robinhood_mcp_readiness(
        session,
        tenant_id=tenant.id,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
    )
    now = datetime.now(tz=UTC)
    ok = readiness.connector_installed and readiness.oauth_ready and not readiness.guardrails_kill_switch
    status: ProbeStatus = "passed" if ok else "failed"
    message = (
        "Robinhood MCP connector installed with OAuth sealed."
        if ok
        else readiness.operator_hint
    )

    root = dict(tenant.operator_settings or {})
    root["broker_robinhood_mcp"] = {
        "last_probe_at": now.isoformat(),
        "last_probe_status": status,
        "last_probe_message": message,
    }
    tenant.operator_settings = root
    await session.flush()

    _logger.info(
        "broker_robinhood_mcp.probe",
        agent_id=str(dashboard_user_id),
        swarm_id=str(tenant.id),
        task_id="probe",
        ok=ok,
        status=status,
    )
    return {
        "ok": ok,
        "status": status,
        "message": message,
        "last_probe_at": now.isoformat(),
    }


__all__ = [
    "ROBINHOOD_MCP_SERVER_URL",
    "ROBINHOOD_MCP_SLUG",
    "ROBINHOOD_MCP_TEMPLATE_ID",
    "RobinhoodMcpReadinessOut",
    "compose_robinhood_mcp_readiness",
    "run_robinhood_mcp_probe",
]
