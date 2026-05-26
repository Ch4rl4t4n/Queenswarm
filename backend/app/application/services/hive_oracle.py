"""Hive Oracle v2 — predictive warnings + optional LLM-light synthesis (compose-only)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.operator_control_plane import OperatorLoopActionOut
from app.core.config import settings

logger = structlog.get_logger(__name__)

OracleSeverity = Literal["low", "medium", "high", "critical"]
OracleHorizon = Literal["today", "week"]


class HiveOracleWarningOut(BaseModel):
    """One predictive warning with fix link."""

    model_config = ConfigDict(extra="ignore")

    id: str
    severity: OracleSeverity
    message: str
    fix_href: str | None = None
    confidence_pct: int = Field(default=85, ge=0, le=100)


class HiveOraclePredictionOut(BaseModel):
    """Forward-looking heuristic prediction."""

    model_config = ConfigDict(extra="ignore")

    id: str
    horizon: OracleHorizon
    message: str
    likelihood_pct: int = Field(default=60, ge=0, le=100)


class HiveOracleSnapshotOut(BaseModel):
    """Hive Oracle snapshot for /operator/oracle and cockpit widget."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    generated_at: datetime
    warnings: list[HiveOracleWarningOut] = Field(default_factory=list)
    predictions: list[HiveOraclePredictionOut] = Field(default_factory=list)
    synthesis_md: str = ""
    synthesis_model: str | None = None
    llm_synthesis_enabled: bool = False
    metrics: dict[str, Any] = Field(default_factory=dict)


def _warning_dicts(warnings: list[HiveOracleWarningOut]) -> list[dict[str, str]]:
    """Legacy cockpit shape."""

    return [
        {
            "id": row.id,
            "severity": row.severity,
            "message": row.message,
            "fix_href": row.fix_href or "",
        }
        for row in warnings
    ]


def derive_heuristic_warnings(
    *,
    loop_actions: list[OperatorLoopActionOut],
    fleet: list[Any],
    trio: dict[str, Any],
    loop: dict[str, Any] | None = None,
    innovation_pending: int = 0,
) -> list[HiveOracleWarningOut]:
    """Rule-based predictive warnings — fast, no LLM."""

    warnings: list[HiveOracleWarningOut] = []
    loop_raw = loop or {}

    bound = int(trio.get("lanes_bound") or trio.get("bound_lane_count") or 0)
    if bound < 3:
        warnings.append(
            HiveOracleWarningOut(
                id="trio_unbound",
                severity="medium",
                message=f"My 3 Bees {bound}/3 bound — morning cycle may skip lanes.",
                fix_href="/settings/harness",
                confidence_pct=90,
            ),
        )

    quarantined = [item for item in fleet if str(getattr(item, "immune_status", "")) == "quarantine"]
    if quarantined:
        warnings.append(
            HiveOracleWarningOut(
                id="immune_quarantine",
                severity="high",
                message=f"{len(quarantined)} routine(s) in immune quarantine — review before autopilot.",
                fix_href="/cockpit#swarm-fleet",
                confidence_pct=95,
            ),
        )

    watch = [item for item in fleet if str(getattr(item, "immune_status", "")) == "watch"]
    if watch and not quarantined:
        warnings.append(
            HiveOracleWarningOut(
                id="immune_watch",
                severity="medium",
                message=f"{len(watch)} routine(s) on immune watch — failure streak detected.",
                fix_href="/cockpit#swarm-fleet",
                confidence_pct=80,
            ),
        )

    for action in loop_actions:
        if action.id == "approve_publish":
            warnings.append(
                HiveOracleWarningOut(
                    id="publish_backlog",
                    severity="high",
                    message=action.label,
                    fix_href=action.href or "/integrations?tab=studio#publish-queue",
                    confidence_pct=92,
                ),
            )
            break

    overnight = loop_raw.get("overnight") or {}
    stalled = int(overnight.get("stalled_signals") or 0)
    if stalled > 0:
        warnings.append(
            HiveOracleWarningOut(
                id="overnight_stalled",
                severity="medium",
                message=f"{stalled} overnight signal(s) stalled — Dump Sleep may need attention.",
                fix_href="/knowledge",
                confidence_pct=78,
            ),
        )

    onboard = loop_raw.get("publish_onboarding") or {}
    progress = int(onboard.get("progress_pct") or 0)
    if 0 < progress < 100:
        warnings.append(
            HiveOracleWarningOut(
                id="publish_onboarding_gap",
                severity="medium" if progress >= 60 else "high",
                message=f"Publish onboarding {progress}% — live lane blocked until complete.",
                fix_href="/settings/harness",
                confidence_pct=88,
            ),
        )

    trading = loop_raw.get("trading") or {}
    perf = trading.get("performance") if isinstance(trading.get("performance"), dict) else {}
    if perf.get("is_halted"):
        warnings.append(
            HiveOracleWarningOut(
                id="trading_halted",
                severity="high",
                message="Paper trading halted — review risk limits before next session.",
                fix_href="/integrations?tab=studio#trading-cockpit",
                confidence_pct=94,
            ),
        )

    if innovation_pending > 0:
        warnings.append(
            HiveOracleWarningOut(
                id="innovation_pending",
                severity="low" if innovation_pending == 1 else "medium",
                message=f"{innovation_pending} Innovation Lab proposal(s) awaiting review.",
                fix_href="/cockpit#innovation-lab",
                confidence_pct=100,
            ),
        )

    inactive_autopilot = [
        r for r in fleet if bool(getattr(r, "autopilot", False)) and not bool(getattr(r, "active", True))
    ]
    if len(inactive_autopilot) >= 2:
        warnings.append(
            HiveOracleWarningOut(
                id="fleet_paused",
                severity="medium",
                message=f"{len(inactive_autopilot)} autopilot routines paused — swarm throughput reduced.",
                fix_href="/cockpit#swarm-fleet",
                confidence_pct=85,
            ),
        )

    severity_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    warnings.sort(key=lambda row: severity_rank.get(row.severity, 9))
    return warnings[:8]


