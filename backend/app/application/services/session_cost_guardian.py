"""Per-supervisor-session cost guardrail (complements the daily CostGovernor).

Aggregates ``CostRecord`` rows scoped to a supervisor session's lifetime so
operators (and the Queen herself) see when a single session is about to blow
through its per-session ceiling (default $0.50).

This deliberately does NOT add a new DB column — we infer per-session spend
by intersecting ``cost_records`` rows with the session's ``started_at`` /
``completed_at`` window (tenant-scoped). That keeps the change purely
additive and rollback-safe.

Output states:
- ``ok``    — under warn_ratio of cap
- ``warn``  — between warn_ratio and 1.0 of cap (Queen should sub-divide)
- ``halt``  — over cap (Queen must stop, return smaller plan to operator)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.cost import CostRecord
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession

DEFAULT_SESSION_CAP_USD = 0.50
DEFAULT_WARN_RATIO = 0.60

State = Literal["ok", "warn", "halt"]


@dataclass(slots=True)
class SessionCostState:
    """Per-session spend snapshot the Orchestrator can read between turns."""

    session_id: uuid.UUID
    spent_usd: float
    cap_usd: float
    warn_ratio: float
    utilization: float
    state: State
    hint: str
    started_at: datetime | None
    completed_at: datetime | None

    def to_payload(self) -> dict[str, object]:
        """Plain-JSON dict for API + orchestrator context_summary embedding."""

        return {
            "session_id": str(self.session_id),
            "spent_usd": round(self.spent_usd, 4),
            "cap_usd": round(self.cap_usd, 4),
            "warn_ratio": round(self.warn_ratio, 3),
            "utilization": round(self.utilization, 3),
            "state": self.state,
            "hint": self.hint,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


def _hint_for(state: State, utilization: float, cap_usd: float) -> str:
    """Return a short, action-oriented hint string for the given state."""

    if state == "halt":
        return (
            f"Session exceeded ${cap_usd:.2f} cap. Stop further LLM hops; return a "
            "smaller scoped plan to the operator with rationale."
        )
    if state == "warn":
        return (
            f"At {utilization * 100:.0f}% of ${cap_usd:.2f} cap. Sub-divide the next "
            "step into 2 smaller delegations or fall back to a cached recipe."
        )
    return "Under budget."


async def measure_session_cost(
    db: AsyncSession,
    *,
    session_id: uuid.UUID,
    cap_usd: float = DEFAULT_SESSION_CAP_USD,
    warn_ratio: float = DEFAULT_WARN_RATIO,
) -> SessionCostState:
    """Compute spend + state for one supervisor session.

    Args:
        db: Active async SQLAlchemy session.
        session_id: SupervisorSession UUID to measure.
        cap_usd: Hard ceiling above which state flips to ``halt``.
        warn_ratio: Fraction of cap above which state flips to ``warn``.
    """

    sess = await db.get(SupervisorSession, session_id)
    if sess is None:
        msg = f"SupervisorSession {session_id} not found"
        raise ValueError(msg)

    started = sess.started_at
    end = sess.completed_at or datetime.now(tz=UTC)
    stmt = select(func.coalesce(func.sum(CostRecord.cost_usd), 0.0)).where(
        CostRecord.created_at >= started if started is not None else CostRecord.created_at.isnot(None),
        CostRecord.created_at <= end,
    )
    if sess.tenant_id is not None:
        stmt = stmt.where(CostRecord.tenant_id == sess.tenant_id)
    spent = float(await db.scalar(stmt) or 0.0)

    utilization = spent / cap_usd if cap_usd > 0 else 0.0
    if utilization >= 1.0:
        state: State = "halt"
    elif utilization >= warn_ratio:
        state = "warn"
    else:
        state = "ok"

    return SessionCostState(
        session_id=session_id,
        spent_usd=spent,
        cap_usd=cap_usd,
        warn_ratio=warn_ratio,
        utilization=utilization,
        state=state,
        hint=_hint_for(state, utilization, cap_usd),
        started_at=started,
        completed_at=sess.completed_at,
    )


__all__ = [
    "DEFAULT_SESSION_CAP_USD",
    "DEFAULT_WARN_RATIO",
    "SessionCostState",
    "State",
    "measure_session_cost",
]
