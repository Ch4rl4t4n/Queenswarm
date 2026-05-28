"""Grok Control Plane orchestration (plan -> approve -> execute) for operator cockpit."""

from __future__ import annotations

import asyncio
import shlex
import shutil
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.execution_studio_notifications import notify_execution_studio_pending_approval
from app.application.services.operator_telegram_gateway import notify_zero_ui_ping
from app.core.config import settings
from app.core.database import async_session
from app.core.chroma_client import HIVE_MIND_COLLECTION, embed_and_store
from app.core.neo4j_client import create_knowledge_node
from app.infrastructure.persistence.models.grok_control_plane import (
    GrokRunApprovalORM,
    GrokRunArtifactORM,
    GrokRunEventORM,
    GrokRunORM,
    GrokRunStepORM,
    GrokRunTemplateORM,
)
from app.infrastructure.persistence.models.knowledge import KnowledgeItem
from app.infrastructure.persistence.models.recipe import Recipe
from app.infrastructure.persistence.models.swarm import SubSwarm
from app.infrastructure.persistence.models.task import Task
from app.infrastructure.persistence.models.tenant import DashboardUserTenantMembership, Tenant

RunStatus = Literal[
    "draft",
    "awaiting_approval",
    "approved",
    "running",
    "succeeded",
    "failed",
    "cancelled",
    "rejected",
]
RunMode = Literal["read_only", "code_edit", "code_edit_and_test", "deploy_candidate", "prod_deploy"]
RiskLevel = Literal["low", "medium", "high", "critical"]
ContextSource = Literal["tasks", "swarms", "recipes", "knowledge", "grok_history"]

_MAX_OUTPUT_CHARS = 100_000
_AVAILABLE_CONTEXT_SOURCES: tuple[ContextSource, ...] = (
    "tasks",
    "swarms",
    "recipes",
    "knowledge",
    "grok_history",
)


def _tokenize_text(value: str) -> set[str]:
    tokens = {
        token.strip().lower()
        for token in "".join(ch if ch.isalnum() else " " for ch in value).split()
        if len(token.strip()) > 2
    }
    return set(sorted(tokens))


def _jaccard_score(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    denom = len(a | b)
    if denom == 0:
        return 0.0
    return float(len(a & b) / denom)


def _artifact_confidence_and_priority(*, run_status: RunStatus, artifact_kind: str, text: str) -> tuple[float, Literal["high", "medium", "low"]]:
    """Estimate confidence + write-back priority for one Grok artifact."""

    base = 0.88 if run_status == "succeeded" else 0.7
    kind_bonus = {
        "summary": 0.07,
        "plan": 0.05,
        "context": 0.03,
        "command_log": -0.03,
    }.get(artifact_kind, 0.0)
    length_bonus = 0.03 if len(text.strip()) >= 900 else (0.015 if len(text.strip()) >= 300 else -0.02)
    confidence = max(0.05, min(0.99, base + kind_bonus + length_bonus))
    if confidence >= 0.86:
        priority: Literal["high", "medium", "low"] = "high"
    elif confidence >= 0.7:
        priority = "medium"
    else:
        priority = "low"
    return round(confidence, 3), priority


def _extract_priority_from_tags(tags: list[str]) -> Literal["high", "medium", "low"]:
    normalized = {str(tag).strip().lower() for tag in tags}
    if "priority-high" in normalized:
        return "high"
    if "priority-medium" in normalized:
        return "medium"
    return "low"


def _apply_hivemind_review_tags(
    tags: list[str],
    *,
    decision: Literal["approve", "reject"],
) -> list[str]:
    """Apply normalized queue-review tags to a HiveMind topic tag list."""

    tag_set = {str(tag).strip().lower() for tag in tags}
    tag_set.discard("hivemind-review-pending")
    tag_set.discard("hivemind-review-approved")
    tag_set.discard("hivemind-review-rejected")
    if decision == "approve":
        tag_set.add("hivemind-review-approved")
    else:
        tag_set.add("hivemind-review-rejected")
    return sorted(tag_set)


def _review_alert_timing_allowed(*, tenant: Tenant, now: datetime) -> bool:
    root = dict(tenant.operator_settings or {})
    studio = dict(root.get("execution_studio") or {}) if isinstance(root.get("execution_studio"), dict) else {}
    grok_bucket = (
        dict(studio.get("grok_hivemind_review") or {}) if isinstance(studio.get("grok_hivemind_review"), dict) else {}
    )
    last_raw = str(grok_bucket.get("last_alert_at") or "").strip()
    if not last_raw:
        return True
    try:
        last_at = datetime.fromisoformat(last_raw.replace("Z", "+00:00"))
    except ValueError:
        return True
    if last_at.tzinfo is None:
        last_at = last_at.replace(tzinfo=UTC)
    cooldown = max(60, int(settings.grok_cp_hivemind_review_alert_cooldown_sec))
    return (now - last_at).total_seconds() >= cooldown


def _stamp_review_alert_sent(*, tenant: Tenant, pending_count: int, now: datetime) -> None:
    root = dict(tenant.operator_settings or {})
    studio = dict(root.get("execution_studio") or {}) if isinstance(root.get("execution_studio"), dict) else {}
    grok_bucket = (
        dict(studio.get("grok_hivemind_review") or {}) if isinstance(studio.get("grok_hivemind_review"), dict) else {}
    )
    grok_bucket["last_alert_at"] = now.isoformat()
    grok_bucket["last_alert_pending_count"] = int(pending_count)
    studio["grok_hivemind_review"] = grok_bucket
    root["execution_studio"] = studio
    tenant.operator_settings = root


def _review_queue_escalation_reason(
    *,
    pending_count: int,
    threshold: int,
    oldest_age_hours: float | None,
    age_threshold_hours: int,
) -> str | None:
    """Return escalation reason summary when queue exceeds count/age SLA."""

    if pending_count <= 0:
        return None
    reasons: list[str] = []
    if pending_count >= threshold:
        reasons.append(f"count={pending_count}>=threshold={threshold}")
    if oldest_age_hours is not None and oldest_age_hours >= float(age_threshold_hours):
        reasons.append(f"oldest_age_hours={round(oldest_age_hours, 1)}>=sla={age_threshold_hours}")
    if not reasons:
        return None
    return ", ".join(reasons)


class GrokGuardrailsOut(BaseModel):
    """Resolved policy surface displayed in UI."""

    model_config = ConfigDict(extra="ignore")

    command_allow_profiles: list[str] = Field(default_factory=list)
    require_approval_for_risk: list[RiskLevel] = Field(default_factory=list)
    deny_patterns: list[str] = Field(default_factory=list)
    allow_prod_deploy: bool = False


class GrokLastResumedEscalationOut(BaseModel):
    """Persisted info about last escalation dedup resume action."""

    model_config = ConfigDict(extra="ignore")

    run_id: str
    escalation_kind: str
    resumed_at: datetime
    remaining_ttl_hours: float | None = None


class GrokControlPlaneSnapshotOut(BaseModel):
    """High-level Grok module snapshot for cockpit."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    cli_available: bool
    active_runs: int
    draft_runs: int
    failed_runs: int
    failed_alert_threshold: int = 3
    health_level: Literal["ok", "warn", "error"] = "ok"
    available_context_sources: list[ContextSource] = Field(default_factory=list)
    guardrails: GrokGuardrailsOut
    governance: "GrokGovernanceOut" = Field(default_factory=lambda: GrokGovernanceOut())
    last_resumed_escalation: GrokLastResumedEscalationOut | None = None


class GrokGovernanceOut(BaseModel):
    """Runtime governance envelope for the last 24h execution window."""

    model_config = ConfigDict(extra="ignore")

    window_hours: int = 24
    estimated_cost_usd: float = 0.0
    cost_cap_usd: float = 0.0
    cost_utilization: float = 0.0
    cost_cap_breached: bool = False
    timeout_breaches: int = 0
    timeout_threshold: int = 3
    timeout_escalated: bool = False
    high_risk_runs: int = 0
    risk_threshold: int = 6
    risk_escalated: bool = False
    escalation_resumes_24h: int = 0
    timeout_trend: Literal["up", "down", "flat"] = "flat"
    risk_trend: Literal["up", "down", "flat"] = "flat"
    resume_trend: Literal["up", "down", "flat"] = "flat"


class GrokRunCreateIn(BaseModel):
    """Operator intake for one Grok run."""

    model_config = ConfigDict(extra="forbid")

    objective: str = Field(min_length=8, max_length=4000)
    scope_paths: list[str] = Field(default_factory=list, max_length=40)
    run_mode: RunMode = "code_edit_and_test"
    risk_level: RiskLevel = "medium"
    command_profile: str = "ci_quick"
    context_sources: list[ContextSource] = Field(default_factory=list)
    template_id: str | None = None
    force_fresh_run: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class GrokTemplateCreateIn(BaseModel):
    """Create one reusable run template."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    objective: str = Field(min_length=8, max_length=4000)
    scope_paths: list[str] = Field(default_factory=list, max_length=40)
    run_mode: RunMode = "code_edit_and_test"
    risk_level: RiskLevel = "medium"
    command_profile: str = "ci_quick"
    context_sources: list[ContextSource] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list, max_length=24)


