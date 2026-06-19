"""LOOP2 — Closed-loop guardrails: max turns, min score, cost cap per session."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.queen_maintainer.maintainer_guard import is_maintainer_session
from app.application.services.session_cost_guardian import (
    DEFAULT_SESSION_CAP_USD,
    DEFAULT_WARN_RATIO,
    measure_session_cost,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.supervisor_session import (
    SupervisorSession,
    SupervisorSessionEvent,
)

_logger = get_logger(__name__)

LOOP_GUARDRAILS_SETTINGS_KEY = "loop_guardrails"
SloStatus = Literal["healthy", "warn", "halt"]
PolicySource = Literal["deployment", "tenant"]

MAX_TURNS_MIN = 1
MAX_TURNS_MAX = 25
MIN_SCORE_MIN = 0.0
MIN_SCORE_MAX = 1.0
COST_CAP_MIN = 0.05
COST_CAP_MAX = 50.0


class LoopGuardrailsPolicyOut(BaseModel):
    """Tenant-default closed-loop guardrails."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    max_turns: int = 5
    min_score: float = 0.8
    cost_cap_usd: float = DEFAULT_SESSION_CAP_USD
    cost_warn_ratio: float = DEFAULT_WARN_RATIO
    source: PolicySource = "deployment"
    updated_at: datetime | None = None

    @field_validator("max_turns")
    @classmethod
    def _clamp_turns(cls, value: int) -> int:
        return max(MAX_TURNS_MIN, min(int(value), MAX_TURNS_MAX))

    @field_validator("min_score")
    @classmethod
    def _clamp_score(cls, value: float) -> float:
        return max(MIN_SCORE_MIN, min(float(value), MIN_SCORE_MAX))

    @field_validator("cost_cap_usd")
    @classmethod
    def _clamp_cap(cls, value: float) -> float:
        return max(COST_CAP_MIN, min(float(value), COST_CAP_MAX))

    @field_validator("cost_warn_ratio")
    @classmethod
    def _clamp_warn(cls, value: float) -> float:
        return max(0.1, min(float(value), 1.0))


class LoopGuardrailsPolicyPatchIn(BaseModel):
    """Operator PATCH body for tenant loop guardrails."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool | None = None
    max_turns: int | None = Field(default=None, ge=MAX_TURNS_MIN, le=MAX_TURNS_MAX)
    min_score: float | None = Field(default=None, ge=MIN_SCORE_MIN, le=MIN_SCORE_MAX)
    cost_cap_usd: float | None = Field(default=None, ge=COST_CAP_MIN, le=COST_CAP_MAX)
    cost_warn_ratio: float | None = Field(default=None, ge=0.1, le=1.0)


class SessionLoopGuardrailsStateOut(BaseModel):
    """Live guardrail state for one supervisor session."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    status: SloStatus = "healthy"
    max_turns: int = 5
    turns_used: int = 0
    min_score: float = 0.8
    min_score_label: str = "4.0/5"
    last_rubric_score: float | None = None
    cost_cap_usd: float = DEFAULT_SESSION_CAP_USD
    spent_usd: float = 0.0
    cost_utilization: float = 0.0
    alerts: list[str] = Field(default_factory=list)
    next_operator_action: str = "Loop guardrails inactive."


def _deployment_defaults() -> LoopGuardrailsPolicyOut:
    """Deployment-level defaults from Settings."""

    return LoopGuardrailsPolicyOut(
        enabled=settings.loop_guardrails_enabled,
        max_turns=settings.loop_guardrails_default_max_turns,
        min_score=settings.loop_guardrails_default_min_score,
        cost_cap_usd=float(settings.loop_guardrails_default_cost_cap_usd),
        cost_warn_ratio=float(settings.loop_guardrails_default_cost_warn_ratio),
        source="deployment",
    )


def _policy_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    bucket = root.get(LOOP_GUARDRAILS_SETTINGS_KEY)
    return dict(bucket) if isinstance(bucket, dict) else {}


