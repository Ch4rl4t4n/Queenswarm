"""TR1 — Injection guard coverage dashboard."""

from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.injection_guard_telemetry import (
    CHECKPOINT_LABELS,
    GUARDED_EXTERNAL_TOOLS,
    injection_guard_store,
    merge_telemetry_patch,
    telemetry_bucket_from_settings,
)
from app.application.services.prompt_injection_guard import InjectionCheckpoint
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

CoverageStatus = Literal["healthy", "warn", "critical"]


class InjectionGuardCheckpointOut(BaseModel):
    """One 3-checkpoint row."""

    model_config = ConfigDict(extra="ignore")

    checkpoint_id: str
    label: str
    scans: int = 0
    blocked: int = 0
    block_rate_pct: float = 0.0
    coverage_pct: int = 100


class InjectionGuardToolOut(BaseModel):
    """Guard coverage for one external tool."""

    model_config = ConfigDict(extra="ignore")

    tool_name: str
    label: str
    scans: int = 0
    blocked: int = 0
    covered: bool = True
    checkpoint_id: str = InjectionCheckpoint.EXTERNAL_TOOL.value


class InjectionGuardHitOut(BaseModel):
    """Recent blocked hit."""

    model_config = ConfigDict(extra="ignore")

    at: str
    checkpoint_id: str
    checkpoint_label: str
    tool_name: str | None = None
    matched_pattern: str | None = None


class InjectionGuardCoverageOut(BaseModel):
    """Operator trust dashboard snapshot for TR1."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    status: CoverageStatus = "healthy"
    total_scans: int = 0
    total_blocked: int = 0
    guarded_tool_count: int = 0
    checkpoints: list[InjectionGuardCheckpointOut] = Field(default_factory=list)
    tools: list[InjectionGuardToolOut] = Field(default_factory=list)
    recent_hits: list[InjectionGuardHitOut] = Field(default_factory=list)
    operator_hint: str = "All external fetch/search tools pass through the 3-checkpoint injection guard."
    updated_at: str | None = None


def _block_rate(blocked: int, scans: int) -> float:
    if scans <= 0:
        return 0.0
    return round((blocked / scans) * 100.0, 2)


def _resolve_status(total_blocked: int, recent_blocked: int) -> CoverageStatus:
    if recent_blocked >= 3 or total_blocked >= 10:
        return "critical"
    if recent_blocked >= 1 or total_blocked >= 3:
        return "warn"
    return "healthy"


def derive_injection_guard_coverage(bucket: dict) -> InjectionGuardCoverageOut:  # noqa: ANN001
    """Build TR1 dashboard from merged telemetry bucket."""

    checkpoints: list[InjectionGuardCheckpointOut] = []
    total_scans = 0
    total_blocked = 0
    cp_rows = dict(bucket.get("checkpoints") or {})
    for checkpoint_id, label in CHECKPOINT_LABELS.items():
        row = cp_rows.get(checkpoint_id) or {}
        scans = int(row.get("scans") or 0)
        blocked = int(row.get("blocked") or 0)
        total_scans += scans
        total_blocked += blocked
        checkpoints.append(
            InjectionGuardCheckpointOut(
                checkpoint_id=checkpoint_id,
                label=label,
                scans=scans,
                blocked=blocked,
                block_rate_pct=_block_rate(blocked, scans),
                coverage_pct=100,
            ),
        )

    tool_rows = dict(bucket.get("tools") or {})
    tools: list[InjectionGuardToolOut] = []
    for tool_name, tool_label in GUARDED_EXTERNAL_TOOLS:
        row = tool_rows.get(tool_name) or {"scans": 0, "blocked": 0}
        tools.append(
            InjectionGuardToolOut(
                tool_name=tool_name,
                label=tool_label,
                scans=int(row.get("scans") or 0),
                blocked=int(row.get("blocked") or 0),
                covered=True,
            ),
        )
    for tool_name, row in tool_rows.items():
        if any(item.tool_name == tool_name for item in tools):
            continue
        tools.append(
            InjectionGuardToolOut(
                tool_name=tool_name,
                label=tool_name.replace("_", " ").title(),
                scans=int(row.get("scans") or 0),
                blocked=int(row.get("blocked") or 0),
                covered=True,
            ),
        )

    recent_raw = list(bucket.get("recent_hits") or [])[:8]
    recent_hits = [
        InjectionGuardHitOut(
            at=str(row.get("at") or ""),
            checkpoint_id=str(row.get("checkpoint") or ""),
            checkpoint_label=CHECKPOINT_LABELS.get(str(row.get("checkpoint") or ""), "Unknown"),
            tool_name=str(row.get("tool_name")).strip() if row.get("tool_name") else None,
            matched_pattern=str(row.get("matched_pattern") or "").strip() or None,
        )
        for row in recent_raw
        if isinstance(row, dict)
    ]

    status = _resolve_status(total_blocked, len(recent_hits))
    if status == "critical":
        hint = "Multiple injection markers blocked recently — review recent hits and operator inputs."
    elif status == "warn":
        hint = "At least one injection marker blocked — verify external tool output before approving live actions."
    elif total_scans == 0:
        hint = "No guard scans recorded yet — coverage is armed on operator input, external tools, and agent output."
    else:
        hint = "Guard coverage active — external tools and session outputs scanned at all three checkpoints."

    return InjectionGuardCoverageOut(
        enabled=True,
        status=status,
        total_scans=total_scans,
        total_blocked=total_blocked,
        guarded_tool_count=len(GUARDED_EXTERNAL_TOOLS),
        checkpoints=checkpoints,
        tools=tools,
        recent_hits=recent_hits,
        operator_hint=hint,
        updated_at=str(bucket.get("updated_at") or "") or None,
    )


async def compose_injection_guard_coverage(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> InjectionGuardCoverageOut:
    """Flush pending telemetry and compose TR1 injection guard coverage dashboard."""

    if not settings.injection_guard_coverage_enabled:
        return InjectionGuardCoverageOut(enabled=False)

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        return InjectionGuardCoverageOut(enabled=True, status="healthy")

    pending = injection_guard_store.drain_patch(tenant_id)
    if pending:
        tenant.operator_settings = merge_telemetry_patch(tenant.operator_settings, pending)
        await session.flush()

    bucket = telemetry_bucket_from_settings(tenant.operator_settings)
    coverage = derive_injection_guard_coverage(bucket)
    _logger.info(
        "injection_guard_coverage.composed",
        agent_id="injection_guard_coverage",
        swarm_id=str(tenant_id),
        status=coverage.status,
        total_scans=coverage.total_scans,
        total_blocked=coverage.total_blocked,
    )
    return coverage


__all__ = [
    "InjectionGuardCheckpointOut",
    "InjectionGuardCoverageOut",
    "InjectionGuardHitOut",
    "InjectionGuardToolOut",
    "compose_injection_guard_coverage",
    "derive_injection_guard_coverage",
]
