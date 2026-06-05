"""BA5 — Proactive Pulse: midday what-changed / what-ran digest."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.approval_inbox import compose_approval_inbox_snapshot
from app.application.services.background_business_team import compose_background_business_team
from app.application.services.operator_loop import compose_operator_loop_lite
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

PulsePhase = Literal["morning", "midday", "evening", "anytime"]


class ProactivePulseChangeOut(BaseModel):
    """One delta line in the pulse."""

    model_config = ConfigDict(extra="ignore")

    id: str
    category: str
    label: str
    detail: str
    severity: Literal["info", "warn", "success"] = "info"


class ProactivePulseAutonomousOut(BaseModel):
    """Something that ran without operator action."""

    model_config = ConfigDict(extra="ignore")

    id: str
    label: str
    detail: str
    ran_at: datetime | None = None


class ProactivePulseOut(BaseModel):
    """Midday (or anytime) proactive pulse."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    phase: PulsePhase = "midday"
    headline: str = ""
    changes: list[ProactivePulseChangeOut] = Field(default_factory=list)
    autonomous_runs: list[ProactivePulseAutonomousOut] = Field(default_factory=list)
    links: dict[str, str] = Field(default_factory=dict)


PULSE_SETTINGS_KEY = "proactive_pulse"


def _pulse_root(tenant: Tenant | None) -> dict[str, Any]:
    if tenant is None:
        return {}
    root = dict(tenant.operator_settings or {})
    block = root.get(PULSE_SETTINGS_KEY)
    return dict(block) if isinstance(block, dict) else {}


def record_pulse_snapshot(tenant: Tenant, *, phase: PulsePhase, headline: str) -> None:
    """Persist last pulse for dedup and UI."""

    root = dict(tenant.operator_settings or {})
    root[PULSE_SETTINGS_KEY] = {
        "last_phase": phase,
        "last_headline": headline[:200],
        "last_at": datetime.now(tz=UTC).isoformat(),
    }
    tenant.operator_settings = root


async def _sessions_since(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    since: datetime,
) -> int:
    value = await db.scalar(
        select(func.count())
        .select_from(SupervisorSession)
        .where(
            SupervisorSession.tenant_id == tenant_id,
            SupervisorSession.created_at >= since,
        ),
    )
    return int(value or 0)


async def compose_proactive_pulse(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
    phase: PulsePhase = "midday",
) -> ProactivePulseOut:
    """Compose proactive pulse — no LLM, verified subsystem reads only."""

    if not settings.proactive_pulse_enabled or not settings.operator_control_plane_enabled:
        return ProactivePulseOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
            phase=phase,
        )

    now = datetime.now(tz=UTC)
    since = now.replace(hour=0, minute=0, second=0, microsecond=0)
    if phase == "midday":
        since = now - timedelta(hours=6)

    changes: list[ProactivePulseChangeOut] = []
    autonomous: list[ProactivePulseAutonomousOut] = []

    loop = await compose_operator_loop_lite(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
        phase="anytime",
    )
    pending_publish = int((loop.publish_pipeline or {}).get("pending_publish_count") or 0)
    if pending_publish > 0:
        changes.append(
            ProactivePulseChangeOut(
                id="publish_pending",
                category="marketing",
                label=f"{pending_publish} publish pack(s) awaiting approval",
                detail="Simulate-first — review in Execution Studio publish queue.",
                severity="warn",
            ),
        )

    trading = loop.trading or {}
    perf = trading.get("performance") if isinstance(trading.get("performance"), dict) else {}
    if perf.get("is_halted"):
        changes.append(
            ProactivePulseChangeOut(
                id="trading_halted",
                category="trading",
                label="Trading agent halted",
                detail=str(perf.get("halt_reason") or "Review Trading Cockpit."),
                severity="warn",
            ),
        )

    inbox = await compose_approval_inbox_snapshot(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
        limit=10,
    )
    total_pending = int(inbox.counts.total or 0)
    if total_pending > 0:
        changes.append(
            ProactivePulseChangeOut(
                id="approval_inbox",
                category="governance",
                label=f"{total_pending} item(s) in Approval Inbox",
                detail="Publish, lane digests, and agent suggestions need operator review.",
                severity="warn" if total_pending >= 3 else "info",
            ),
        )

    session_count = await _sessions_since(db, tenant_id=tenant_id, since=since)
    if session_count > 0:
        autonomous.append(
            ProactivePulseAutonomousOut(
                id="supervisor_sessions",
                label=f"{session_count} supervisor session(s) since window start",
                detail="Includes CBO dispatch and manual session starts.",
                ran_at=now,
            ),
        )

    team = await compose_background_business_team(db, tenant_id=tenant_id, tenant=tenant)
    for bee in team.bees:
        if bee.last_run_at is None:
            continue
        if bee.last_run_at >= since:
            autonomous.append(
                ProactivePulseAutonomousOut(
                    id=f"bee_{bee.bee_id}",
                    label=f"{bee.label} heartbeat",
                    detail=bee.summary or bee.status,
                    ran_at=bee.last_run_at,
                ),
            )
        elif bee.status == "attention":
            changes.append(
                ProactivePulseChangeOut(
                    id=f"bee_attention_{bee.bee_id}",
                    category="background_team",
                    label=f"{bee.label} needs attention",
                    detail=bee.summary,
                    severity="warn",
                ),
            )

    overnight = loop.overnight or {}
    if overnight.get("available"):
        ingested = int(overnight.get("items_ingested") or 0)
        if ingested > 0:
            autonomous.append(
                ProactivePulseAutonomousOut(
                    id="overnight_dump",
                    label=f"Overnight dump ingested {ingested} item(s)",
                    detail=f"Stalled signals: {overnight.get('stalled_signals', 0)}",
                    ran_at=now,
                ),
            )

    if changes:
        headline = changes[0].label
    elif autonomous:
        headline = f"{len(autonomous)} autonomous run(s) today"
    else:
        headline = "No urgent changes — business loop steady"

    if tenant is not None:
        record_pulse_snapshot(tenant, phase=phase, headline=headline)

    return ProactivePulseOut(
        enabled=True,
        generated_at=now,
        phase=phase,
        headline=headline,
        changes=changes,
        autonomous_runs=autonomous,
        links={
            "cockpit": "/cockpit",
            "approvals": "/cockpit#approvals",
            "mission_control": "/tasks",
        },
    )


__all__ = [
    "ProactivePulseOut",
    "compose_proactive_pulse",
    "record_pulse_snapshot",
]