class GrokTemplateUpdateIn(BaseModel):
    """Patch existing template fields."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    objective: str | None = Field(default=None, min_length=8, max_length=4000)
    scope_paths: list[str] | None = Field(default=None, max_length=40)
    run_mode: RunMode | None = None
    risk_level: RiskLevel | None = None
    command_profile: str | None = None
    context_sources: list[ContextSource] | None = None
    tags: list[str] | None = Field(default=None, max_length=24)
    is_archived: bool | None = None


class GrokTemplateOut(BaseModel):
    """Template row serialized for UI."""

    model_config = ConfigDict(extra="ignore")

    id: str
    tenant_id: str
    name: str
    description: str | None = None
    objective: str
    scope_paths: list[str] = Field(default_factory=list)
    run_mode: RunMode
    risk_level: RiskLevel
    command_profile: str
    context_sources: list[ContextSource] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    usage_count: int = 0
    is_archived: bool = False
    last_used_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class GrokReuseCandidateOut(BaseModel):
    """One potentially reusable prior outcome similar to intake objective."""

    model_config = ConfigDict(extra="ignore")

    source_type: Literal["task", "recipe", "knowledge", "grok_run"]
    source_id: str
    title: str
    score: float
    status: str | None = None
    updated_at: datetime | None = None


class GrokIntakeAdviceIn(BaseModel):
    """Input for duplicate-awareness recommendation before run creation."""

    model_config = ConfigDict(extra="forbid")

    objective: str = Field(min_length=8, max_length=4000)
    scope_paths: list[str] = Field(default_factory=list, max_length=40)
    context_sources: list[ContextSource] = Field(default_factory=list)


class GrokIntakeAdviceOut(BaseModel):
    """Dedup score and recommendation for run intake."""

    model_config = ConfigDict(extra="ignore")

    dedup_score: float
    recommendation: Literal["reuse", "hybrid", "new"]
    rationale: str
    top_candidates: list[GrokReuseCandidateOut] = Field(default_factory=list)
    context_sources: list[ContextSource] = Field(default_factory=list)
    hard_gate_enabled: bool = False
    hard_gate_blocked: bool = False
    thresholds: dict[str, float] = Field(default_factory=dict)


class GrokPushArtifactToHiveMindIn(BaseModel):
    """Optional push settings when writing one artifact to HiveMind."""

    model_config = ConfigDict(extra="forbid")

    title_override: str | None = Field(default=None, max_length=240)
    tags: list[str] = Field(default_factory=list, max_length=24)
    auto_priority: bool = True
    priority_override: Literal["high", "medium", "low"] | None = None
    confidence_override: float | None = Field(default=None, ge=0.0, le=1.0)


class GrokPushArtifactToHiveMindOut(BaseModel):
    """Result of Grok artifact ingestion into HiveMind."""

    model_config = ConfigDict(extra="ignore")

    run_id: str
    artifact_id: str
    knowledge_item_id: str
    embedding_id: str | None = None
    neo4j_node_id: str | None = None
    source_type: str = "grok_control_plane"
    confidence_score: float = 0.0
    priority: Literal["high", "medium", "low"] = "medium"
    applied_tags: list[str] = Field(default_factory=list)


class GrokHiveMindReviewItemOut(BaseModel):
    """One low-confidence HiveMind item waiting for operator review."""

    model_config = ConfigDict(extra="ignore")

    knowledge_item_id: str
    source_url: str | None = None
    confidence_score: float
    priority: Literal["high", "medium", "low"] = "low"
    preview: str
    topic_tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class GrokHiveMindReviewQueueOut(BaseModel):
    """Review queue payload for low-confidence Grok HiveMind writes."""

    model_config = ConfigDict(extra="ignore")

    count: int
    oldest_pending_age_hours: float = 0.0
    sla_hours: int = 24
    sla_breached: bool = False
    items: list[GrokHiveMindReviewItemOut] = Field(default_factory=list)


class GrokHiveMindReviewDecisionIn(BaseModel):
    """Approve/reject review queue item."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    decision: Literal["approve", "reject"]
    note: str | None = Field(default=None, max_length=500)


class GrokHiveMindReviewDecisionOut(BaseModel):
    """Result of review decision over a queue item."""

    model_config = ConfigDict(extra="ignore")

    knowledge_item_id: str
    decision: Literal["approve", "reject"]
    reviewed_at: str
    topic_tags: list[str] = Field(default_factory=list)


class GrokRunDecisionIn(BaseModel):
    """Approve/reject/cancel payload."""

    model_config = ConfigDict(extra="forbid")

    note: str | None = Field(default=None, max_length=1000)


class GrokRunStartIn(BaseModel):
    """Start execution payload."""

    model_config = ConfigDict(extra="forbid")

    execute_commands: bool = False


class GrokRunStepOut(BaseModel):
    """One planned/executed run step."""

    model_config = ConfigDict(extra="ignore")

    id: str
    title: str
    kind: Literal["plan", "command", "verify", "deploy"]
    status: Literal["pending", "running", "done", "failed", "skipped"] = "pending"
    command: str | None = None
    output: str | None = None
    exit_code: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class GrokRunEventOut(BaseModel):
    """Timeline event row."""

    model_config = ConfigDict(extra="ignore")

    at: datetime
    level: Literal["info", "warning", "error", "success"]
    code: str
    message: str


class GrokRunArtifactOut(BaseModel):
    """Persisted run artifact (plan log, command output, summary bundle)."""

    model_config = ConfigDict(extra="ignore")

    id: str
    kind: str
    title: str
    mime_type: str
    content_text: str | None = None
    artifact_meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class GrokRunApprovalOut(BaseModel):
    """Approval/rejection history row for one run."""

    model_config = ConfigDict(extra="ignore")

    id: str
    decision: str
    decided_by: str
    note: str | None = None
    decided_at: datetime | None = None


class GrokRunOut(BaseModel):
    """Persisted run envelope."""

    model_config = ConfigDict(extra="ignore")

    id: str
    tenant_id: str
    dashboard_user_id: str
    objective: str
    scope_paths: list[str] = Field(default_factory=list)
    run_mode: RunMode
    risk_level: RiskLevel
    command_profile: str
    status: RunStatus
    requires_approval: bool
    created_at: datetime
    updated_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    approved_by: str | None = None
    approval_note: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    steps: list[GrokRunStepOut] = Field(default_factory=list)
    events: list[GrokRunEventOut] = Field(default_factory=list)
    artifacts: list[GrokRunArtifactOut] = Field(default_factory=list)


@dataclass(slots=True, frozen=True)
class _PolicyConfig:
    require_approval_for_risk: set[RiskLevel]
    deny_patterns: tuple[str, ...]
    allow_profiles: dict[str, list[str]]
    allow_prod_deploy: bool


@dataclass(slots=True, frozen=True)
class _DedupConfig:
    hard_gate_enabled: bool
    reuse_threshold: float
    hybrid_threshold: float
    source_min_score: dict[str, float]
    source_weight: dict[str, float]


def _utcnow() -> datetime:
    return datetime.now(tz=UTC)


def _split_csv(raw: str | None) -> list[str]:
    if raw is None:
        return []
    return [part.strip() for part in str(raw).split(",") if part.strip()]


def _parse_source_float_map(raw: str | None, *, default: dict[str, float], low: float, high: float) -> dict[str, float]:
    if raw is None or not str(raw).strip():
        return dict(default)
    out = dict(default)
    for part in _split_csv(raw):
        if ":" not in part:
            continue
        key_raw, value_raw = part.split(":", 1)
        key = key_raw.strip().lower()
        if key not in default:
            continue
        try:
            parsed = float(value_raw.strip())
        except ValueError:
            continue
        out[key] = max(low, min(high, parsed))
    return out


def _policy_config() -> _PolicyConfig:
    return _PolicyConfig(
        require_approval_for_risk={
            level
            for level in _split_csv(settings.grok_cp_require_approval_for_risk)
            if level in {"low", "medium", "high", "critical"}
        },
        deny_patterns=tuple(_split_csv(settings.grok_cp_deny_command_patterns)),
        allow_profiles={
            "read_only": _split_csv(settings.grok_cp_profile_read_only_commands),
            "ci_quick": _split_csv(settings.grok_cp_profile_ci_quick_commands),
            "deploy_candidate": _split_csv(settings.grok_cp_profile_deploy_candidate_commands),
            "prod_deploy": _split_csv(settings.grok_cp_profile_prod_deploy_commands),
        },
        allow_prod_deploy=bool(settings.grok_cp_allow_prod_deploy),
    )


def _dedup_config() -> _DedupConfig:
    default_min_score = {
        "task": 0.12,
        "recipe": 0.18,
        "knowledge": 0.16,
        "grok_run": 0.20,
    }
    default_weight = {
        "task": 1.0,
        "recipe": 1.1,
        "knowledge": 0.95,
        "grok_run": 1.15,
    }
    reuse_threshold = float(settings.grok_cp_dedup_reuse_threshold)
    hybrid_threshold = float(settings.grok_cp_dedup_hybrid_threshold)
    if hybrid_threshold >= reuse_threshold:
        hybrid_threshold = max(0.01, reuse_threshold - 0.05)
    return _DedupConfig(
        hard_gate_enabled=bool(settings.grok_cp_dedup_hard_gate_enabled),
        reuse_threshold=max(0.05, min(0.98, reuse_threshold)),
        hybrid_threshold=max(0.01, min(0.95, hybrid_threshold)),
        source_min_score=_parse_source_float_map(
            settings.grok_cp_dedup_min_score_by_source,
            default=default_min_score,
            low=0.0,
            high=0.95,
        ),
        source_weight=_parse_source_float_map(
            settings.grok_cp_dedup_weight_by_source,
            default=default_weight,
            low=0.2,
            high=2.5,
        ),
    )


def _escalation_dedup_window_sec() -> int:
    """Return enabled escalation dedup cooldown window."""

    if not bool(settings.grok_cp_escalation_dedup_enabled):
        return 0
    return max(0, int(settings.grok_cp_escalation_cooldown_sec))


def _escalation_kind_from_metadata(metadata: dict[str, Any] | None) -> str | None:
    """Extract normalized escalation kind from run metadata."""

    if not isinstance(metadata, dict):
        return None
    raw = str(metadata.get("escalation_kind") or "").strip().lower()
    if not raw:
        return None
    cleaned = "".join(ch for ch in raw if ch.isalnum() or ch in {"_", "-"})
    if not cleaned:
        return None
    return cleaned[:64]


def _stamp_last_resumed_escalation(
    tenant: Tenant | None,
    *,
    run_id: uuid.UUID,
    escalation_kind: str,
    resumed_at: datetime,
) -> None:
    """Persist last resumed escalation marker into tenant operator settings."""

    if tenant is None:
        return
    root = dict(tenant.operator_settings or {})
    bucket = (
        dict(root.get("grok_control_plane") or {})
        if isinstance(root.get("grok_control_plane"), dict)
        else {}
    )
    bucket["last_resumed_escalation"] = {
        "run_id": str(run_id),
        "escalation_kind": escalation_kind,
        "resumed_at": resumed_at.isoformat(),
    }
    root["grok_control_plane"] = bucket
    tenant.operator_settings = root


def _record_escalation_resume_event(
    tenant: Tenant | None,
    *,
    run_id: uuid.UUID,
    escalation_kind: str,
    resumed_at: datetime,
) -> None:
    """Append one escalation resume telemetry event to tenant settings."""

    if tenant is None:
        return
    root = dict(tenant.operator_settings or {})
    bucket = (
        dict(root.get("grok_control_plane") or {})
        if isinstance(root.get("grok_control_plane"), dict)
        else {}
    )
    events = list(bucket.get("resume_events") or []) if isinstance(bucket.get("resume_events"), list) else []
    events.append(
        {
            "run_id": str(run_id),
            "escalation_kind": escalation_kind,
            "at": resumed_at.isoformat(),
        }
    )
    bucket["resume_events"] = events[-160:]
    root["grok_control_plane"] = bucket
    tenant.operator_settings = root


def _count_recent_escalation_resumes(tenant: Tenant | None, *, window_hours: int = 24) -> int:
    """Return count of escalation resume events inside rolling window."""

    if tenant is None:
        return 0
    root = dict(tenant.operator_settings or {})
    bucket = (
        dict(root.get("grok_control_plane") or {})
        if isinstance(root.get("grok_control_plane"), dict)
        else {}
    )
    events = list(bucket.get("resume_events") or []) if isinstance(bucket.get("resume_events"), list) else []
    if not events:
        return 0
    now = _utcnow()
    since = now - timedelta(hours=max(1, int(window_hours)))
    count = 0
    for raw in events:
        if not isinstance(raw, dict):
            continue
        at_raw = str(raw.get("at") or "").strip()
        if not at_raw:
            continue
        try:
            at = datetime.fromisoformat(at_raw)
        except ValueError:
            continue
        if at.tzinfo is None:
            at = at.replace(tzinfo=UTC)
        if at >= since:
            count += 1
    return count


