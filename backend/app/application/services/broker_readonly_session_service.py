"""Track P RA4 — Read-only broker session until smoke + guardrails configured."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.broker_guardrails_service import BrokerGuardrailsOut, get_broker_guardrails
from app.application.services.prediction_market_trading import build_prediction_markets_status_snapshot
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

BROKER_READONLY_SETTINGS_KEY = "broker_readonly"
BROKER_READONLY_LANE = "broker_readonly"
TEMPLATE_ID = "broker-readonly-probe"

SmokeStatus = Literal["missing", "passed", "failed"]

GOAL_TEMPLATE = """\
Broker read-only probe (RA4 — portfolio & quotes ONLY).

Verify broker connectivity before any live orders:
1. **Quotes:** Fetch Polymarket Gamma market snapshot (top 3 by volume) — read-only.
2. **Portfolio:** Summarize any read-only balance/position data available via connectors.
3. **Guardrails:** Report tenant broker guardrails status (max order, daily cap, kill switch).
4. **Smoke:** Confirm connectors healthy; never call execute_trade or CLOB order_post.

Skills: broker-readonly-playbook, polymarket-prediction-evaluator, real-money-risk-gate.
Lane: broker_readonly. Orders blocked until operator completes smoke + guardrails in Trading Automation.
""".strip()


class BrokerReadonlyKpiOut(BaseModel):
    """Read-only broker lane KPI for Trading Automation connect tab."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool
    readonly_required: bool = True
    live_eligible: bool = False
    smoke_status: SmokeStatus = "missing"
    smoke_passed_at: datetime | None = None
    smoke_message: str = ""
    guardrails_ready: bool = False
    guardrails_kill_switch: bool = False
    gamma_connector_ready: bool = False
    clob_connector_ready: bool = False
    last_session_id: str | None = None
    last_session_href: str | None = None
    template_id: str = TEMPLATE_ID
    template_href: str = "/swarm-builder?template=broker-readonly-probe"
    session_bootstrap_href: str = "/api/v1/trading-cockpit/readonly-session/bootstrap"
    operator_hint: str = ""
    workspace_href: str = "/apps-tools/trading-automation?section=connect#broker-readonly-session"