def _policy_from_bucket(bucket: dict[str, Any]) -> LoopGuardrailsPolicyOut:
    """Merge tenant bucket over deployment defaults."""

    base = _deployment_defaults()
    if not bucket:
        return base
    merged = base.model_copy(
        update={
            "enabled": bool(bucket.get("enabled", base.enabled)),
            "max_turns": int(bucket.get("max_turns", base.max_turns)),
            "min_score": float(bucket.get("min_score", base.min_score)),
            "cost_cap_usd": float(bucket.get("cost_cap_usd", base.cost_cap_usd)),
            "cost_warn_ratio": float(bucket.get("cost_warn_ratio", base.cost_warn_ratio)),
            "source": "tenant",
            "updated_at": bucket.get("updated_at"),
        },
    )
    return LoopGuardrailsPolicyOut.model_validate(merged.model_dump(mode="python"))


async def get_loop_guardrails_policy(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> LoopGuardrailsPolicyOut:
    """Load tenant loop guardrails policy."""

    from app.infrastructure.persistence.models.tenant import Tenant

    tenant = await session.get(Tenant, tenant_id)
    bucket = _policy_bucket(tenant.operator_settings if tenant else None)
    return _policy_from_bucket(bucket)


async def save_loop_guardrails_policy(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    patch: LoopGuardrailsPolicyPatchIn,
) -> LoopGuardrailsPolicyOut:
    """Persist tenant loop guardrails overrides."""

    from app.infrastructure.persistence.models.tenant import Tenant

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        msg = f"Tenant {tenant_id} not found"
        raise ValueError(msg)

    current = await get_loop_guardrails_policy(session, tenant_id=tenant_id)
    data = current.model_dump(mode="python")
    for key, value in patch.model_dump(exclude_unset=True).items():
        if value is not None:
            data[key] = value
    data["source"] = "tenant"
    data["updated_at"] = datetime.now(tz=UTC).isoformat()
    saved = LoopGuardrailsPolicyOut.model_validate(data)

    root = dict(tenant.operator_settings or {})
    root[LOOP_GUARDRAILS_SETTINGS_KEY] = {
        "enabled": saved.enabled,
        "max_turns": saved.max_turns,
        "min_score": saved.min_score,
        "cost_cap_usd": saved.cost_cap_usd,
        "cost_warn_ratio": saved.cost_warn_ratio,
        "updated_at": saved.updated_at,
    }
    tenant.operator_settings = root
    await session.flush()
    _logger.info(
        "loop_guardrails.policy_saved",
        agent_id="loop_guardrails",
        swarm_id=str(tenant_id),
        enabled=saved.enabled,
        max_turns=saved.max_turns,
    )
    return saved


def min_score_to_five_scale(min_score: float) -> str:
    """Render 0–1 min score as x/5 label."""

    return f"{min_score * 5:.1f}/5"


def is_loop_guardrails_active(context_summary: dict[str, Any] | None) -> bool:
    """Return True when closed-loop guardrails apply to this session."""

    if not isinstance(context_summary, dict):
        return False
    if is_maintainer_session(context_summary):
        return False
    return bool(context_summary.get("loop_guardrails_enabled", settings.loop_guardrails_enabled))


def build_loop_guardrails_context_seed(policy: LoopGuardrailsPolicyOut) -> dict[str, object]:
    """Context seed keys merged into supervisor session summary."""

    if not policy.enabled:
        return {"loop_guardrails_enabled": False}
    return {
        "loop_guardrails_enabled": True,
        "loop_max_turns": policy.max_turns,
        "loop_min_score": policy.min_score,
        "session_cost_cap_usd": policy.cost_cap_usd,
        "session_cost_warn_ratio": policy.cost_warn_ratio,
        "loop_guardrails_policy_source": policy.source,
    }


async def apply_loop_guardrails_to_summary(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    summary: dict[str, object],
) -> dict[str, object]:
    """Inject tenant loop guardrails unless session already defines caps (e.g. Maintainer)."""

    if is_maintainer_session(summary):
        return summary
    if summary.get("session_cost_cap_usd") is not None and summary.get("loop_max_turns") is not None:
        return summary
    policy = await get_loop_guardrails_policy(session, tenant_id=tenant_id)
    merged = dict(summary)
    merged.update(build_loop_guardrails_context_seed(policy))
    return merged


def loop_max_turns_from_summary(context_summary: dict[str, Any] | None) -> int:
    """Resolve max turns from session context."""

    if not isinstance(context_summary, dict):
        return settings.loop_guardrails_default_max_turns
    raw = context_summary.get("loop_max_turns")
    if isinstance(raw, int) and MAX_TURNS_MIN <= raw <= MAX_TURNS_MAX:
        return raw
    return settings.loop_guardrails_default_max_turns


def loop_min_score_from_summary(context_summary: dict[str, Any] | None) -> float:
    """Resolve minimum rubric score (0–1) from session context."""

    if not isinstance(context_summary, dict):
        return settings.loop_guardrails_default_min_score
    raw = context_summary.get("loop_min_score")
    if isinstance(raw, (int, float)):
        return max(MIN_SCORE_MIN, min(float(raw), MIN_SCORE_MAX))
    return settings.loop_guardrails_default_min_score


def loop_cost_cap_from_summary(context_summary: dict[str, Any] | None) -> float:
    """Resolve session cost cap from loop guardrails context."""

    if not isinstance(context_summary, dict):
        return float(settings.loop_guardrails_default_cost_cap_usd)
    raw = context_summary.get("session_cost_cap_usd")
    if isinstance(raw, (int, float)) and raw > 0:
        return float(raw)
    return float(settings.loop_guardrails_default_cost_cap_usd)


def loop_cost_warn_ratio_from_summary(context_summary: dict[str, Any] | None) -> float:
    """Resolve warn ratio for session cost guardian."""

    if not isinstance(context_summary, dict):
        return float(settings.loop_guardrails_default_cost_warn_ratio)
    raw = context_summary.get("session_cost_warn_ratio")
    if isinstance(raw, (int, float)):
        return max(0.1, min(float(raw), 1.0))
    return float(settings.loop_guardrails_default_cost_warn_ratio)


def last_rubric_score_from_summary(context_summary: dict[str, Any] | None) -> float | None:
    """Read last rubric score stored on session context (0–1)."""

    if not isinstance(context_summary, dict):
        return None
    raw = context_summary.get("loop_last_rubric_score")
    if isinstance(raw, (int, float)):
        return max(0.0, min(float(raw), 1.0))
    return None


async def count_session_loop_turns(
    session: AsyncSession,
    *,
    session_id: uuid.UUID,
) -> int:
    """Count completed sub-agent turns for loop cap enforcement."""

    count = await session.scalar(
        select(func.count())
        .select_from(SupervisorSessionEvent)
        .where(
            SupervisorSessionEvent.supervisor_session_id == session_id,
            SupervisorSessionEvent.event_type == "sub_agent_completed",
        ),
    )
    return int(count or 0)


def append_loop_guardrails_goal_footer(goal: str, *, policy: LoopGuardrailsPolicyOut) -> str:
    """Append operator-facing loop guardrails to session goal."""

    if not policy.enabled:
        return goal
    return (
        f"{goal.rstrip()}\n\n"
        "--- Closed-loop guardrails (mandatory) ---\n"
        f"- Max turns: {policy.max_turns} sub-agent completions — stop and return plan if reached.\n"
        f"- Min rubric score: {min_score_to_five_scale(policy.min_score)} before operator approve.\n"
        f"- Session LLM cap: ${policy.cost_cap_usd:.2f} — halt if exceeded.\n"
        "- Simulate-first; no live publish or financial actions without gates.\n"
    )


def _resolve_loop_status(
    *,
    turns_used: int,
    max_turns: int,
    cost_state: str,
    min_score: float,
    last_score: float | None,
) -> tuple[SloStatus, list[str], str]:
    """Derive aggregate loop guardrail status."""

    alerts: list[str] = []
    if cost_state == "halt":
        alerts.append("Critical: session LLM cost cap reached.")
    elif cost_state == "warn":
        alerts.append("Warn: session approaching LLM cost cap.")
    if turns_used >= max_turns:
        alerts.append(f"Critical: max turns reached ({turns_used}/{max_turns}).")
    elif turns_used >= max(1, max_turns - 1):
        alerts.append(f"Warn: near max turns ({turns_used}/{max_turns}).")
    if last_score is not None and last_score < min_score:
        alerts.append(
            f"Warn: last rubric score {min_score_to_five_scale(last_score)} "
            f"below minimum {min_score_to_five_scale(min_score)}.",
        )

    if any("Critical:" in row for row in alerts) or cost_state == "halt":
        status: SloStatus = "halt"
        if turns_used >= max_turns:
            next_action = "Pause loop — approve partial output or start a smaller scoped session."
        elif cost_state == "halt":
            next_action = "Session halted on cost cap — reduce scope or raise cap in Settings → Harness loops."
        else:
            next_action = "Resolve critical guardrail alerts before continuing the loop."
    elif alerts or cost_state == "warn":
        status = "warn"
        next_action = "Monitor turns and spend — consider checkpoint approve before next hop."
    else:
        status = "healthy"
        next_action = "Loop within guardrails — continue or approve when critic passes."

    return status, alerts, next_action


def failure_signature(
    *,
    issues: list[str] | None = None,
    role: str = "",
    error_text: str = "",
) -> str:
    """Stable key for duplicate_failure detection (LN1)."""

    normalized = sorted({str(item).strip().lower() for item in (issues or []) if str(item).strip()})
    if normalized:
        return f"{role.strip().lower()}:{'|'.join(normalized)}"
    cleaned = error_text.strip().lower()[:160]
    return f"{role.strip().lower()}:{cleaned}" if cleaned else ""


def record_same_failure_signature(
    context_summary: dict[str, Any] | None,
    *,
    issues: list[str] | None = None,
    role: str = "",
    error_text: str = "",
) -> tuple[bool, dict[str, Any]]:
    """LN1 — same_failure_twice halts loop; returns (should_halt, updated_summary)."""

    summary = dict(context_summary or {})
    sig = failure_signature(issues=issues, role=role, error_text=error_text)
    if not sig or sig.endswith(":"):
        return False, summary

    previous = str(summary.get("loop_last_failure_signature") or "")
    count = int(summary.get("loop_same_failure_count") or 0)
    if sig == previous:
        count += 1
    else:
        count = 1

    summary["loop_last_failure_signature"] = sig
    summary["loop_same_failure_count"] = count
    if count >= 2:
        summary["same_failure_twice"] = True
        summary["discipline_halt_reason"] = f"same_failure_twice:{sig}"
        return True, summary
    return False, summary


async def compose_session_loop_guardrails_state(
    session: AsyncSession,
    *,
    supervisor_session: SupervisorSession,
) -> SessionLoopGuardrailsStateOut:
    """Build live LOOP2 state for session drawer / report."""

    summary = dict(supervisor_session.context_summary or {})
    if not is_loop_guardrails_active(summary):
        return SessionLoopGuardrailsStateOut(enabled=False)

    max_turns = loop_max_turns_from_summary(summary)
    min_score = loop_min_score_from_summary(summary)
    cap_usd = loop_cost_cap_from_summary(summary)
    warn_ratio = loop_cost_warn_ratio_from_summary(summary)
    turns_used = await count_session_loop_turns(session, session_id=supervisor_session.id)
    cost = await measure_session_cost(
        session,
        session_id=supervisor_session.id,
        cap_usd=cap_usd,
        warn_ratio=warn_ratio,
    )
    last_score = last_rubric_score_from_summary(summary)
    status, alerts, next_action = _resolve_loop_status(
        turns_used=turns_used,
        max_turns=max_turns,
        cost_state=cost.state,
        min_score=min_score,
        last_score=last_score,
    )

    return SessionLoopGuardrailsStateOut(
        enabled=True,
        status=status,
        max_turns=max_turns,
        turns_used=turns_used,
        min_score=min_score,
        min_score_label=min_score_to_five_scale(min_score),
        last_rubric_score=last_score,
        cost_cap_usd=cap_usd,
        spent_usd=cost.spent_usd,
        cost_utilization=cost.utilization,
        alerts=alerts,
        next_operator_action=next_action,
    )


__all__ = [
    "LoopGuardrailsPolicyOut",
    "LoopGuardrailsPolicyPatchIn",
    "SessionLoopGuardrailsStateOut",
    "apply_loop_guardrails_to_summary",
    "append_loop_guardrails_goal_footer",
    "build_loop_guardrails_context_seed",
    "compose_session_loop_guardrails_state",
    "count_session_loop_turns",
    "failure_signature",
    "get_loop_guardrails_policy",
    "is_loop_guardrails_active",
    "loop_cost_cap_from_summary",
    "loop_cost_warn_ratio_from_summary",
    "loop_max_turns_from_summary",
    "loop_min_score_from_summary",
    "min_score_to_five_scale",
    "record_same_failure_signature",
    "save_loop_guardrails_policy",
]