def _count_escalation_resumes_between(
    tenant: Tenant | None,
    *,
    since: datetime,
    until: datetime | None = None,
) -> int:
    """Return count of escalation resume events between two timestamps."""

    if tenant is None:
        return 0
    root = dict(tenant.operator_settings or {})
    bucket = (
        dict(root.get("grok_control_plane") or {})
        if isinstance(root.get("grok_control_plane"), dict)
        else {}
    )
    events = list(bucket.get("resume_events") or []) if isinstance(bucket.get("resume_events"), list) else []
    if not events:
        return 0
    upper = until or _utcnow()
    count = 0
    for raw in events:
        if not isinstance(raw, dict):
            continue
        at_raw = str(raw.get("at") or "").strip()
        if not at_raw:
            continue
        try:
            at = datetime.fromisoformat(at_raw)
        except ValueError:
            continue
        if at.tzinfo is None:
            at = at.replace(tzinfo=UTC)
        if since <= at < upper:
            count += 1
    return count


def _read_last_resumed_escalation(tenant: Tenant | None) -> GrokLastResumedEscalationOut | None:
    """Read persisted last resumed escalation marker from tenant settings."""

    if tenant is None:
        return None
    root = dict(tenant.operator_settings or {})
    bucket = (
        dict(root.get("grok_control_plane") or {})
        if isinstance(root.get("grok_control_plane"), dict)
        else {}
    )
    raw = bucket.get("last_resumed_escalation")
    if not isinstance(raw, dict):
        return None
    run_id = str(raw.get("run_id") or "").strip()
    kind = str(raw.get("escalation_kind") or "").strip()
    raw_at = str(raw.get("resumed_at") or "").strip()
    if not run_id or not kind or not raw_at:
        return None
    try:
        resumed_at = datetime.fromisoformat(raw_at)
    except ValueError:
        return None
    if resumed_at.tzinfo is None:
        resumed_at = resumed_at.replace(tzinfo=UTC)
    ttl_hours = max(1, int(settings.grok_cp_last_resumed_marker_ttl_hours))
    now = _utcnow()
    ttl_delta = timedelta(hours=ttl_hours)
    age = now - resumed_at
    if age > ttl_delta:
        return None
    remaining_hours = max(0.0, round((ttl_delta - age).total_seconds() / 3600.0, 2))
    return GrokLastResumedEscalationOut(
        run_id=run_id,
        escalation_kind=kind,
        resumed_at=resumed_at,
        remaining_ttl_hours=remaining_hours,
    )


async def _existing_escalation_run_in_cooldown(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    escalation_kind: str,
) -> GrokRunORM | None:
    """Return recent escalation run row when cooldown gate is active."""

    cooldown_sec = _escalation_dedup_window_sec()
    if cooldown_sec <= 0:
        return None
    since = _utcnow() - timedelta(seconds=cooldown_sec)
    rows = list(
        (
            await session.scalars(
                select(GrokRunORM)
                .where(
                    GrokRunORM.tenant_id == tenant_id,
                    GrokRunORM.created_at >= since,
                )
                .order_by(GrokRunORM.created_at.desc())
                .limit(60),
            )
        ).all(),
    )
    for row in rows:
        if row.status in {"cancelled", "rejected"}:
            continue
        meta = dict(row.metadata_json or {})
        if _escalation_kind_from_metadata(meta) == escalation_kind:
            return row
    return None


def _run_mode_cost_map() -> dict[str, float]:
    default = {
        "read_only": 0.03,
        "code_edit": 0.12,
        "code_edit_and_test": 0.30,
        "deploy_candidate": 0.55,
        "prod_deploy": 0.80,
    }
    return _parse_source_float_map(
        settings.grok_cp_estimated_cost_per_run,
        default=default,
        low=0.0,
        high=100.0,
    )


def _build_governance_snapshot(
    *,
    mode_counts: dict[str, int],
    timeout_breaches: int,
    timeout_breaches_prev: int,
    high_risk_runs: int,
    high_risk_runs_prev: int,
    escalation_resumes_24h: int,
    escalation_resumes_prev_24h: int,
) -> GrokGovernanceOut:
    """Build cost/timeout/risk governance metrics for cockpit visibility."""

    cost_map = _run_mode_cost_map()
    estimated_cost = sum(float(cost_map.get(mode, 0.0)) * int(count) for mode, count in mode_counts.items())
    cap = max(0.0, float(settings.grok_cp_cost_cap_usd_24h))
    utilization = 0.0
    if cap > 0.0:
        utilization = max(0.0, min(3.0, estimated_cost / cap))
    timeout_threshold = max(1, int(settings.grok_cp_timeout_alert_threshold_24h))
    risk_threshold = max(1, int(settings.grok_cp_risk_escalation_threshold_24h))
    timeout_trend: Literal["up", "down", "flat"] = "flat"
    if timeout_breaches > timeout_breaches_prev:
        timeout_trend = "up"
    elif timeout_breaches < timeout_breaches_prev:
        timeout_trend = "down"
    risk_trend: Literal["up", "down", "flat"] = "flat"
    if high_risk_runs > high_risk_runs_prev:
        risk_trend = "up"
    elif high_risk_runs < high_risk_runs_prev:
        risk_trend = "down"
    resume_trend: Literal["up", "down", "flat"] = "flat"
    if escalation_resumes_24h > escalation_resumes_prev_24h:
        resume_trend = "up"
    elif escalation_resumes_24h < escalation_resumes_prev_24h:
        resume_trend = "down"
    return GrokGovernanceOut(
        window_hours=24,
        estimated_cost_usd=round(estimated_cost, 2),
        cost_cap_usd=round(cap, 2),
        cost_utilization=round(utilization, 4),
        cost_cap_breached=bool(cap > 0.0 and estimated_cost >= cap),
        timeout_breaches=int(timeout_breaches),
        timeout_threshold=timeout_threshold,
        timeout_escalated=bool(timeout_breaches >= timeout_threshold),
        high_risk_runs=int(high_risk_runs),
        risk_threshold=risk_threshold,
        risk_escalated=bool(high_risk_runs >= risk_threshold),
        escalation_resumes_24h=max(0, int(escalation_resumes_24h)),
        timeout_trend=timeout_trend,
        risk_trend=risk_trend,
        resume_trend=resume_trend,
    )


def _render_guardrails(cfg: _PolicyConfig) -> GrokGuardrailsOut:
    return GrokGuardrailsOut(
        command_allow_profiles=sorted(list(cfg.allow_profiles.keys())),
        require_approval_for_risk=sorted(cfg.require_approval_for_risk),  # type: ignore[arg-type]
        deny_patterns=list(cfg.deny_patterns),
        allow_prod_deploy=cfg.allow_prod_deploy,
    )


def _grok_cli_available() -> bool:
    return shutil.which(settings.grok_cp_cli_binary) is not None


def _repo_root() -> Path:
    root = Path(settings.grok_cp_repo_root).resolve()
    return root if root.exists() else Path.cwd()


def _safe_scope_paths(scope_paths: list[str]) -> list[str]:
    out: list[str] = []
    for raw in scope_paths:
        cleaned = raw.strip().replace("\\", "/")
        if not cleaned or ".." in cleaned:
            continue
        out.append(cleaned[:240])
    return out[:40]


def _safe_context_sources(sources: list[str] | list[ContextSource] | None) -> list[ContextSource]:
    if not sources:
        return list(_AVAILABLE_CONTEXT_SOURCES)
    normalized: list[ContextSource] = []
    for raw in sources:
        value = str(raw).strip().lower()
        if value in _AVAILABLE_CONTEXT_SOURCES and value not in normalized:
            normalized.append(value)  # type: ignore[arg-type]
    return normalized if normalized else list(_AVAILABLE_CONTEXT_SOURCES)


def _safe_tags(tags: list[str] | None) -> list[str]:
    if not tags:
        return []
    out: list[str] = []
    for raw in tags:
        tag = str(raw).strip().lower()
        if not tag:
            continue
        cleaned = "".join(ch for ch in tag if ch.isalnum() or ch in {"-", "_"})
        if cleaned and cleaned not in out:
            out.append(cleaned[:48])
    return out[:24]


def _parse_run_uuid(run_id: str) -> uuid.UUID:
    """Return validated run UUID or raise LookupError for API-friendly handling."""

    try:
        return uuid.UUID(run_id)
    except (ValueError, TypeError) as exc:
        raise LookupError("Run not found.") from exc


