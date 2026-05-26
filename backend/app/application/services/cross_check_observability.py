"""Observability for the Grok "truth arbiter" cross-check protocol.

The cross-check protocol (see `agent_prompt_templates._HIVEMIND_DUTY` and
`bootstrap_hive_policy.py` Instructions section) tells every agent to run
ONE Grok call (`xai/grok-3-mini`) before writing low-confidence claims
into HiveMind or surfacing them to the operator.

This service answers two operator questions:

1. **Are agents actually cross-checking?**
   - Proxy: count of `CostRecord` entries with `llm_model` matching the
     Grok primary slug in the window.

2. **What does Grok catch?**
   - Proxy: count of `SubSwarm.local_memory['health_notes']` entries whose
     `source` or `metadata.kind` mentions cross-check, plus a small sample
     of recent verdict=false fail messages.

No new tables — we read what already exists.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.session_cost_guardian import DEFAULT_SESSION_CAP_USD
from app.infrastructure.persistence.models.cost import CostRecord
from app.infrastructure.persistence.models.swarm import SubSwarm


_DEFAULT_WINDOW_HOURS = 168  # 7 days
_GROK_PRIMARY_SLUG = "xai/grok-3-mini"
_CROSS_CHECK_TOKENS = ("cross_check", "cross-check", "truth_arbiter", "truth-arbiter")


def _is_cross_check_note(entry: dict[str, Any]) -> bool:
    """Heuristic: does this health note look like a cross-check signal?"""

    bits: list[str] = []
    src = entry.get("source")
    if isinstance(src, str):
        bits.append(src.lower())
    meta = entry.get("metadata") or {}
    if isinstance(meta, dict):
        kind = meta.get("kind")
        if isinstance(kind, str):
            bits.append(kind.lower())
        if isinstance(meta.get("cross_check"), (str, bool, dict)):
            return True
    msg = (entry.get("message") or "").lower()
    bits.append(msg)
    joined = " ".join(bits)
    return any(tok in joined for tok in _CROSS_CHECK_TOKENS)


async def _grok_call_count(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    window_hours: int,
) -> dict[str, Any]:
    """Count primary-slug Grok calls within window as a proxy for cross-checks."""

    cutoff = datetime.now(tz=UTC) - timedelta(hours=window_hours)
    total = int(
        await db.scalar(
            select(func.count())
            .select_from(CostRecord)
            .where(
                CostRecord.tenant_id == tenant_id,
                CostRecord.created_at >= cutoff,
                CostRecord.llm_model == _GROK_PRIMARY_SLUG,
            )
        )
        or 0
    )
    cost = float(
        await db.scalar(
            select(func.coalesce(func.sum(CostRecord.cost_usd), 0.0))
            .where(
                CostRecord.tenant_id == tenant_id,
                CostRecord.created_at >= cutoff,
                CostRecord.llm_model == _GROK_PRIMARY_SLUG,
            )
        )
        or 0.0
    )
    return {
        "model": _GROK_PRIMARY_SLUG,
        "call_count": total,
        "spend_usd": round(cost, 4),
    }


async def _swarm_health_cross_check_signals(
    db: AsyncSession,
    *,
    window_hours: int,
) -> dict[str, Any]:
    """Walk every SubSwarm.local_memory['health_notes'] and pull cross-check entries."""

    cutoff = datetime.now(tz=UTC) - timedelta(hours=window_hours)
    swarms = list((await db.scalars(select(SubSwarm))).all())

    total = 0
    by_severity: dict[str, int] = {"info": 0, "warn": 0, "error": 0}
    samples: list[dict[str, Any]] = []

    for swarm in swarms:
        block = (swarm.local_memory or {}).get("health_notes") or {}
        items = block.get("items") or []
        for entry in items:
            if not _is_cross_check_note(entry):
                continue
            ts_raw = entry.get("at")
            try:
                ts = datetime.fromisoformat(str(ts_raw).replace("Z", "+00:00"))
            except (TypeError, ValueError):
                continue
            if ts < cutoff:
                continue
            total += 1
            sev = str(entry.get("severity") or "warn").lower()
            if sev in by_severity:
                by_severity[sev] += 1
            if len(samples) < 8:
                samples.append(
                    {
                        "swarm_name": swarm.name,
                        "at": ts.isoformat(),
                        "severity": sev,
                        "message": (entry.get("message") or "")[:240],
                    }
                )

    return {
        "total": total,
        "by_severity": by_severity,
        "samples": samples,
    }


def _operator_notes(grok: dict[str, Any], signals: dict[str, Any]) -> list[str]:
    """Short, headed advisories for the operator panel."""

    notes: list[str] = []
    calls = int(grok.get("call_count") or 0)
    verdict_signals = int(signals.get("total") or 0)

    if calls == 0:
        notes.append(
            "Zero Grok calls in window — either no swarm ran, or agents are "
            "skipping the cross-check (check curated memory `Instructions`)."
        )
    elif verdict_signals == 0 and calls > 0:
        notes.append(
            f"{calls} Grok calls landed, but no health notes mention cross-check. "
            "Likely all verdicts were `true` (good) — or agents are not emitting "
            "the warn note on `verdict=false` (worth spot-checking)."
        )
    if verdict_signals > 5:
        notes.append(
            f"{verdict_signals} cross-check warn notes in window — Grok is rejecting "
            "agent claims at unusual rate; review the sample below to find the "
            "noisy source (prompt issue or upstream data issue)."
        )
    return notes


async def build_cross_check_overview(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    window_hours: int | None = None,
) -> dict[str, Any]:
    """Build operator dashboard payload for cross-check observability."""

    window = max(1, min(int(window_hours or _DEFAULT_WINDOW_HOURS), 720))

    grok = await _grok_call_count(db, tenant_id=tenant_id, window_hours=window)
    signals = await _swarm_health_cross_check_signals(db, window_hours=window)

    headline = {
        "grok_calls_window": grok["call_count"],
        "grok_spend_usd": grok["spend_usd"],
        "verdict_false_signals_window": signals["total"],
        "session_cost_cap_usd": float(DEFAULT_SESSION_CAP_USD),
    }

    return {
        "window_hours": window,
        "as_of": datetime.now(tz=UTC).isoformat(),
        "headline": headline,
        "grok": grok,
        "signals": signals,
        "notes": _operator_notes(grok, signals),
    }


__all__ = ["build_cross_check_overview"]
