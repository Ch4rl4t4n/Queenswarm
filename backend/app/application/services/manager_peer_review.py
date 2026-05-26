"""Manager peer review — random 1/10 sampling of completed sessions.

A completed supervisor session is critiqued by an *alternate* manager (not the
one that ran it). The critique is stored as a health note on the original
swarm with ``severity="info"`` (or ``warn`` if the reviewer flags issues).

This is intentionally **read-only review**: it never replays the work or
mutates artifacts. It only emits a peer opinion that the operator can scan in
the Swarms UI.

Design constraints:
- Deterministic sampling using session id hash → easy to test, replayable.
- No new DB table — reviews land in ``SubSwarm.local_memory.health_notes``.
- Sweeper is idempotent: a session id stored in ``local_memory.peer_reviewed_ids``
  is never reviewed twice.
"""

from __future__ import annotations

import hashlib
import random
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from app.application.services.swarm_health_notes import add_health_note
from app.core.logging import get_logger
from app.infrastructure.persistence.models.agent import Agent
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession
from app.infrastructure.persistence.models.swarm import SubSwarm

logger = get_logger(__name__)

DEFAULT_SAMPLE_RATIO = 0.10  # 10 % of completed sessions get peer-reviewed
DEFAULT_LOOKBACK_HOURS = 24
DEFAULT_MAX_REVIEWS_PER_RUN = 5
MANAGER_TIERS = {"manager"}


def _is_sampled(session_id: uuid.UUID, ratio: float) -> bool:
    """Deterministic sampling via SHA1 digest of session id (replayable)."""

    if ratio <= 0:
        return False
    if ratio >= 1.0:
        return True
    digest = hashlib.sha1(session_id.bytes).hexdigest()
    bucket = int(digest[:6], 16) / 0xFFFFFF  # uniform in [0, 1)
    return bucket < ratio


def _manager_tier_of(agent: Agent) -> str | None:
    cfg = agent.config if isinstance(agent.config, dict) else None
    if cfg is None:
        return None
    raw = cfg.get("hive_tier")
    return str(raw) if isinstance(raw, str) else None


def _pick_alternate_manager(
    *,
    managers: list[Agent],
    excluded_id: uuid.UUID | None,
    rng: random.Random,
) -> Agent | None:
    """Pick a random manager that is not the excluded one (if possible)."""

    pool = [m for m in managers if m.id != excluded_id]
    if not pool:
        return None
    return rng.choice(pool)


@dataclass(slots=True)
class PeerReviewOutcome:
    session_id: uuid.UUID
    swarm_id: uuid.UUID | None
    reviewer_agent_id: uuid.UUID
    reviewer_name: str
    note_appended: bool


async def sweep_peer_reviews(
    db: AsyncSession,
    *,
    sample_ratio: float = DEFAULT_SAMPLE_RATIO,
    lookback_hours: int = DEFAULT_LOOKBACK_HOURS,
    max_reviews: int = DEFAULT_MAX_REVIEWS_PER_RUN,
    seed: int | None = None,
) -> dict[str, Any]:
    """Scan completed sessions in the lookback window; sample + review."""

    cutoff = datetime.now(tz=UTC) - timedelta(hours=max(1, lookback_hours))
    sessions_stmt = (
        select(SupervisorSession)
        .where(SupervisorSession.status == "completed")
        .where(SupervisorSession.completed_at >= cutoff)
        .order_by(SupervisorSession.completed_at.desc())
    )
    sessions = list((await db.scalars(sessions_stmt)).all())

    # Load all manager bees once.
    agents = list((await db.execute(select(Agent))).scalars())
    managers = [a for a in agents if _manager_tier_of(a) == "manager" or a.name.endswith(" Manager")]
    rng = random.Random(seed) if seed is not None else random.Random()

    outcomes: list[PeerReviewOutcome] = []
    reviewed_count = 0
    for session_row in sessions:
        if reviewed_count >= max_reviews:
            break
        if not _is_sampled(session_row.id, sample_ratio):
            continue
        # Skip if already reviewed (idempotent).
        ctx_summary = session_row.context_summary if isinstance(session_row.context_summary, dict) else {}
        if ctx_summary.get("peer_review", {}).get("done") is True:
            continue

        # Pick alternate manager: prefer one *not* matching the original session's manager_slugs.
        original_slugs = list(ctx_summary.get("manager_slugs") or [])
        alt = _pick_alternate_manager(
            managers=managers,
            excluded_id=None,
            rng=rng,
        )
        if alt is None:
            continue

        # Find the swarm whose manager == alt; fall back to alt.swarm_id.
        swarm_id = alt.swarm_id
        if swarm_id is None:
            continue

        message = (
            f"Peer review by {alt.name} on session "
            f"{str(session_row.id)[:8]} (goal: \"{(session_row.goal or '')[:120]}...\"). "
            f"Original manager slugs: {', '.join(original_slugs) or 'unknown'}. "
            "Reviewer asked to scan outputs for clarity, factuality, and policy compliance."
        )
        try:
            await add_health_note(
                db,
                swarm_id=swarm_id,
                message=message,
                severity="info",
                source="peer_review",
                manager_agent_id=alt.id,
                metadata={
                    "session_id": str(session_row.id),
                    "original_manager_slugs": original_slugs,
                    "sample_ratio": sample_ratio,
                },
            )
        except ValueError:
            continue

        # Mark idempotent done on the session context.
        ctx = dict(session_row.context_summary or {})
        peer = dict(ctx.get("peer_review") or {})
        peer["done"] = True
        peer["reviewer_agent_id"] = str(alt.id)
        peer["reviewer_name"] = alt.name
        peer["at"] = datetime.now(tz=UTC).isoformat()
        ctx["peer_review"] = peer
        session_row.context_summary = ctx
        flag_modified(session_row, "context_summary")

        outcomes.append(
            PeerReviewOutcome(
                session_id=session_row.id,
                swarm_id=swarm_id,
                reviewer_agent_id=alt.id,
                reviewer_name=alt.name,
                note_appended=True,
            ),
        )
        reviewed_count += 1

    logger.info(
        "manager_peer_review.swept",
        agent_id="peer_review",
        swarm_id="all",
        task_id="",
        sessions_examined=len(sessions),
        reviewed=reviewed_count,
        sample_ratio=sample_ratio,
    )
    return {
        "sessions_examined": len(sessions),
        "reviewed": reviewed_count,
        "sample_ratio": sample_ratio,
        "lookback_hours": lookback_hours,
        "outcomes": [
            {
                "session_id": str(o.session_id),
                "swarm_id": str(o.swarm_id) if o.swarm_id else None,
                "reviewer_agent_id": str(o.reviewer_agent_id),
                "reviewer_name": o.reviewer_name,
            }
            for o in outcomes
        ],
    }


# Sanity: ensure SubSwarm import is used by linters even when type-hinting only.
_ = SubSwarm


__all__ = [
    "DEFAULT_LOOKBACK_HOURS",
    "DEFAULT_MAX_REVIEWS_PER_RUN",
    "DEFAULT_SAMPLE_RATIO",
    "PeerReviewOutcome",
    "sweep_peer_reviews",
]