def derive_heuristic_predictions(
    *,
    warnings: list[HiveOracleWarningOut],
    fleet: list[Any],
    loop: dict[str, Any] | None = None,
) -> list[HiveOraclePredictionOut]:
    """Short-horizon predictions from warning + fleet signals."""

    predictions: list[HiveOraclePredictionOut] = []
    loop_raw = loop or {}
    pending = int((loop_raw.get("publish_pipeline") or {}).get("pending_publish_count") or 0)

    if pending >= 3:
        predictions.append(
            HiveOraclePredictionOut(
                id="publish_backlog_slip",
                horizon="today",
                message="Publish backlog likely delays morning brief pipeline unless queue cleared.",
                likelihood_pct=min(95, 60 + pending * 8),
            ),
        )

    if any(w.id == "immune_quarantine" for w in warnings):
        predictions.append(
            HiveOraclePredictionOut(
                id="routine_miss_cron",
                horizon="today",
                message="Quarantined routine(s) will miss next scheduled run without resume.",
                likelihood_pct=88,
            ),
        )

    due_soon = [
        r
        for r in fleet
        if bool(getattr(r, "active", False))
        and getattr(r, "next_run_at", None)
        and str(getattr(r, "immune_status", "healthy")) != "healthy"
    ]
    if due_soon:
        predictions.append(
            HiveOraclePredictionOut(
                id="watch_routine_fail",
                horizon="week",
                message="Watch-status routines have elevated fail probability this week.",
                likelihood_pct=65,
            ),
        )

    if not predictions and not warnings:
        predictions.append(
            HiveOraclePredictionOut(
                id="stable_hive",
                horizon="today",
                message="Hive signals stable — Trust Autopilot can run on schedule.",
                likelihood_pct=75,
            ),
        )

    return predictions[:5]


async def _synthesize_with_llm(
    *,
    warnings: list[HiveOracleWarningOut],
    predictions: list[HiveOraclePredictionOut],
    metrics: dict[str, Any],
) -> tuple[str, str | None]:
    """Optional cheap LLM synthesis — best-effort, never blocks snapshot."""

    if not settings.hive_oracle_llm_synthesis_enabled:
        return "", None

    model = (settings.hive_oracle_synthesis_model or "gpt-4o-mini").strip()
    lines = ["Warnings:"]
    for w in warnings[:5]:
        lines.append(f"- [{w.severity}] {w.message}")
    lines.append("Predictions:")
    for p in predictions[:3]:
        lines.append(f"- ({p.horizon}) {p.message} ~{p.likelihood_pct}%")
    lines.append(f"Metrics: {metrics}")

    system = (
        "You are Hive Oracle for Queenswarm operator cockpit. "
        "Write 2-3 short sentences in Slovak: what matters now + one recommended action. "
        "Verify-first tone. No hype."
    )
    prompt = "\n".join(lines)

    try:
        from app.core.llm_router import llm_complete

        text = await llm_complete(
            prompt,
            system=system,
            max_tokens=180,
            temperature=0.2,
            swarm_id="hive_oracle",
            task_id="oracle_synthesis",
        )
        return text[:800], model
    except Exception as exc:
        logger.warning(
            "hive_oracle.llm_synthesis_failed",
            agent_id="hive_oracle",
            task_id="oracle_synthesis",
            error=str(exc),
        )
        return "", None


async def compose_hive_oracle_snapshot(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    loop_actions: list[OperatorLoopActionOut],
    fleet: list[Any],
    trio: dict[str, Any],
    loop: dict[str, Any] | None = None,
    innovation_pending: int = 0,
    include_synthesis: bool = True,
) -> HiveOracleSnapshotOut:
    """Assemble Hive Oracle v2 snapshot."""

    if not settings.hive_oracle_enabled:
        return HiveOracleSnapshotOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            llm_synthesis_enabled=settings.hive_oracle_llm_synthesis_enabled,
        )

    warnings = derive_heuristic_warnings(
        loop_actions=loop_actions,
        fleet=fleet,
        trio=trio,
        loop=loop,
        innovation_pending=innovation_pending,
    )
    predictions = derive_heuristic_predictions(warnings=warnings, fleet=fleet, loop=loop)

    loop_raw = loop or {}
    metrics = {
        "trio_bound": int(trio.get("lanes_bound") or trio.get("bound_lane_count") or 0),
        "fleet_count": len(fleet),
        "publish_pending": int((loop_raw.get("publish_pipeline") or {}).get("pending_publish_count") or 0),
        "innovation_pending": innovation_pending,
        "warning_count": len(warnings),
    }

    synthesis_md = ""
    synthesis_model: str | None = None
    if include_synthesis and settings.hive_oracle_llm_synthesis_enabled:
        synthesis_md, synthesis_model = await _synthesize_with_llm(
            warnings=warnings,
            predictions=predictions,
            metrics=metrics,
        )

    return HiveOracleSnapshotOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        warnings=warnings,
        predictions=predictions,
        synthesis_md=synthesis_md,
        synthesis_model=synthesis_model,
        llm_synthesis_enabled=settings.hive_oracle_llm_synthesis_enabled,
        metrics=metrics,
    )


__all__ = [
    "HiveOraclePredictionOut",
    "HiveOracleSnapshotOut",
    "HiveOracleWarningOut",
    "_warning_dicts",
    "compose_hive_oracle_snapshot",
    "derive_heuristic_predictions",
    "derive_heuristic_warnings",
]