class BrokerReadonlySmokeOut(BaseModel):
    """Smoke probe result."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    smoke_status: SmokeStatus
    smoke_passed_at: datetime | None = None
    message: str
    gamma_connector_ready: bool = False
    guardrails_ready: bool = False
    live_eligible: bool = False


class BrokerReadonlyBootstrapOut(BaseModel):
    """Read-only supervisor session bootstrap result."""

    model_config = ConfigDict(extra="forbid")

    ok: bool
    session_id: str | None = None
    session_href: str | None = None
    message: str = ""


class BrokerOrderGateBlock(BaseModel):
    """RA4 live order block."""

    model_config = ConfigDict(extra="forbid")

    reason: str
    detail: str


def _readonly_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    bucket = root.get(BROKER_READONLY_SETTINGS_KEY)
    return dict(bucket) if isinstance(bucket, dict) else {}


def _connector_flags(pm_status: dict[str, Any]) -> tuple[bool, bool]:
    connectors = pm_status.get("connectors_active") if isinstance(pm_status.get("connectors_active"), dict) else {}
    return bool(connectors.get("polymarket_gamma")), bool(connectors.get("polymarket_clob"))


def is_live_broker_eligible(
    *,
    guardrails: BrokerGuardrailsOut,
    readonly_bucket: dict[str, Any],
    gamma_ready: bool,
) -> bool:
    """Return True when live broker orders may proceed (RA3 + RA4 gates)."""

    if not settings.broker_readonly_session_enabled:
        return True
    if guardrails.kill_switch:
        return False
    if guardrails.source != "tenant":
        return False
    if not bool(readonly_bucket.get("smoke_passed")):
        return False
    if not gamma_ready:
        return False
    return True


async def compose_broker_readonly_kpi(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
) -> BrokerReadonlyKpiOut:
    """Compose connect-tab KPI for read-only broker lane."""

    if not settings.broker_readonly_session_enabled:
        return BrokerReadonlyKpiOut(
            enabled=False,
            readonly_required=False,
            live_eligible=True,
            operator_hint="Read-only broker gate disabled — existing live guards apply.",
        )

    tenant = await session.get(Tenant, tenant_id)
    bucket = _readonly_bucket(tenant.operator_settings if tenant else None)
    guardrails = await get_broker_guardrails(session, tenant_id=tenant_id)
    pm_status = await build_prediction_markets_status_snapshot(session, dashboard_user_id=dashboard_user_id)
    gamma_ready, clob_ready = _connector_flags(pm_status)

    smoke_passed = bool(bucket.get("smoke_passed"))
    smoke_status: SmokeStatus = "passed" if smoke_passed else "missing"
    if bucket.get("smoke_failed"):
        smoke_status = "failed"

    guardrails_ready = guardrails.source == "tenant"
    live_eligible = is_live_broker_eligible(
        guardrails=guardrails,
        readonly_bucket=bucket,
        gamma_ready=gamma_ready,
    )
    readonly_required = not live_eligible

    smoke_at_raw = bucket.get("smoke_passed_at")
    smoke_at: datetime | None = None
    if isinstance(smoke_at_raw, str):
        try:
            smoke_at = datetime.fromisoformat(smoke_at_raw.replace("Z", "+00:00"))
        except ValueError:
            smoke_at = None

    last_session_raw = bucket.get("last_session_id")
    last_session_id = str(last_session_raw) if last_session_raw else None
    last_href = f"/agents/sessions/{last_session_id}" if last_session_id else None

    if live_eligible:
        hint = "Smoke + guardrails OK — live orders allowed when RA3/RA5 gates pass."
    elif not gamma_ready:
        hint = "Install polymarket_gamma connector, run smoke probe, then save broker guardrails."
    elif not guardrails_ready:
        hint = "Save broker guardrails (tenant overrides), then run smoke probe."
    elif not smoke_passed:
        hint = "Run read-only smoke probe before any live broker orders."
    elif guardrails.kill_switch:
        hint = "Kill switch is ON — turn off in Broker guardrails to enable live lane."
    else:
        hint = "Complete connect checklist before live trading."

    return BrokerReadonlyKpiOut(
        enabled=True,
        readonly_required=readonly_required,
        live_eligible=live_eligible,
        smoke_status=smoke_status,
        smoke_passed_at=smoke_at,
        smoke_message=str(bucket.get("smoke_message") or ""),
        guardrails_ready=guardrails_ready,
        guardrails_kill_switch=guardrails.kill_switch,
        gamma_connector_ready=gamma_ready,
        clob_connector_ready=clob_ready,
        last_session_id=last_session_id,
        last_session_href=last_href,
        operator_hint=hint,
    )


async def run_broker_readonly_smoke_probe(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
) -> BrokerReadonlySmokeOut:
    """Verify Gamma connector + guardrails before marking smoke passed."""

    if not settings.broker_readonly_session_enabled:
        return BrokerReadonlySmokeOut(
            ok=True,
            smoke_status="passed",
            message="Read-only gate disabled.",
            live_eligible=True,
        )

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        msg = f"Tenant {tenant_id} not found"
        raise ValueError(msg)

    guardrails = await get_broker_guardrails(session, tenant_id=tenant_id)
    pm_status = await build_prediction_markets_status_snapshot(session, dashboard_user_id=dashboard_user_id)
    gamma_ready, _ = _connector_flags(pm_status)
    guardrails_ready = guardrails.source == "tenant"

    now = datetime.now(tz=UTC)
    root = dict(tenant.operator_settings or {})
    bucket = _readonly_bucket(root)

    if not gamma_ready:
        bucket.update(
            {
                "smoke_passed": False,
                "smoke_failed": True,
                "smoke_message": "polymarket_gamma connector not active — install in Integrations.",
                "smoke_passed_at": None,
            },
        )
        root[BROKER_READONLY_SETTINGS_KEY] = bucket
        tenant.operator_settings = root
        await session.flush()
        return BrokerReadonlySmokeOut(
            ok=False,
            smoke_status="failed",
            message=bucket["smoke_message"],
            gamma_connector_ready=False,
            guardrails_ready=guardrails_ready,
            live_eligible=False,
        )

    if not guardrails_ready:
        bucket.update(
            {
                "smoke_passed": False,
                "smoke_failed": True,
                "smoke_message": "Save broker guardrails first (tenant overrides required).",
                "smoke_passed_at": None,
            },
        )
        root[BROKER_READONLY_SETTINGS_KEY] = bucket
        tenant.operator_settings = root
        await session.flush()
        return BrokerReadonlySmokeOut(
            ok=False,
            smoke_status="failed",
            message=bucket["smoke_message"],
            gamma_connector_ready=True,
            guardrails_ready=False,
            live_eligible=False,
        )

    bucket.update(
        {
            "smoke_passed": True,
            "smoke_failed": False,
            "smoke_message": "Gamma connector ready; read-only smoke passed.",
            "smoke_passed_at": now.isoformat(),
        },
    )
    root[BROKER_READONLY_SETTINGS_KEY] = bucket
    tenant.operator_settings = root
    await session.flush()

    live_eligible = is_live_broker_eligible(
        guardrails=guardrails,
        readonly_bucket=bucket,
        gamma_ready=gamma_ready,
    )
    _logger.info(
        "broker_readonly.smoke_passed",
        agent_id="broker_readonly",
        swarm_id=str(tenant_id),
        live_eligible=live_eligible,
    )
    return BrokerReadonlySmokeOut(
        ok=True,
        smoke_status="passed",
        smoke_passed_at=now,
        message=bucket["smoke_message"],
        gamma_connector_ready=True,
        guardrails_ready=True,
        live_eligible=live_eligible,
    )


async def bootstrap_broker_readonly_session(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    created_by_subject: str | None = None,
) -> BrokerReadonlyBootstrapOut:
    """Dispatch read-only supervisor session (portfolio/quotes tools only)."""

    if not settings.broker_readonly_session_enabled:
        return BrokerReadonlyBootstrapOut(ok=False, message="Read-only broker session disabled.")

    from app.application.services.supervisor.session_service import create_supervisor_session
    from app.application.services.supervisor.shared_context import SharedContextService

    guardrails = await get_broker_guardrails(session, tenant_id=tenant_id)
    pm_status = await build_prediction_markets_status_snapshot(session, dashboard_user_id=dashboard_user_id)
    gamma_ready, clob_ready = _connector_flags(pm_status)

    goal = (
        f"{GOAL_TEMPLATE}\n\n"
        f"--- Current status ---\n"
        f"Gamma ready: {gamma_ready}\n"
        f"CLOB ready: {clob_ready}\n"
        f"Guardrails source: {guardrails.source}\n"
        f"Max order USD: {guardrails.max_order_usd}\n"
        f"Daily cap USD: {guardrails.daily_cap_usd}\n"
        f"Kill switch: {guardrails.kill_switch}\n"
    )

    shared = SharedContextService(session)
    sup = await create_supervisor_session(
        session,
        goal=goal,
        created_by_subject=created_by_subject or "operator:broker-readonly",
        runtime_mode="durable",
        roles=["orchestrator", "researcher", "critic"],
        shared_context=shared,
        retrieval_contract="customer_history+policy+last_3_tasks",
        skill_slugs=["broker-readonly-playbook", "polymarket-prediction-evaluator", "real-money-risk-gate"],
        context_seed={
            "lane": BROKER_READONLY_LANE,
            "broker_readonly": True,
            "orders_blocked": True,
            "template_id": TEMPLATE_ID,
        },
        tenant_id=tenant_id,
    )
    await session.flush()

    tenant = await session.get(Tenant, tenant_id)
    if tenant is not None:
        root = dict(tenant.operator_settings or {})
        bucket = _readonly_bucket(root)
        bucket["last_session_id"] = str(sup.id)
        bucket["last_session_at"] = datetime.now(tz=UTC).isoformat()
        root[BROKER_READONLY_SETTINGS_KEY] = bucket
        tenant.operator_settings = root
        await session.flush()

    session_id = str(sup.id)
    _logger.info(
        "broker_readonly.session_bootstrapped",
        agent_id="broker_readonly",
        swarm_id=str(tenant_id),
        task_id=session_id,
    )
    return BrokerReadonlyBootstrapOut(
        ok=True,
        session_id=session_id,
        session_href=f"/agents/sessions/{session_id}",
        message="Read-only broker session started — quotes/portfolio only.",
    )


async def assert_live_broker_allowed(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID | None,
    dashboard_user_id: uuid.UUID,
) -> BrokerOrderGateBlock | None:
    """Return block detail when RA4 live eligibility fails."""

    if not settings.broker_readonly_session_enabled or tenant_id is None:
        return None

    tenant = await session.get(Tenant, tenant_id)
    bucket = _readonly_bucket(tenant.operator_settings if tenant else None)
    guardrails = await get_broker_guardrails(session, tenant_id=tenant_id)
    pm_status = await build_prediction_markets_status_snapshot(session, dashboard_user_id=dashboard_user_id)
    gamma_ready, _ = _connector_flags(pm_status)

    if is_live_broker_eligible(guardrails=guardrails, readonly_bucket=bucket, gamma_ready=gamma_ready):
        return None

    if guardrails.source != "tenant":
        detail = "Configure broker guardrails (tenant overrides) before live orders."
        reason = "guardrails_not_configured"
    elif not bucket.get("smoke_passed"):
        detail = "Run read-only smoke probe in Trading Automation → Connect before live orders."
        reason = "broker_readonly_smoke_required"
    elif not gamma_ready:
        detail = "polymarket_gamma connector required for broker lane."
        reason = "connector_not_ready"
    elif guardrails.kill_switch:
        detail = "Broker kill switch is ON."
        reason = "kill_switch"
    else:
        detail = "Broker read-only gate blocked live execution."
        reason = "broker_readonly_required"

    return BrokerOrderGateBlock(reason=reason, detail=detail)


__all__ = [
    "BROKER_READONLY_LANE",
    "BROKER_READONLY_SETTINGS_KEY",
    "BrokerOrderGateBlock",
    "BrokerReadonlyBootstrapOut",
    "BrokerReadonlyKpiOut",
    "BrokerReadonlySmokeOut",
    "TEMPLATE_ID",
    "assert_live_broker_allowed",
    "bootstrap_broker_readonly_session",
    "compose_broker_readonly_kpi",
    "is_live_broker_eligible",
    "run_broker_readonly_smoke_probe",
]
