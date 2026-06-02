"""Viability gate — block Innovation Lab → Maintainer handoff when unsafe or underspecified."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.queen_maintainer.maintainer_guard import maintainer_run_precheck
from app.application.services.queen_maintainer.pr_workflow import validate_changed_paths
from app.application.services.queen_maintainer.pre_tool_denylist import scan_maintainer_text_for_violations
from app.core.config import settings
from app.infrastructure.persistence.models.agent_suggestion import AgentSuggestion

GateStatus = Literal["pass", "warn", "block"]


class ViabilityCheckItem(BaseModel):
    """Single viability dimension."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    status: GateStatus
    detail: str


class InnovationViabilityOut(BaseModel):
    """Aggregated viability assessment for one innovation proposal."""

    model_config = ConfigDict(extra="ignore")

    ok: bool
    status: GateStatus
    proposal_id: str
    checks: list[ViabilityCheckItem] = Field(default_factory=list)
    blocked_reasons: list[str] = Field(default_factory=list)


def _check(
    *,
    check_id: str,
    label: str,
    ok: bool,
    detail_ok: str,
    detail_fail: str,
    warn: bool = False,
) -> ViabilityCheckItem:
    if ok:
        return ViabilityCheckItem(id=check_id, label=label, status="pass", detail=detail_ok)
    if warn:
        return ViabilityCheckItem(id=check_id, label=label, status="warn", detail=detail_fail)
    return ViabilityCheckItem(id=check_id, label=label, status="block", detail=detail_fail)


async def assess_innovation_viability(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    proposal: AgentSuggestion,
    acknowledge_high_risk: bool = False,
) -> InnovationViabilityOut:
    """Evaluate whether an approved proposal may queue Queen Maintainer safely."""

    checks: list[ViabilityCheckItem] = []
    blocked: list[str] = []
    payload = dict(proposal.proposal_payload or {})
    plan = str(payload.get("implementation_plan_md") or "").strip()
    paths = [str(p) for p in list(payload.get("suggested_paths") or []) if str(p).strip()]
    source = str(payload.get("source_prompt") or proposal.description or "").strip()
    trust_lane = str(payload.get("trust_lane") or "simulate")

    if not settings.hive_innovation_lab_enabled:
        checks.append(_check(
            check_id="innovation_lab",
            label="Innovation Lab",
            ok=False,
            detail_ok="enabled",
            detail_fail="Hive Innovation Lab is disabled.",
        ))
        blocked.append("innovation_lab_disabled")
    else:
        checks.append(_check(
            check_id="innovation_lab",
            label="Innovation Lab",
            ok=True,
            detail_ok="Enabled",
            detail_fail="",
        ))

    maintainer_on = settings.queen_maintainer_enabled
    checks.append(_check(
        check_id="maintainer",
        label="Queen Maintainer",
        ok=maintainer_on,
        detail_ok="Enabled (PR-only)",
        detail_fail="Set QUEEN_MAINTAINER_ENABLED=true to queue implementation.",
    ))
    if not maintainer_on:
        blocked.append("queen_maintainer_disabled")

    approved_ok = proposal.status == "approved"
    checks.append(_check(
        check_id="approved",
        label="Operator approval",
        ok=approved_ok,
        detail_ok="Approved",
        detail_fail=f"Status is {proposal.status!r} — approve before Implement.",
    ))
    if not approved_ok:
        blocked.append("not_approved")

    plan_ok = len(plan) >= 80
    checks.append(_check(
        check_id="plan",
        label="Implementation plan",
        ok=plan_ok,
        detail_ok="Plan present",
        detail_fail="Plan too short — brainstorm again with clearer scope.",
    ))
    if not plan_ok:
        blocked.append("plan_too_short")

    source_ok = len(source) >= 16
    checks.append(_check(
        check_id="source",
        label="Source prompt",
        ok=source_ok,
        detail_ok="Source captured",
        detail_fail="Missing source prompt context.",
    ))
    if not source_ok:
        blocked.append("source_missing")

    simulate_ok = trust_lane == "simulate"
    checks.append(_check(
        check_id="trust_lane",
        label="Trust lane",
        ok=simulate_ok,
        detail_ok="simulate-first",
        detail_fail=f"Trust lane {trust_lane!r} must be simulate for auto-implement.",
    ))
    if not simulate_ok:
        blocked.append("trust_lane_not_simulate")

    risk = str(proposal.risk_level or "medium").lower()
    high_risk = risk == "high"
    high_ok = not high_risk or acknowledge_high_risk
    checks.append(_check(
        check_id="risk",
        label="Risk level",
        ok=high_ok,
        detail_ok=f"Risk {risk}",
        detail_fail="High risk — confirm with acknowledge_high_risk before Implement.",
        warn=high_risk and acknowledge_high_risk,
    ))
    if high_risk and not acknowledge_high_risk:
        blocked.append("high_risk_unacknowledged")

    if paths:
        allowed, blocked_paths = validate_changed_paths(paths)
        checks.append(_check(
            check_id="paths",
            label="Suggested paths",
            ok=allowed,
            detail_ok=f"{len(paths)} path(s) within Maintainer allowlist",
            detail_fail=f"Blocked paths: {', '.join(blocked_paths[:6])}",
        ))
        if not allowed:
            blocked.append("paths_denylisted")
    else:
        checks.append(_check(
            check_id="paths",
            label="Suggested paths",
            ok=True,
            detail_ok="No explicit paths — Maintainer uses plan text",
            detail_fail="",
            warn=True,
        ))

    combined_text = f"{plan}\n{source}\n{proposal.title}\n{proposal.description}"
    violations = scan_maintainer_text_for_violations(combined_text)
    checks.append(_check(
        check_id="pre_tool",
        label="Pre-tool safety scan",
        ok=not violations,
        detail_ok="No blocked command patterns",
        detail_fail=f"Blocked patterns: {', '.join(violations[:4])}",
    ))
    if violations:
        blocked.append("pre_tool_denylist")

    precheck: dict[str, Any] = {"ok": False}
    if tenant_id is not None:
        precheck = await maintainer_run_precheck(session, tenant_id=tenant_id)
    precheck_ok = bool(precheck.get("ok"))
    checks.append(_check(
        check_id="budget",
        label="Maintainer daily budget",
        ok=precheck_ok,
        detail_ok=str(precheck.get("remaining_runs_today", "ok")),
        detail_fail=str(precheck.get("message") or precheck.get("error") or "Daily limit reached"),
    ))
    if not precheck_ok:
        blocked.append(str(precheck.get("error") or "maintainer_precheck_failed"))

    already = proposal.implemented_at is not None
    if already:
        checks.append(_check(
            check_id="duplicate",
            label="Implementation state",
            ok=False,
            detail_ok="Not yet implemented",
            detail_fail="Already queued — check Agents → sessions for Maintainer run.",
        ))
        blocked.append("already_implemented")

    has_block = any(c.status == "block" for c in checks) or bool(blocked)
    has_warn = any(c.status == "warn" for c in checks)
    status: GateStatus = "block" if has_block else ("warn" if has_warn else "pass")

    return InnovationViabilityOut(
        ok=not has_block,
        status=status,
        proposal_id=str(proposal.id),
        checks=checks,
        blocked_reasons=list(dict.fromkeys(blocked)),
    )


__all__ = [
    "InnovationViabilityOut",
    "ViabilityCheckItem",
    "assess_innovation_viability",
]