def _parse_template_uuid(template_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(template_id)
    except (ValueError, TypeError) as exc:
        raise LookupError("Template not found.") from exc


def _default_plan(body: GrokRunCreateIn) -> list[GrokRunStepOut]:
    verify_step_kind: Literal["verify", "deploy"] = "deploy" if body.run_mode in {"deploy_candidate", "prod_deploy"} else "verify"
    return [
        GrokRunStepOut(id="plan", title="Generate structured implementation plan", kind="plan"),
        GrokRunStepOut(id="lint", title="Run lint/profile checks", kind="command"),
        GrokRunStepOut(id="tests", title="Run selected test profile", kind="verify"),
        GrokRunStepOut(id="finalize", title="Create run artifacts and summary", kind=verify_step_kind),
    ]


def _event(code: str, message: str, *, level: Literal["info", "warning", "error", "success"] = "info") -> GrokRunEventOut:
    return GrokRunEventOut(at=_utcnow(), level=level, code=code, message=message)


def _step_to_out(step: GrokRunStepORM) -> GrokRunStepOut:
    return GrokRunStepOut(
        id=step.step_id,
        title=step.title,
        kind=step.kind,  # type: ignore[arg-type]
        status=step.status,  # type: ignore[arg-type]
        command=step.command,
        output=step.output,
        exit_code=step.exit_code,
        started_at=step.started_at,
        finished_at=step.finished_at,
    )


def _event_to_out(event: GrokRunEventORM) -> GrokRunEventOut:
    return GrokRunEventOut(
        at=event.occurred_at,
        level=event.level,  # type: ignore[arg-type]
        code=event.code,
        message=event.message,
    )


def _template_to_out(template: GrokRunTemplateORM) -> GrokTemplateOut:
    return GrokTemplateOut(
        id=str(template.id),
        tenant_id=str(template.tenant_id),
        name=template.name,
        description=template.description,
        objective=template.objective,
        scope_paths=[str(item) for item in list(template.scope_paths or [])],
        run_mode=template.run_mode,  # type: ignore[arg-type]
        risk_level=template.risk_level,  # type: ignore[arg-type]
        command_profile=template.command_profile,
        context_sources=_safe_context_sources(list(template.context_sources or [])),
        tags=[str(tag) for tag in list(template.tags or [])],
        usage_count=int(template.usage_count or 0),
        is_archived=bool(template.is_archived),
        last_used_at=template.last_used_at,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def _truncate_text(value: str, *, limit: int = 220) -> str:
    compact = " ".join(value.strip().split())
    if len(compact) <= limit:
        return compact
    return f"{compact[: limit - 1]}…"


async def _build_context_pack(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    objective: str,
    scope_paths: list[str],
    sources: list[ContextSource],
) -> dict[str, Any]:
    pack: dict[str, Any] = {
        "objective": objective,
        "scope_paths": scope_paths,
        "sources": sources,
        "generated_at": _utcnow().isoformat(),
    }

    if "tasks" in sources:
        task_rows = list(
            (
                await session.scalars(
                    select(Task)
                    .where(Task.tenant_id == tenant_id, Task.completed_at.is_not(None))
                    .order_by(Task.completed_at.desc())
                    .limit(6),
                )
            ).all(),
        )
        pack["tasks"] = [
            {
                "id": str(task.id),
                "title": _truncate_text(task.title, limit=160),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "swarm_id": str(task.swarm_id) if task.swarm_id else None,
                "recipe_used_id": str(task.recipe_used_id) if task.recipe_used_id else None,
            }
            for task in task_rows
        ]
    if "swarms" in sources:
        swarm_rows = list(
            (
                await session.scalars(
                    select(SubSwarm)
                    .where(SubSwarm.is_active.is_(True))
                    .order_by(SubSwarm.updated_at.desc())
                    .limit(5),
                )
            ).all(),
        )
        pack["swarms"] = [
            {
                "id": str(swarm.id),
                "name": swarm.name,
                "purpose": swarm.purpose.value,
                "member_count": int(swarm.member_count),
                "total_pollen": float(swarm.total_pollen),
            }
            for swarm in swarm_rows
        ]
    if "recipes" in sources:
        recipe_rows = list(
            (
                await session.scalars(
                    select(Recipe)
                    .where(Recipe.is_deprecated.is_(False))
                    .order_by(Recipe.updated_at.desc())
                    .limit(6),
                )
            ).all(),
        )
        pack["recipes"] = [
            {
                "id": str(recipe.id),
                "name": recipe.name,
                "description": _truncate_text(recipe.description or "", limit=160),
                "success_count": int(recipe.success_count),
                "success_rate": round(float(recipe.success_rate), 3),
            }
            for recipe in recipe_rows
        ]
    if "knowledge" in sources:
        knowledge_rows = list(
            (
                await session.scalars(
                    select(KnowledgeItem)
                    .where(KnowledgeItem.tenant_id == tenant_id)
                    .order_by(KnowledgeItem.updated_at.desc())
                    .limit(6),
                )
            ).all(),
        )
        pack["knowledge"] = [
            {
                "id": str(item.id),
                "source_type": item.source_type,
                "topic_tags": list(item.topic_tags or []),
                "summary": _truncate_text(item.content_text, limit=180),
            }
            for item in knowledge_rows
        ]
    if "grok_history" in sources:
        history_rows = list(
            (
                await session.scalars(
                    select(GrokRunORM)
                    .where(
                        GrokRunORM.tenant_id == tenant_id,
                        GrokRunORM.status.in_(("succeeded", "failed", "cancelled")),
                    )
                    .order_by(GrokRunORM.updated_at.desc())
                    .limit(5),
                )
            ).all(),
        )
        pack["grok_history"] = [
            {
                "id": str(row.id),
                "objective": _truncate_text(row.objective, limit=160),
                "status": row.status,
                "updated_at": row.updated_at.isoformat(),
            }
            for row in history_rows
        ]
    return pack


def _render_context_pack(pack: dict[str, Any]) -> str:
    lines = [
        f"Objective: {pack.get('objective', '')}",
        f"Scope: {', '.join(pack.get('scope_paths', [])) or 'entire repository'}",
        f"Sources: {', '.join(pack.get('sources', []))}",
        "",
    ]

    def append_section(title: str, items: list[dict[str, Any]], fields: tuple[str, ...]) -> None:
        lines.append(f"{title}:")
        if not items:
            lines.append("- none")
            lines.append("")
            return
        for item in items[:6]:
            parts: list[str] = []
            for field in fields:
                value = item.get(field)
                if value in (None, "", [], {}):
                    continue
                parts.append(f"{field}={value}")
            lines.append(f"- {'; '.join(parts)}")
        lines.append("")

    append_section("Recent tasks", list(pack.get("tasks", [])), ("title", "completed_at", "recipe_used_id"))
    append_section("Active swarms", list(pack.get("swarms", [])), ("name", "purpose", "member_count", "total_pollen"))
    append_section("Top recipes", list(pack.get("recipes", [])), ("name", "success_rate", "description"))
    append_section("Knowledge clues", list(pack.get("knowledge", [])), ("source_type", "summary", "topic_tags"))
    append_section("Grok history", list(pack.get("grok_history", [])), ("objective", "status", "updated_at"))
    return "\n".join(lines).strip()


async def _hydrate_run(session: AsyncSession, row: GrokRunORM) -> GrokRunOut:
    steps = list(
        (
            await session.scalars(
                select(GrokRunStepORM)
                .where(GrokRunStepORM.run_id == row.id)
                .order_by(GrokRunStepORM.step_order.asc()),
            )
        ).all(),
    )
    events = list(
        (
            await session.scalars(
                select(GrokRunEventORM)
                .where(GrokRunEventORM.run_id == row.id)
                .order_by(GrokRunEventORM.occurred_at.asc()),
            )
        ).all(),
    )
    artifacts = list(
        (
            await session.scalars(
                select(GrokRunArtifactORM)
                .where(GrokRunArtifactORM.run_id == row.id)
                .order_by(GrokRunArtifactORM.created_at.asc()),
            )
        ).all(),
    )
    return GrokRunOut(
        id=str(row.id),
        tenant_id=str(row.tenant_id),
        dashboard_user_id=str(row.dashboard_user_id),
        objective=row.objective,
        scope_paths=[str(item) for item in list(row.scope_paths or [])],
        run_mode=row.run_mode,  # type: ignore[arg-type]
        risk_level=row.risk_level,  # type: ignore[arg-type]
        command_profile=row.command_profile,
        status=row.status,  # type: ignore[arg-type]
        requires_approval=row.requires_approval,
        created_at=row.created_at,
        updated_at=row.updated_at,
        started_at=row.started_at,
        finished_at=row.finished_at,
        approved_by=row.approved_by,
        approval_note=row.approval_note,
        metadata=dict(row.metadata_json or {}),
        steps=[_step_to_out(step) for step in steps],
        events=[_event_to_out(event) for event in events],
        artifacts=[
            GrokRunArtifactOut(
                id=str(artifact.id),
                kind=artifact.artifact_kind,
                title=artifact.title,
                mime_type=artifact.mime_type,
                content_text=artifact.content_text,
                artifact_meta=dict(artifact.artifact_meta or {}),
                created_at=artifact.created_at,
            )
            for artifact in artifacts
        ],
    )


async def _append_event(
    session: AsyncSession,
    *,
    run_row: GrokRunORM,
    level: Literal["info", "warning", "error", "success"],
    code: str,
    message: str,
) -> None:
    session.add(
        GrokRunEventORM(
            tenant_id=run_row.tenant_id,
            run_id=run_row.id,
            level=level,
            code=code,
            message=message,
            occurred_at=_utcnow(),
        ),
    )


async def list_grok_run_approvals(tenant_id: uuid.UUID, run_id: str, *, limit: int = 50) -> list[GrokRunApprovalOut]:
    """Return approval/rejection history for one run."""

    async with async_session() as session:
        run_row = await session.get(GrokRunORM, _parse_run_uuid(run_id))
        if run_row is None or run_row.tenant_id != tenant_id:
            raise LookupError("Run not found.")
        rows = list(
            (
                await session.scalars(
                    select(GrokRunApprovalORM)
                    .where(GrokRunApprovalORM.run_id == run_row.id)
                    .order_by(GrokRunApprovalORM.decided_at.desc())
                    .limit(max(1, min(limit, 200))),
                )
            ).all(),
        )
        return [
            GrokRunApprovalOut(
                id=str(row.id),
                decision=row.decision,
                decided_by=row.decided_by,
                note=row.note,
                decided_at=row.decided_at,
            )
            for row in rows
        ]


async def list_grok_run_artifacts(
    tenant_id: uuid.UUID,
    run_id: str,
    *,
    kind: str | None = None,
    limit: int = 100,
) -> list[GrokRunArtifactOut]:
    """Return artifacts for one run with optional kind filter."""

    async with async_session() as session:
        run_row = await session.get(GrokRunORM, _parse_run_uuid(run_id))
        if run_row is None or run_row.tenant_id != tenant_id:
            raise LookupError("Run not found.")
        stmt = (
            select(GrokRunArtifactORM)
            .where(GrokRunArtifactORM.run_id == run_row.id)
            .order_by(GrokRunArtifactORM.created_at.desc())
            .limit(max(1, min(limit, 300)))
        )
        if kind and kind.strip():
            stmt = stmt.where(GrokRunArtifactORM.artifact_kind == kind.strip())
        rows = list((await session.scalars(stmt)).all())
        return [
            GrokRunArtifactOut(
                id=str(row.id),
                kind=row.artifact_kind,
                title=row.title,
                mime_type=row.mime_type,
                content_text=row.content_text,
                artifact_meta=dict(row.artifact_meta or {}),
                created_at=row.created_at,
            )
            for row in rows
        ]


async def rerun_grok_run(
    tenant_id: uuid.UUID,
    run_id: str,
    *,
    dashboard_user_id: uuid.UUID,
    objective_override: str | None = None,
) -> GrokRunOut:
    """Clone an existing run into a new draft/approval run."""

    original = await get_grok_run(tenant_id=tenant_id, run_id=run_id)
    objective = (objective_override or original.objective).strip()
    if not objective:
        raise ValueError("Objective must not be empty.")
    body = GrokRunCreateIn(
        objective=objective,
        scope_paths=original.scope_paths,
        run_mode=original.run_mode,
        risk_level=original.risk_level,
        command_profile=original.command_profile,
        metadata={**original.metadata, "rerun_of": original.id},
    )
    cloned = await create_grok_run(tenant_id=tenant_id, dashboard_user_id=dashboard_user_id, body=body)
    return cloned


def _requires_approval(*, risk_level: RiskLevel, run_mode: RunMode, cfg: _PolicyConfig) -> bool:
    if risk_level in cfg.require_approval_for_risk:
        return True
    if run_mode in {"deploy_candidate", "prod_deploy"}:
        return True
    return False


def _validate_mode_policy(*, body: GrokRunCreateIn, cfg: _PolicyConfig) -> None:
    if body.run_mode == "prod_deploy" and not cfg.allow_prod_deploy:
        raise ValueError("Policy denies prod_deploy mode.")
    if body.command_profile not in cfg.allow_profiles:
        raise ValueError(f"Unknown command profile: {body.command_profile}")


def _apply_command_policy(command: str, cfg: _PolicyConfig) -> bool:
    command_lower = command.lower()
    for pattern in cfg.deny_patterns:
        if pattern.lower() in command_lower:
            return False
    return True


async def compose_grok_control_plane_snapshot(tenant_id: uuid.UUID) -> GrokControlPlaneSnapshotOut:
    """Return Grok module snapshot for cockpit."""

    if not settings.grok_control_plane_enabled:
        return GrokControlPlaneSnapshotOut(
            enabled=False,
            generated_at=_utcnow(),
            cli_available=False,
            active_runs=0,
            draft_runs=0,
            failed_runs=0,
            guardrails=GrokGuardrailsOut(),
        )

    cfg = _policy_config()
    async with async_session() as session:
        now = _utcnow()
        since = now - timedelta(hours=24)
        prev_since = now - timedelta(hours=48)
        prev_until = since
        tenant = await session.get(Tenant, tenant_id)
        active_count = await session.scalar(
            select(func.count())
            .select_from(GrokRunORM)
            .where(
                GrokRunORM.tenant_id == tenant_id,
                GrokRunORM.status.in_(("running", "approved", "awaiting_approval")),
            ),
        )
        draft_count = await session.scalar(
            select(func.count())
            .select_from(GrokRunORM)
            .where(
                GrokRunORM.tenant_id == tenant_id,
                GrokRunORM.status.in_(("draft", "awaiting_approval")),
            ),
        )
        failed_count = await session.scalar(
            select(func.count())
            .select_from(GrokRunORM)
            .where(
                GrokRunORM.tenant_id == tenant_id,
                GrokRunORM.status == "failed",
            ),
        )
        mode_rows = list(
            (
                await session.execute(
                    select(GrokRunORM.run_mode, func.count())
                    .where(
                        GrokRunORM.tenant_id == tenant_id,
                        GrokRunORM.created_at >= since,
                    )
                    .group_by(GrokRunORM.run_mode),
                )
            ).all(),
        )
        mode_counts = {str(mode): int(count or 0) for mode, count in mode_rows}
        timeout_breaches = int(
            await session.scalar(
                select(func.count())
                .select_from(GrokRunStepORM)
                .join(GrokRunORM, GrokRunORM.id == GrokRunStepORM.run_id)
                .where(
                    GrokRunStepORM.tenant_id == tenant_id,
                    GrokRunORM.tenant_id == tenant_id,
                    GrokRunStepORM.exit_code == 124,
                    GrokRunStepORM.created_at >= since,
                ),
            )
            or 0
        )
        timeout_breaches_prev = int(
            await session.scalar(
                select(func.count())
                .select_from(GrokRunStepORM)
                .join(GrokRunORM, GrokRunORM.id == GrokRunStepORM.run_id)
                .where(
                    GrokRunStepORM.tenant_id == tenant_id,
                    GrokRunORM.tenant_id == tenant_id,
                    GrokRunStepORM.exit_code == 124,
                    GrokRunStepORM.created_at >= prev_since,
                    GrokRunStepORM.created_at < prev_until,
                ),
            )
            or 0
        )
        high_risk_runs = int(
            await session.scalar(
                select(func.count())
                .select_from(GrokRunORM)
                .where(
                    GrokRunORM.tenant_id == tenant_id,
                    GrokRunORM.created_at >= since,
                    GrokRunORM.risk_level.in_(("high", "critical")),
                ),
            )
            or 0
        )
        high_risk_runs_prev = int(
            await session.scalar(
                select(func.count())
                .select_from(GrokRunORM)
                .where(
                    GrokRunORM.tenant_id == tenant_id,
                    GrokRunORM.created_at >= prev_since,
                    GrokRunORM.created_at < prev_until,
                    GrokRunORM.risk_level.in_(("high", "critical")),
                ),
            )
            or 0
        )
        resumes_current = _count_escalation_resumes_between(tenant, since=since, until=now)
        resumes_prev = _count_escalation_resumes_between(tenant, since=prev_since, until=prev_until)
        governance = _build_governance_snapshot(
            mode_counts=mode_counts,
            timeout_breaches=timeout_breaches,
            timeout_breaches_prev=timeout_breaches_prev,
            high_risk_runs=high_risk_runs,
            high_risk_runs_prev=high_risk_runs_prev,
            escalation_resumes_24h=resumes_current,
            escalation_resumes_prev_24h=resumes_prev,
        )
    return GrokControlPlaneSnapshotOut(
        enabled=True,
        generated_at=now,
        cli_available=_grok_cli_available(),
        active_runs=int(active_count or 0),
        draft_runs=int(draft_count or 0),
        failed_runs=int(failed_count or 0),
        failed_alert_threshold=max(1, int(settings.grok_cp_failed_alert_threshold)),
        health_level=(
            "error"
            if int(failed_count or 0) >= max(1, int(settings.grok_cp_failed_alert_threshold))
            else "warn"
            if int(active_count or 0) > 0 or int(draft_count or 0) > 0
            else "ok"
        ),
        available_context_sources=list(_AVAILABLE_CONTEXT_SOURCES),
        guardrails=_render_guardrails(cfg),
        governance=governance,
        last_resumed_escalation=_read_last_resumed_escalation(tenant),
    )


async def list_grok_templates(
    tenant_id: uuid.UUID,
    *,
    limit: int = 24,
    offset: int = 0,
    include_archived: bool = False,
    archived_only: bool = False,
    query: str | None = None,
) -> list[GrokTemplateOut]:
    """List tenant template library rows."""

    async with async_session() as session:
        stmt = (
            select(GrokRunTemplateORM)
            .where(GrokRunTemplateORM.tenant_id == tenant_id)
            .order_by(GrokRunTemplateORM.updated_at.desc())
            .limit(max(1, min(limit, 80)))
            .offset(max(0, offset))
        )
        if archived_only:
            stmt = stmt.where(GrokRunTemplateORM.is_archived.is_(True))
        elif not include_archived:
            stmt = stmt.where(GrokRunTemplateORM.is_archived.is_(False))
        if query and query.strip():
            needle = f"%{query.strip().lower()}%"
            stmt = stmt.where(
                func.lower(GrokRunTemplateORM.name).like(needle)
                | func.lower(func.coalesce(GrokRunTemplateORM.description, "")).like(needle)
                | func.lower(GrokRunTemplateORM.objective).like(needle)
            )
        rows = list((await session.scalars(stmt)).all())
        return [_template_to_out(row) for row in rows]


async def build_grok_intake_advice(tenant_id: uuid.UUID, body: GrokIntakeAdviceIn) -> GrokIntakeAdviceOut:
    """Compute duplicate-awareness recommendation from Hive artifacts."""

    objective = body.objective.strip()
    scope_paths = _safe_scope_paths(body.scope_paths)
    sources = _safe_context_sources(body.context_sources)
    dedup_cfg = _dedup_config()
    objective_tokens = _tokenize_text(f"{objective} {' '.join(scope_paths)}")
    candidates: list[GrokReuseCandidateOut] = []

    def _score_for_source(*, source: Literal["task", "recipe", "knowledge", "grok_run"], raw_score: float) -> float:
        weighted = raw_score * float(dedup_cfg.source_weight.get(source, 1.0))
        return max(0.0, min(1.0, weighted))

    async with async_session() as session:
        if "tasks" in sources:
            task_rows = list(
                (
                    await session.scalars(
                        select(Task)
                        .where(Task.tenant_id == tenant_id, Task.completed_at.is_not(None))
                        .order_by(Task.completed_at.desc())
                        .limit(12),
                    )
                ).all(),
            )
            for task in task_rows:
                raw_score = _jaccard_score(objective_tokens, _tokenize_text(task.title))
                score = _score_for_source(source="task", raw_score=raw_score)
                if score < float(dedup_cfg.source_min_score.get("task", 0.0)):
                    continue
                candidates.append(
                    GrokReuseCandidateOut(
                        source_type="task",
                        source_id=str(task.id),
                        title=_truncate_text(task.title, limit=180),
                        score=round(score, 3),
                        status=task.status.value if hasattr(task.status, "value") else str(task.status),
                        updated_at=task.updated_at,
                    )
                )
        if "recipes" in sources:
            recipe_rows = list(
                (
                    await session.scalars(
                        select(Recipe)
                        .where(Recipe.is_deprecated.is_(False))
                        .order_by(Recipe.updated_at.desc())
                        .limit(10),
                    )
                ).all(),
            )
            for recipe in recipe_rows:
                blob = f"{recipe.name} {recipe.description or ''}"
                raw_score = _jaccard_score(objective_tokens, _tokenize_text(blob))
                score = _score_for_source(source="recipe", raw_score=raw_score)
                if score < float(dedup_cfg.source_min_score.get("recipe", 0.0)):
                    continue
                candidates.append(
                    GrokReuseCandidateOut(
                        source_type="recipe",
                        source_id=str(recipe.id),
                        title=_truncate_text(recipe.name, limit=180),
                        score=round(score, 3),
                        status="verified" if recipe.verified_at else "unverified",
                        updated_at=recipe.updated_at,
                    )
                )
        if "knowledge" in sources:
            knowledge_rows = list(
                (
                    await session.scalars(
                        select(KnowledgeItem)
                        .where(KnowledgeItem.tenant_id == tenant_id)
                        .order_by(KnowledgeItem.updated_at.desc())
                        .limit(12),
                    )
                ).all(),
            )
            for item in knowledge_rows:
                raw_score = _jaccard_score(objective_tokens, _tokenize_text(item.content_text[:600]))
                score = _score_for_source(source="knowledge", raw_score=raw_score)
                if score < float(dedup_cfg.source_min_score.get("knowledge", 0.0)):
                    continue
                candidates.append(
                    GrokReuseCandidateOut(
                        source_type="knowledge",
                        source_id=str(item.id),
                        title=_truncate_text(item.content_text, limit=180),
                        score=round(score, 3),
                        status=item.source_type,
                        updated_at=item.updated_at,
                    )
                )
        if "grok_history" in sources:
            run_rows = list(
                (
                    await session.scalars(
                        select(GrokRunORM)
                        .where(
                            GrokRunORM.tenant_id == tenant_id,
                            GrokRunORM.status.in_(("succeeded", "failed", "cancelled")),
                        )
                        .order_by(GrokRunORM.updated_at.desc())
                        .limit(10),
                    )
                ).all(),
            )
            for run in run_rows:
                raw_score = _jaccard_score(objective_tokens, _tokenize_text(run.objective))
                score = _score_for_source(source="grok_run", raw_score=raw_score)
                if score < float(dedup_cfg.source_min_score.get("grok_run", 0.0)):
                    continue
                candidates.append(
                    GrokReuseCandidateOut(
                        source_type="grok_run",
                        source_id=str(run.id),
                        title=_truncate_text(run.objective, limit=180),
                        score=round(score, 3),
                        status=run.status,
                        updated_at=run.updated_at,
                    )
                )

    candidates_sorted = sorted(candidates, key=lambda item: item.score, reverse=True)[:6]
    top_score = round(float(candidates_sorted[0].score), 3) if candidates_sorted else 0.0
    if top_score >= dedup_cfg.reuse_threshold:
        recommendation: Literal["reuse", "hybrid", "new"] = "reuse"
        rationale = "High overlap with existing outcomes. Start from prior artifacts/templates and run a focused delta."
    elif top_score >= dedup_cfg.hybrid_threshold:
        recommendation = "hybrid"
        rationale = "Partial overlap detected. Reuse known blocks but execute new run for changed scope."
    else:
        recommendation = "new"
        rationale = "Low overlap. Execute a fresh run; existing history offers little direct reuse."
    hard_gate_blocked = bool(dedup_cfg.hard_gate_enabled and recommendation == "reuse")
    return GrokIntakeAdviceOut(
        dedup_score=top_score,
        recommendation=recommendation,
        rationale=rationale,
        top_candidates=candidates_sorted,
        context_sources=sources,
        hard_gate_enabled=dedup_cfg.hard_gate_enabled,
        hard_gate_blocked=hard_gate_blocked,
        thresholds={
            "reuse": round(dedup_cfg.reuse_threshold, 3),
            "hybrid": round(dedup_cfg.hybrid_threshold, 3),
        },
    )


async def create_grok_template(tenant_id: uuid.UUID, body: GrokTemplateCreateIn) -> GrokTemplateOut:
    """Create one reusable Grok intake template."""

    cfg = _policy_config()
    run_probe = GrokRunCreateIn(
        objective=body.objective,
        scope_paths=body.scope_paths,
        run_mode=body.run_mode,
        risk_level=body.risk_level,
        command_profile=body.command_profile,
        context_sources=body.context_sources,
    )
    _validate_mode_policy(body=run_probe, cfg=cfg)
    async with async_session() as session:
        row = GrokRunTemplateORM(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            name=body.name.strip(),
            description=(body.description or "").strip() or None,
            objective=body.objective.strip(),
            scope_paths=_safe_scope_paths(body.scope_paths),
            run_mode=body.run_mode,
            risk_level=body.risk_level,
            command_profile=body.command_profile,
            context_sources=_safe_context_sources(body.context_sources),
            tags=_safe_tags(body.tags),
            is_archived=False,
        )
        session.add(row)
        await session.commit()
        await session.refresh(row)
        return _template_to_out(row)


async def update_grok_template(tenant_id: uuid.UUID, template_id: str, body: GrokTemplateUpdateIn) -> GrokTemplateOut:
    """Patch existing tenant template."""

    async with async_session() as session:
        row = await session.get(GrokRunTemplateORM, _parse_template_uuid(template_id))
        if row is None or row.tenant_id != tenant_id:
            raise LookupError("Template not found.")
        if body.name is not None:
            row.name = body.name.strip()
        if body.description is not None:
            row.description = body.description.strip() or None
        if body.objective is not None:
            row.objective = body.objective.strip()
        if body.scope_paths is not None:
            row.scope_paths = _safe_scope_paths(body.scope_paths)
        if body.run_mode is not None:
            row.run_mode = body.run_mode
        if body.risk_level is not None:
            row.risk_level = body.risk_level
        if body.command_profile is not None:
            row.command_profile = body.command_profile
        if body.context_sources is not None:
            row.context_sources = _safe_context_sources(body.context_sources)
        if body.tags is not None:
            row.tags = _safe_tags(body.tags)
        if body.is_archived is not None:
            row.is_archived = bool(body.is_archived)
        probe = GrokRunCreateIn(
            objective=row.objective,
            scope_paths=[str(item) for item in list(row.scope_paths or [])],
            run_mode=row.run_mode,  # type: ignore[arg-type]
            risk_level=row.risk_level,  # type: ignore[arg-type]
            command_profile=row.command_profile,
            context_sources=_safe_context_sources(list(row.context_sources or [])),
        )
        _validate_mode_policy(body=probe, cfg=_policy_config())
        row.updated_at = _utcnow()
        await session.commit()
        await session.refresh(row)
        return _template_to_out(row)


async def delete_grok_template(tenant_id: uuid.UUID, template_id: str) -> None:
    """Delete one template permanently."""

    async with async_session() as session:
        row = await session.get(GrokRunTemplateORM, _parse_template_uuid(template_id))
        if row is None or row.tenant_id != tenant_id:
            raise LookupError("Template not found.")
        await session.delete(row)
        await session.commit()


async def create_grok_run(tenant_id: uuid.UUID, dashboard_user_id: uuid.UUID, body: GrokRunCreateIn) -> GrokRunOut:
    """Create a run in draft/approval state."""

    if not settings.grok_control_plane_enabled:
        raise ValueError("Grok Control Plane disabled.")
    cfg = _policy_config()
    _validate_mode_policy(body=body, cfg=cfg)
    requires_approval = _requires_approval(risk_level=body.risk_level, run_mode=body.run_mode, cfg=cfg)
    context_sources = _safe_context_sources(body.context_sources)
    dedup_advice = await build_grok_intake_advice(
        tenant_id=tenant_id,
        body=GrokIntakeAdviceIn(
            objective=body.objective,
            scope_paths=body.scope_paths,
            context_sources=context_sources,
        ),
    )
    if dedup_advice.hard_gate_blocked and not body.force_fresh_run and body.run_mode != "read_only":
        msg = (
            "Dedup hard gate blocked this run due to high overlap. "
            "Reuse existing artifacts/template or set force_fresh_run=true to override."
        )
        raise ValueError(msg)
    async with async_session() as session:
        incoming_metadata = dict(body.metadata)
        escalation_kind = _escalation_kind_from_metadata(incoming_metadata)
        if escalation_kind:
            existing = await _existing_escalation_run_in_cooldown(
                session,
                tenant_id=tenant_id,
                escalation_kind=escalation_kind,
            )
            if existing is not None:
                tenant = await session.get(Tenant, tenant_id)
                _stamp_last_resumed_escalation(
                    tenant,
                    run_id=existing.id,
                    escalation_kind=escalation_kind,
                    resumed_at=_utcnow(),
                )
                _record_escalation_resume_event(
                    tenant,
                    run_id=existing.id,
                    escalation_kind=escalation_kind,
                    resumed_at=_utcnow(),
                )
                await session.commit()
                raise ValueError(
                    "Escalation cooldown active. "
                    f"Reuse existing escalation run {existing.id} "
                    f"(kind={escalation_kind}, created_at={existing.created_at.isoformat()})."
                )
        context_pack = await _build_context_pack(
            session,
            tenant_id=tenant_id,
            objective=body.objective.strip(),
            scope_paths=_safe_scope_paths(body.scope_paths),
            sources=context_sources,
        )
        metadata_payload = incoming_metadata
        metadata_payload["context_sources"] = context_sources
        metadata_payload["context_pack"] = context_pack
        metadata_payload["dedup_advice"] = dedup_advice.model_dump(mode="json")
        metadata_payload["dedup_override"] = bool(body.force_fresh_run)
        run_row = GrokRunORM(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            dashboard_user_id=dashboard_user_id,
            objective=body.objective.strip(),
            scope_paths=_safe_scope_paths(body.scope_paths),
            run_mode=body.run_mode,
            risk_level=body.risk_level,
            command_profile=body.command_profile,
            status="awaiting_approval" if requires_approval else "approved",
            requires_approval=requires_approval,
            metadata_json=metadata_payload,
        )
        session.add(run_row)
        await session.flush()

        if body.template_id:
            template_row = await session.get(GrokRunTemplateORM, _parse_template_uuid(body.template_id))
            if template_row is not None and template_row.tenant_id == tenant_id:
                template_row.usage_count = int(template_row.usage_count or 0) + 1
                template_row.last_used_at = _utcnow()
                template_row.updated_at = _utcnow()

        for index, step in enumerate(_default_plan(body)):
            session.add(
                GrokRunStepORM(
                    tenant_id=tenant_id,
                    run_id=run_row.id,
                    step_order=index,
                    step_id=step.id,
                    title=step.title,
                    kind=step.kind,
                    status=step.status,
                ),
            )
        await _append_event(
            session,
            run_row=run_row,
            level="info",
            code="run_created",
            message="Run created from cockpit intake.",
        )
        await _append_event(
            session,
            run_row=run_row,
            level="warning" if requires_approval else "success",
            code="approval_required" if requires_approval else "auto_approved",
            message=(
                "Run requires explicit approval before execution."
                if requires_approval
                else "Run auto-approved by policy."
            ),
        )
        await _append_event(
            session,
            run_row=run_row,
            level="info",
            code="context_attached",
            message=f"Context pack attached from sources: {', '.join(context_sources)}",
        )
        await session.commit()
        return await _hydrate_run(session, run_row)


async def list_grok_runs(tenant_id: uuid.UUID, *, limit: int = 30) -> list[GrokRunOut]:
    """List recent runs for tenant."""

    async with async_session() as session:
        rows = list(
            (
                await session.scalars(
                    select(GrokRunORM)
                    .where(GrokRunORM.tenant_id == tenant_id)
                    .order_by(GrokRunORM.created_at.desc())
                    .limit(max(1, min(limit, 80))),
                )
            ).all(),
        )
        out: list[GrokRunOut] = []
        for row in rows:
            out.append(await _hydrate_run(session, row))
        return out


async def get_grok_run(tenant_id: uuid.UUID, run_id: str) -> GrokRunOut:
    """Return one run, enforcing tenant ownership."""

    async with async_session() as session:
        run_uuid = _parse_run_uuid(run_id)
        row = await session.get(GrokRunORM, run_uuid)
        if row is None or row.tenant_id != tenant_id:
            raise LookupError("Run not found.")
        return await _hydrate_run(session, row)


async def approve_grok_run(tenant_id: uuid.UUID, run_id: str, *, approver: str, note: str | None) -> GrokRunOut:
    """Approve one run."""

    async with async_session() as session:
        row = await session.get(GrokRunORM, _parse_run_uuid(run_id))
        if row is None or row.tenant_id != tenant_id:
            raise LookupError("Run not found.")
        if row.status in {"running", "succeeded", "failed", "cancelled"}:
            raise ValueError("Cannot approve finalized run.")
        row.status = "approved"
        row.approved_by = approver
        row.approval_note = note
        row.updated_at = _utcnow()
        session.add(
            GrokRunApprovalORM(
                tenant_id=tenant_id,
                run_id=row.id,
                decision="approved",
                decided_by=approver,
                note=note,
            ),
        )
        await _append_event(session, run_row=row, level="success", code="run_approved", message=f"Approved by {approver}.")
        await session.commit()
        return await _hydrate_run(session, row)


async def reject_grok_run(tenant_id: uuid.UUID, run_id: str, *, approver: str, note: str | None) -> GrokRunOut:
    """Reject one run."""

    async with async_session() as session:
        row = await session.get(GrokRunORM, _parse_run_uuid(run_id))
        if row is None or row.tenant_id != tenant_id:
            raise LookupError("Run not found.")
        if row.status in {"running", "succeeded", "failed", "cancelled"}:
            raise ValueError("Cannot reject finalized run.")
        row.status = "rejected"
        row.approved_by = approver
        row.approval_note = note
        row.updated_at = _utcnow()
        session.add(
            GrokRunApprovalORM(
                tenant_id=tenant_id,
                run_id=row.id,
                decision="rejected",
                decided_by=approver,
                note=note,
            ),
        )
        await _append_event(session, run_row=row, level="warning", code="run_rejected", message=f"Rejected by {approver}.")
        await session.commit()
        return await _hydrate_run(session, row)


async def cancel_grok_run(tenant_id: uuid.UUID, run_id: str, *, actor: str, note: str | None) -> GrokRunOut:
    """Cancel one run."""

    async with async_session() as session:
        row = await session.get(GrokRunORM, _parse_run_uuid(run_id))
        if row is None or row.tenant_id != tenant_id:
            raise LookupError("Run not found.")
        if row.status in {"succeeded", "failed", "cancelled"}:
            return await _hydrate_run(session, row)
        row.status = "cancelled"
        row.updated_at = _utcnow()
        row.finished_at = _utcnow()
        if note:
            row.approval_note = note
        await _append_event(session, run_row=row, level="warning", code="run_cancelled", message=f"Cancelled by {actor}.")
        await session.commit()
        return await _hydrate_run(session, row)


async def queue_grok_run_execution(tenant_id: uuid.UUID, run_id: str, *, execute_commands: bool) -> GrokRunOut:
    """Queue Celery worker execution for a run."""

    async with async_session() as session:
        row = await session.get(GrokRunORM, _parse_run_uuid(run_id))
        if row is None or row.tenant_id != tenant_id:
            raise LookupError("Run not found.")
        if row.status != "approved":
            raise ValueError("Run must be approved before execution.")
        row.updated_at = _utcnow()
        await _append_event(session, run_row=row, level="info", code="run_queued", message="Run queued to worker.")
        await session.commit()
        hydrated = await _hydrate_run(session, row)
    from app.worker.tasks import grok_control_plane_execute_run_task

    grok_control_plane_execute_run_task.delay(str(tenant_id), run_id, execute_commands)
    return hydrated


async def _run_shell(command: str, *, timeout_sec: int) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        "bash",
        "-lc",
        command,
        cwd=str(_repo_root()),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout_sec)
    except TimeoutError:
        proc.kill()
        await proc.communicate()
        return 124, f"Command timeout after {timeout_sec}s: {command}"
    output = (stdout or b"").decode("utf-8", errors="replace")
    return int(proc.returncode or 0), output[-_MAX_OUTPUT_CHARS:]


def _grok_prompt_command(run: GrokRunORM) -> str:
    binary = shlex.quote(settings.grok_cp_cli_binary)
    objective = run.objective.replace('"', "'").strip()
    scope_paths = [str(item) for item in list(run.scope_paths or [])]
    scope = ", ".join(scope_paths) if scope_paths else "entire repository"
    metadata = dict(run.metadata_json or {})
    context_pack = metadata.get("context_pack")
    context_text = ""
    if isinstance(context_pack, dict):
        context_text = _render_context_pack(context_pack)
    context_fragment = f" Existing hive context: {context_text}" if context_text else ""
    return (
        f"{binary} --prompt "
        f"\"Create implementation plan for objective: {objective}. "
        f"Scope: {scope}.{context_fragment} Return concise bullet plan with focus on non-duplicate high-impact work.\""
    )


async def execute_grok_run(tenant_id: str, run_id: str, *, execute_commands: bool) -> GrokRunOut:
    """Worker runtime: execute planned steps and persist artifacts/events."""

    tenant_uuid = uuid.UUID(tenant_id)
    run_uuid = _parse_run_uuid(run_id)
    async with async_session() as session:
        run = await session.get(GrokRunORM, run_uuid)
        if run is None or run.tenant_id != tenant_uuid:
            raise LookupError("Run not found.")
        if run.status != "approved":
            return await _hydrate_run(session, run)

        cfg = _policy_config()
        run.status = "running"
        run.started_at = _utcnow()
        run.updated_at = _utcnow()
        await _append_event(session, run_row=run, level="info", code="run_started", message="Worker started run execution.")

        steps = list(
            (
                await session.scalars(
                    select(GrokRunStepORM)
                    .where(GrokRunStepORM.run_id == run.id)
                    .order_by(GrokRunStepORM.step_order.asc()),
                )
            ).all(),
        )
        profile_commands = cfg.allow_profiles.get(run.command_profile, [])
        success = True
        context_pack = dict(run.metadata_json or {}).get("context_pack")
        if isinstance(context_pack, dict):
            session.add(
                GrokRunArtifactORM(
                    tenant_id=tenant_uuid,
                    run_id=run.id,
                    artifact_kind="context",
                    title="Hive context pack",
                    mime_type="text/plain",
                    content_text=_render_context_pack(context_pack),
                    artifact_meta={"sources": list(context_pack.get("sources") or [])},
                ),
            )

        for step in steps:
            if step.status in {"done", "failed", "skipped"}:
                continue
            step.status = "running"
            step.started_at = _utcnow()

            if step.step_id == "plan":
                if settings.grok_cp_cli_enabled and _grok_cli_available():
                    command = _grok_prompt_command(run)
                    code, output = await _run_shell(command, timeout_sec=settings.grok_cp_command_timeout_sec)
                    step.command = command
                    step.output = output
                    step.exit_code = code
                    session.add(
                        GrokRunArtifactORM(
                            tenant_id=tenant_uuid,
                            run_id=run.id,
                            artifact_kind="plan",
                            title="Grok plan output",
                            mime_type="text/plain",
                            content_text=output,
                            artifact_meta={"command": command, "exit_code": code},
                        ),
                    )
                    if code != 0:
                        step.status = "failed"
                        await _append_event(
                            session,
                            run_row=run,
                            level="error",
                            code="plan_failed",
                            message="Grok CLI plan command failed.",
                        )
                        success = False
                    else:
                        step.status = "done"
                        await _append_event(
                            session,
                            run_row=run,
                            level="success",
                            code="plan_ready",
                            message="Grok plan generated.",
                        )
                else:
                    step.output = (
                        "Grok CLI unavailable/disabled. Plan fallback: scope objective, run checks, "
                        "review diff, then finalize artifacts."
                    )
                    step.status = "done"
                    await _append_event(
                        session,
                        run_row=run,
                        level="warning",
                        code="plan_fallback",
                        message="Used local fallback plan.",
                    )
            elif step.step_id in {"lint", "tests"}:
                if not execute_commands or not settings.grok_cp_execute_commands:
                    step.status = "skipped"
                    step.output = "Command execution disabled. Toggle execute_commands to run."
                    await _append_event(
                        session,
                        run_row=run,
                        level="warning",
                        code="commands_skipped",
                        message="Skipped command execution by policy.",
                    )
                elif not profile_commands:
                    step.status = "skipped"
                    step.output = "No allowed commands configured for selected profile."
                    await _append_event(
                        session,
                        run_row=run,
                        level="warning",
                        code="profile_empty",
                        message="No commands for profile.",
                    )
                else:
                    command = profile_commands[0] if step.step_id == "lint" else profile_commands[min(1, len(profile_commands) - 1)]
                    if not _apply_command_policy(command, cfg):
                        step.status = "failed"
                        step.output = "Command blocked by deny-pattern policy."
                        await _append_event(
                            session,
                            run_row=run,
                            level="error",
                            code="command_blocked",
                            message=f"Blocked command: {command}",
                        )
                        success = False
                    else:
                        code, output = await _run_shell(command, timeout_sec=settings.grok_cp_command_timeout_sec)
                        step.command = command
                        step.output = output
                        step.exit_code = code
                        session.add(
                            GrokRunArtifactORM(
                                tenant_id=tenant_uuid,
                                run_id=run.id,
                                artifact_kind="command_log",
                                title=f"{step.step_id} output",
                                mime_type="text/plain",
                                content_text=output,
                                artifact_meta={"command": command, "exit_code": code},
                            ),
                        )
                        if code == 0:
                            step.status = "done"
                        else:
                            step.status = "failed"
                            await _append_event(
                                session,
                                run_row=run,
                                level="error",
                                code="command_failed",
                                message=f"Command failed: {command}",
                            )
                            success = False
            else:
                step.status = "done"
                step.output = "Run summary + artifact bundle generated."
                session.add(
                    GrokRunArtifactORM(
                        tenant_id=tenant_uuid,
                        run_id=run.id,
                        artifact_kind="summary",
                        title="Run summary",
                        mime_type="text/plain",
                        content_text=step.output,
                        artifact_meta={},
                    ),
                )

            step.finished_at = _utcnow()
            run.updated_at = _utcnow()
            if not success:
                break

        run.finished_at = _utcnow()
        run.status = "succeeded" if success else "failed"
        run.updated_at = _utcnow()
        await _append_event(
            session,
            run_row=run,
            level="success" if success else "error",
            code="run_succeeded" if success else "run_failed",
            message="Run completed successfully." if success else "Run ended with failures.",
        )
        await session.commit()
        return await _hydrate_run(session, run)


async def push_grok_artifact_to_hivemind(
    tenant_id: uuid.UUID,
    run_id: str,
    artifact_id: str,
    *,
    actor: str,
    body: GrokPushArtifactToHiveMindIn | None = None,
) -> GrokPushArtifactToHiveMindOut:
    """Persist selected Grok artifact as KnowledgeItem (+ vector/graph mirrors)."""

    body = body or GrokPushArtifactToHiveMindIn()
    run_uuid = _parse_run_uuid(run_id)
    artifact_uuid = _parse_run_uuid(artifact_id)
    async with async_session() as session:
        run = await session.get(GrokRunORM, run_uuid)
        if run is None or run.tenant_id != tenant_id:
            raise LookupError("Run not found.")
        artifact = await session.get(GrokRunArtifactORM, artifact_uuid)
        if artifact is None or artifact.run_id != run.id or artifact.tenant_id != tenant_id:
            raise LookupError("Artifact not found.")
        text = (artifact.content_text or "").strip()
        if not text:
            raise ValueError("Artifact has no text content.")
        confidence_score, auto_priority = _artifact_confidence_and_priority(
            run_status=run.status,  # type: ignore[arg-type]
            artifact_kind=str(artifact.artifact_kind or ""),
            text=text,
        )
        confidence = (
            max(0.0, min(1.0, float(body.confidence_override)))
            if body.confidence_override is not None
            else confidence_score
        )
        priority: Literal["high", "medium", "low"] = body.priority_override or auto_priority
        if body.auto_priority is False and body.priority_override is None:
            priority = "medium"
        tags = _safe_tags(
            [
                "grok",
                "grok-output",
                "hivemind-candidate",
                f"grok-{artifact.artifact_kind}",
                f"priority-{priority}",
                f"confidence-{int(round(confidence * 100))}",
                *body.tags,
            ]
        )
        if priority == "low":
            tags = _safe_tags([*tags, "hivemind-review-pending"])
        row = KnowledgeItem(
            tenant_id=tenant_id,
            source_url=f"grok://run/{run.id}/artifact/{artifact.id}",
            source_type="grok_control_plane",
            content_text=text[:12000],
            confidence_score=confidence,
            topic_tags=tags,
            decay_factor=1.0,
            scraped_at=_utcnow(),
            verified_at=_utcnow() if run.status == "succeeded" else None,
        )
        session.add(row)
        await session.flush()

        embedding_id: str | None = None
        neo4j_id: str | None = None
        try:
            embedding_id = await embed_and_store(
                text=row.content_text,
                metadata={
                    "kind": "grok_artifact",
                    "tenant_id": str(tenant_id),
                    "knowledge_item_id": str(row.id),
                    "run_id": str(run.id),
                    "artifact_id": str(artifact.id),
                    "artifact_kind": artifact.artifact_kind,
                    "status": run.status,
                    "tags": ",".join(tags),
                },
                collection_name=HIVE_MIND_COLLECTION,
            )
        except Exception:
            embedding_id = None
        try:
            neo4j_id = await create_knowledge_node(
                content=row.content_text[:4000],
                source=f"grok:{run.id}:{artifact.id}",
                confidence=row.confidence_score,
                topic_tags=tags[:24],
            )
        except Exception:
            neo4j_id = None

        row.embedding_id = embedding_id
        row.neo4j_node_id = neo4j_id
        if "hivemind-review-pending" in {str(tag).strip().lower() for tag in tags}:
            await _maybe_escalate_hivemind_review_queue(session, tenant_id=tenant_id)
        await _append_event(
            session,
            run_row=run,
            level="success",
            code="artifact_pushed_hivemind",
            message=f"Artifact {artifact.id} pushed to HiveMind by {actor}.",
        )
        await session.commit()
        return GrokPushArtifactToHiveMindOut(
            run_id=str(run.id),
            artifact_id=str(artifact.id),
            knowledge_item_id=str(row.id),
            embedding_id=embedding_id,
            neo4j_node_id=neo4j_id,
            confidence_score=confidence,
            priority=priority,
            applied_tags=tags,
        )


async def _maybe_escalate_hivemind_review_queue(session: AsyncSession, *, tenant_id: uuid.UUID) -> None:
    """Send operator alerts when pending low-confidence queue exceeds threshold."""

    threshold = max(1, int(settings.grok_cp_hivemind_review_alert_threshold))
    age_threshold_hours = max(1, int(settings.grok_cp_hivemind_review_alert_max_age_hours))
    pending_count = int(
        (
            await session.scalar(
                select(func.count())
                .select_from(KnowledgeItem)
                .where(
                    KnowledgeItem.tenant_id == tenant_id,
                    KnowledgeItem.source_type == "grok_control_plane",
                    KnowledgeItem.topic_tags.contains(["hivemind-review-pending"]),
                ),
            )
        )
        or 0
    )
    oldest_pending_created_at = await session.scalar(
        select(func.min(KnowledgeItem.created_at))
        .where(
            KnowledgeItem.tenant_id == tenant_id,
            KnowledgeItem.source_type == "grok_control_plane",
            KnowledgeItem.topic_tags.contains(["hivemind-review-pending"]),
        ),
    )
    now = _utcnow()
    oldest_age_hours: float | None = None
    if oldest_pending_created_at is not None:
        ref = oldest_pending_created_at
        if ref.tzinfo is None:
            ref = ref.replace(tzinfo=UTC)
        oldest_age_hours = max(0.0, (now - ref).total_seconds() / 3600.0)
    escalation_reason = _review_queue_escalation_reason(
        pending_count=pending_count,
        threshold=threshold,
        oldest_age_hours=oldest_age_hours,
        age_threshold_hours=age_threshold_hours,
    )
    if escalation_reason is None:
        return

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        return
    if not _review_alert_timing_allowed(tenant=tenant, now=now):
        return

    dashboard_user_id = await session.scalar(
        select(DashboardUserTenantMembership.dashboard_user_id)
        .where(
            DashboardUserTenantMembership.tenant_id == tenant_id,
            DashboardUserTenantMembership.role.in_(("owner", "admin")),
        )
        .order_by(DashboardUserTenantMembership.created_at.asc())
        .limit(1),
    )
    if dashboard_user_id is None:
        return

    await notify_zero_ui_ping(
        session,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
        priority="critical",
        title="Grok HiveMind review queue alert",
        detail=(
            f"Pending low-confidence items: {pending_count} (threshold {threshold}). "
            f"Oldest age: {round(oldest_age_hours or 0.0, 1)}h (SLA {age_threshold_hours}h). "
            "Open cockpit queue and approve/reject."
        ),
        href="/cockpit#grok-control-plane",
    )
    await notify_execution_studio_pending_approval(
        tenant=tenant,
        title="Grok HiveMind queue requires review",
        message=f"Grok HiveMind review queue escalation: {escalation_reason}.",
        color="#FF3366",
        session=session,
    )
    _stamp_review_alert_sent(tenant=tenant, pending_count=pending_count, now=now)


async def list_grok_hivemind_review_queue(
    tenant_id: uuid.UUID,
    *,
    limit: int = 30,
) -> GrokHiveMindReviewQueueOut:
    """List low-confidence Grok HiveMind records requiring manual review."""

    async with async_session() as session:
        rows = list(
            (
                await session.scalars(
                    select(KnowledgeItem)
                    .where(
                        KnowledgeItem.tenant_id == tenant_id,
                        KnowledgeItem.source_type == "grok_control_plane",
                    )
                    .order_by(KnowledgeItem.updated_at.desc())
                    .limit(max(1, min(limit, 80))),
                )
            ).all(),
        )
        items: list[GrokHiveMindReviewItemOut] = []
        now = _utcnow()
        oldest_age_hours = 0.0
        for row in rows:
            tags = [str(tag).strip().lower() for tag in list(row.topic_tags or [])]
            tag_set = set(tags)
            if "hivemind-review-approved" in tag_set or "hivemind-review-rejected" in tag_set:
                continue
            priority = _extract_priority_from_tags(tags)
            if priority != "low" and row.confidence_score >= 0.7:
                continue
            ref = row.created_at
            if ref.tzinfo is None:
                ref = ref.replace(tzinfo=UTC)
            age_hours = max(0.0, (now - ref).total_seconds() / 3600.0)
            oldest_age_hours = max(oldest_age_hours, age_hours)
            items.append(
                GrokHiveMindReviewItemOut(
                    knowledge_item_id=str(row.id),
                    source_url=row.source_url,
                    confidence_score=round(float(row.confidence_score), 3),
                    priority=priority,
                    preview=_truncate_text(row.content_text, limit=240),
                    topic_tags=tags[:24],
                    created_at=row.created_at,
                    updated_at=row.updated_at,
                )
            )
        sla_hours = max(1, int(settings.grok_cp_hivemind_review_alert_max_age_hours))
        return GrokHiveMindReviewQueueOut(
            count=len(items),
            oldest_pending_age_hours=round(oldest_age_hours, 2),
            sla_hours=sla_hours,
            sla_breached=bool(oldest_age_hours >= float(sla_hours) and len(items) > 0),
            items=items,
        )


async def review_grok_hivemind_item(
    tenant_id: uuid.UUID,
    *,
    knowledge_item_id: str,
    body: GrokHiveMindReviewDecisionIn,
    actor: str,
) -> GrokHiveMindReviewDecisionOut:
    """Approve/reject a queued low-confidence Grok HiveMind item."""

    item_uuid = _parse_run_uuid(knowledge_item_id)
    async with async_session() as session:
        row = await session.get(KnowledgeItem, item_uuid)
        if row is None or row.tenant_id != tenant_id or row.source_type != "grok_control_plane":
            raise LookupError("HiveMind item not found.")
        tags = list(row.topic_tags or [])
        updated = _apply_hivemind_review_tags(tags, decision=body.decision)
        actor_tags = _safe_tags([f"reviewed-by-{actor}"]) if actor.strip() else []
        actor_tag = actor_tags[0] if actor_tags else None
        if actor_tag:
            updated = _safe_tags([*updated, actor_tag])
        if body.note and body.note.strip():
            note_tag = _safe_tags([f"review-note-{body.note.strip()[:40]}"])
            updated = _safe_tags([*updated, *note_tag])
        row.topic_tags = updated[:24]
        if body.decision == "approve":
            row.verified_at = _utcnow()
        row.updated_at = _utcnow()
        await session.commit()
        return GrokHiveMindReviewDecisionOut(
            knowledge_item_id=str(row.id),
            decision=body.decision,
            reviewed_at=_utcnow().isoformat(),
            topic_tags=[str(tag) for tag in list(row.topic_tags or [])][:24],
        )


__all__ = [
    "GrokControlPlaneSnapshotOut",
    "GrokIntakeAdviceIn",
    "GrokIntakeAdviceOut",
    "GrokHiveMindReviewDecisionIn",
    "GrokHiveMindReviewDecisionOut",
    "GrokHiveMindReviewItemOut",
    "GrokHiveMindReviewQueueOut",
    "GrokPushArtifactToHiveMindIn",
    "GrokPushArtifactToHiveMindOut",
    "GrokRunCreateIn",
    "GrokRunDecisionIn",
    "GrokRunOut",
    "GrokRunArtifactOut",
    "GrokRunApprovalOut",
    "GrokRunStartIn",
    "GrokTemplateCreateIn",
    "GrokTemplateOut",
    "GrokTemplateUpdateIn",
    "approve_grok_run",
    "build_grok_intake_advice",
    "cancel_grok_run",
    "compose_grok_control_plane_snapshot",
    "create_grok_template",
    "create_grok_run",
    "delete_grok_template",
    "execute_grok_run",
    "get_grok_run",
    "list_grok_templates",
    "list_grok_runs",
    "list_grok_run_approvals",
    "list_grok_run_artifacts",
    "list_grok_hivemind_review_queue",
    "queue_grok_run_execution",
    "reject_grok_run",
    "rerun_grok_run",
    "push_grok_artifact_to_hivemind",
    "review_grok_hivemind_item",
    "update_grok_template",
]
