"""Project sub-swarm local_memory into operator-safe hive mind views."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from app.core.config import settings
from app.infrastructure.persistence.models.swarm import SubSwarm


def _sync_metrics(*, last_sync: datetime | None, now: datetime) -> dict[str, Any]:
    """Compute global sync cadence metrics for UI countdown rings."""

    interval = int(settings.hive_sync_interval_sec)
    if last_sync is None:
        return {
            "needs_sync": True,
            "last_sync_seconds_ago": None,
            "sync_due_in_sec": 0,
            "sync_progress_pct": 100,
        }

    ref = last_sync if last_sync.tzinfo is not None else last_sync.replace(tzinfo=UTC)
    elapsed = max(0, int((now - ref).total_seconds()))
    needs = elapsed >= interval
    due_in = 0 if needs else max(0, interval - elapsed)
    progress = min(100, int(round(elapsed / interval * 100))) if interval > 0 else 100
    return {
        "needs_sync": needs,
        "last_sync_seconds_ago": elapsed,
        "sync_due_in_sec": due_in,
        "sync_progress_pct": progress,
    }


def _extract_highlights(local_memory: dict[str, Any]) -> dict[str, Any]:
    """Surface curated local hive mind keys for dashboards."""

    lm = dict(local_memory or {})
    hive_ui = dict(lm.get("hive_ui") or {}) if isinstance(lm.get("hive_ui"), dict) else {}

    wizard_template = lm.get("wizard_template")
    wizard = str(wizard_template).strip() if wizard_template is not None else None
    if wizard == "":
        wizard = None

    last_waggle = lm.get("last_waggle") if isinstance(lm.get("last_waggle"), dict) else None
    waggle_cue: str | None = None
    if isinstance(last_waggle, dict):
        raw_cue = last_waggle.get("cue") or last_waggle.get("message")
        if isinstance(raw_cue, str) and raw_cue.strip():
            waggle_cue = raw_cue.strip()[:240]

    accent = hive_ui.get("accent_hex") or lm.get("accent_hex")
    accent_hex = str(accent).strip() if accent is not None else None
    if accent_hex == "":
        accent_hex = None

    role_label = hive_ui.get("swarm_role_label") or lm.get("swarm_role_label")
    role = str(role_label).strip() if role_label is not None else None
    if role == "":
        role = None

    goals = lm.get("goals")
    goal_preview: str | None = None
    if isinstance(goals, list) and goals:
        first = goals[0]
        if isinstance(first, str) and first.strip():
            goal_preview = first.strip()[:160]
    elif isinstance(goals, str) and goals.strip():
        goal_preview = goals.strip()[:160]

    peers = lm.get("peers")
    peer_count = len(peers) if isinstance(peers, list) else 0

    return {
        "wizard_template": wizard,
        "swarm_role_label": role,
        "accent_hex": accent_hex,
        "last_waggle_cue": waggle_cue,
        "goal_preview": goal_preview,
        "memory_key_count": len(lm),
        "peer_count": peer_count,
    }


def build_local_mind_summary(swarm: SubSwarm, *, now: datetime | None = None) -> dict[str, Any]:
    """Compact local hive mind projection for list cards."""

    stamp = now or datetime.now(tz=UTC)
    metrics = _sync_metrics(last_sync=swarm.last_global_sync_at, now=stamp)
    highlights = _extract_highlights(dict(swarm.local_memory or {}))
    return {
        "swarm_id": str(swarm.id),
        "hive_sync_interval_sec": int(settings.hive_sync_interval_sec),
        "recommended_bee_count": int(settings.sub_swarm_size),
        **metrics,
        **highlights,
    }


def build_local_mind_detail(swarm: SubSwarm, *, now: datetime | None = None) -> dict[str, Any]:
    """Detailed local hive mind view including safe memory preview."""

    summary = build_local_mind_summary(swarm, now=now)
    lm = dict(swarm.local_memory or {})
    safe_preview: dict[str, Any] = {}
    for key in ("wizard_template", "display_name", "subtitle", "goals", "peers", "hive_ui", "last_waggle"):
        if key in lm:
            safe_preview[key] = lm[key]

    summary["local_memory_preview"] = safe_preview
    summary["member_count"] = int(swarm.member_count or 0)
    summary["is_active"] = bool(swarm.is_active)
    summary["purpose"] = swarm.purpose.value
    summary["slug"] = swarm.name
    return summary


__all__ = ["build_local_mind_detail", "build_local_mind_summary"]
