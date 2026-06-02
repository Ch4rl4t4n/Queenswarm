"""Human-readable operator work digest — sessions, outcomes, and deep links."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.application.services.solo_operator_digest_inbox import _extract_excerpt
from app.application.services.solo_operator_four_lanes import (
    FOUR_LANE_IDS,
    FOUR_LANE_PAYLOAD_KEY,
    LANE_META,
    LANE_ROUTINE_NAMES,
    FourLaneId,
    _is_queen_maintainer_routine,
    _lane_from_payload,
    _load_tenant_routines,
)
from app.application.services.supervisor_session_control import is_session_auto_approve_blocked
from app.core.config import settings
from app.infrastructure.persistence.models.supervisor_session import SupervisorSession

WorkDigestBucket = Literal["done", "needs_you", "running", "failed", "other"]

_STATUS_BUCKET: dict[str, WorkDigestBucket] = {
    "completed": "done",
    "done": "done",
    "success": "done",
    "needs_input": "needs_you",
    "paused": "needs_you",
    "running": "running",
    "pending": "running",
    "queued": "running",
    "failed": "failed",
    "error": "failed",
}

_BUCKET_LABELS: dict[WorkDigestBucket, str] = {
    "done": "Done — view results",
    "needs_you": "Needs your action",
    "running": "In progress",
    "failed": "Failed",
    "other": "Other",
}

_BUCKET_LABELS_AUTO: dict[WorkDigestBucket, str] = {
    "done": "Done — view results",
    "needs_you": "Requires manual approval",
    "running": "Swarm working (auto-approve)",
    "failed": "Failed",
    "other": "Other",
}

_BUCKET_ORDER: tuple[WorkDigestBucket, ...] = ("needs_you", "done", "running", "failed", "other")

_MISSION_NOISE_RE = re.compile(r"^===\s*MISSION\s*===.*?(?=\n## |\n# |\Z)", re.DOTALL | re.IGNORECASE)


def _base_url() -> str:
    domain = str(settings.domain or "queenswarm.love").strip().rstrip("/")
    return domain if domain.startswith("http") else f"https://{domain}"


def short_session_id(session_id: uuid.UUID | str) -> str:
    """Compact session handle for operators (S-0A70)."""

    tail = str(session_id).replace("-", "")[-4:].upper()
    return f"S-{tail}"


def human_session_goal(session_row: SupervisorSession, *, max_len: int = 320) -> str:
    """Prefer raw operator goal over mission wrapper noise."""

    ctx = dict(session_row.context_summary or {})
    raw_goal = ctx.get("raw_goal")
    text = raw_goal.strip() if isinstance(raw_goal, str) and raw_goal.strip() else str(session_row.goal or "").strip()
    text = _MISSION_NOISE_RE.sub("", text).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)
    first_block = text.split("\n\n", 1)[0].strip()
    if first_block:
        text = first_block
    if len(text) > max_len:
        return f"{text[: max_len - 1]}…"
    return text or "Supervisor session"


def _routine_lane_map(routines: list[Any]) -> dict[str, FourLaneId]:
    out: dict[str, FourLaneId] = {}
    for row in routines:
        lane = _lane_from_payload(dict(row.context_payload or {}))
        if lane not in FOUR_LANE_IDS:
            continue
        if _is_queen_maintainer_routine(str(row.name)):
            continue
        out[str(row.id)] = lane
    return out


def resolve_lane_label(session_row: SupervisorSession, *, routine_lane: dict[str, FourLaneId]) -> str:
    """Map session to four-lane label or generic supervisor mission."""

    ctx = dict(session_row.context_summary or {})
    routine_id = str(ctx.get("routine_id") or "").strip()
    lane_id = routine_lane.get(routine_id)
    if lane_id is None:
        lane_raw = ctx.get(FOUR_LANE_PAYLOAD_KEY)
        if isinstance(lane_raw, str) and lane_raw.strip().lower() in FOUR_LANE_IDS:
            lane_id = lane_raw.strip().lower()  # type: ignore[assignment]
    if lane_id is None:
        goal_norm = human_session_goal(session_row, max_len=2000).lower()
        for fid in FOUR_LANE_IDS:
            hint = LANE_ROUTINE_NAMES[fid][:24].lower()
            if hint and hint in goal_norm:
                lane_id = fid
                break
    if lane_id is not None:
        return str(LANE_META[lane_id]["label"])
    if "najman" in human_session_goal(session_row, max_len=500).lower():
        return "Najman Marketing"
    created_by = getattr(session_row, "created_by_subject", None)
    if "seed_" in str(created_by or ""):
        return "Bootstrap"
    return "Supervisor mission"


def session_status_bucket(
    session_row: SupervisorSession,
    *,
    auto_approve_enabled: bool = False,
) -> WorkDigestBucket:
    """Map DB status to operator-facing digest bucket."""

    status = str(session_row.status or "").strip().lower()
    ctx = dict(session_row.context_summary or {})
    approval_state = str(ctx.get("approval_state") or "").strip().lower()
    already_approved = approval_state in {"approve", "approved"}

    if status in {"completed", "done", "success"}:
        return "done"
    if status in {"failed", "error"}:
        return "failed"

    if already_approved and status in {"needs_input", "paused", "running", "pending", "queued"}:
        return "running"

    if status in {"needs_input", "paused"}:
        blocked = is_session_auto_approve_blocked(goal=session_row.goal, context_summary=ctx)
        if auto_approve_enabled and not blocked:
            return "running"
        return "needs_you"

    if status in {"running", "pending", "queued"}:
        return "running"

    return _STATUS_BUCKET.get(status, "other")


def _bucket_labels(*, auto_approve_enabled: bool) -> dict[WorkDigestBucket, str]:
    return _BUCKET_LABELS_AUTO if auto_approve_enabled else _BUCKET_LABELS


def session_report_href(session_id: uuid.UUID | str) -> str:
    return f"{_base_url()}/agents?session={session_id}#sessions"


async def list_operator_work_sessions_since(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    since: datetime,
    limit: int = 40,
) -> list[SupervisorSession]:
    """Return supervisor sessions touched in the digest window."""

    safe_limit = max(1, min(int(limit), 100))
    stmt = (
        select(SupervisorSession)
        .where(
            SupervisorSession.tenant_id == tenant_id,
            or_(
                SupervisorSession.completed_at >= since,
                SupervisorSession.updated_at >= since,
                SupervisorSession.created_at >= since,
            ),
        )
        .options(selectinload(SupervisorSession.sub_agents))
        .order_by(desc(SupervisorSession.updated_at))
        .limit(safe_limit)
    )
    return list((await db.scalars(stmt)).all())


def _format_session_block(
    session_row: SupervisorSession,
    *,
    lane_label: str,
    bucket: WorkDigestBucket,
    labels: dict[WorkDigestBucket, str],
    plain_text: bool = False,
) -> list[str]:
    sid = short_session_id(session_row.id)
    goal = human_session_goal(session_row)
    excerpt = _plain_text_snippet(_extract_excerpt(session_row, max_len=360)) if plain_text else _strip_mission_noise(
        _extract_excerpt(session_row, max_len=360),
    )
    href = session_report_href(session_row.id)
    completed = session_row.completed_at.isoformat() if session_row.completed_at else "—"
    bucket_label = labels[bucket]

    if plain_text:
        lines = [
            f"{sid} · {lane_label} · {bucket_label}",
            f"Task: {goal}",
            f"Status: {session_row.status} · completed: {completed}",
        ]
        if session_row.task_id is not None:
            lines.append(f"Task ID: {session_row.task_id} (promoted to Tasks)")
        if excerpt.strip():
            lines.append(f"Result (preview): {excerpt}")
        elif bucket == "done":
            lines.append("Result: session completed — open report for sub-agent outputs.")
        lines.extend([f"Open report: {href}", ""])
        return lines

    lines = [
        f"### {sid} · {lane_label} · {bucket_label}",
        "",
        f"**Task:** {goal}",
        f"**Status:** `{session_row.status}` · completed: {completed}",
    ]
    if session_row.task_id is not None:
        lines.append(f"**Task ID:** `{session_row.task_id}` (promoted to Tasks)")
    if excerpt.strip():
        lines.append(f"**Result (preview):** {excerpt}")
    elif bucket == "done":
        lines.append("**Result:** session completed — open report for sub-agent outputs.")
    lines.extend(
        [
            f"**Open report (Info → PDF):** {href}",
            "",
        ],
    )
    return lines


def _strip_mission_noise(text: str) -> str:
    """Remove mission wrapper from digest excerpts."""

    cleaned = _MISSION_NOISE_RE.sub("", text).strip()
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    if cleaned.startswith("# Mission"):
        parts = cleaned.split("\n\n", 1)
        cleaned = parts[1].strip() if len(parts) > 1 else cleaned
    return cleaned


def _plain_text_snippet(text: str) -> str:
    """Strip markdown emphasis for plain email bodies."""

    snippet = _strip_mission_noise(text)
    snippet = re.sub(r"\*\*(.+?)\*\*", r"\1", snippet)
    snippet = re.sub(r"__(.+?)__", r"\1", snippet)
    snippet = re.sub(r"`([^`]+)`", r"\1", snippet)
    snippet = re.sub(r"^#+\s*", "", snippet, flags=re.MULTILINE)
    return snippet.strip()


def build_operator_work_digest_markdown(
    *,
    tenant_name: str,
    window_hours: int,
    sessions: list[SupervisorSession],
    routine_lane: dict[str, FourLaneId],
    generated_at: datetime,
    auto_approve_enabled: bool = False,
) -> str:
    """Render operator-friendly daily work summary (markdown attachment)."""

    labels = _bucket_labels(auto_approve_enabled=auto_approve_enabled)
    grouped: dict[WorkDigestBucket, list[SupervisorSession]] = {key: [] for key in _BUCKET_ORDER}
    for row in sessions:
        grouped[session_status_bucket(row, auto_approve_enabled=auto_approve_enabled)].append(row)

    done_count = len(grouped["done"])
    needs_count = len(grouped["needs_you"])
    running_count = len(grouped["running"])
    failed_count = len(grouped["failed"])
    needs_label = "Manual approval" if auto_approve_enabled else "Waiting on you"

    lines = [
        f"# Queenswarm · Daily work digest — {tenant_name}",
        "",
        f"Generated: {generated_at.astimezone(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Window: last {window_hours} hours",
        f"Approval mode: {'auto-approve' if auto_approve_enabled else 'manual'}",
        "",
        "## Summary",
        "",
        f"- **Done:** {done_count} · **{needs_label}:** {needs_count} · "
        f"**In progress:** {running_count} · **Failed:** {failed_count}",
        f"- **Open hive:** {_base_url()}/agents#sessions",
        f"- **Four Lanes inbox:** {_base_url()}/agentic-os#lanes",
        "",
    ]

    if not sessions:
        lines.extend(
            [
                "_No supervisor session reports in this window._",
                "",
                "Tip: check **Agents → Sessions** or run a lane digest from **Agentic OS → Lanes**.",
                "",
            ],
        )
        return "\n".join(lines)

    for bucket in _BUCKET_ORDER:
        rows = grouped[bucket]
        if not rows:
            continue
        lines.extend([f"## {labels[bucket]} ({len(rows)})", ""])
        for session_row in rows[:12]:
            lane_label = resolve_lane_label(session_row, routine_lane=routine_lane)
            lines.extend(
                _format_session_block(
                    session_row,
                    lane_label=lane_label,
                    bucket=bucket,
                    labels=labels,
                    plain_text=False,
                ),
            )
        if len(rows) > 12:
            lines.append(f"_… and {len(rows) - 12} more sessions._")
            lines.append("")

    lines.extend(
        [
            "---",
            "",
            "This is a **swarm work summary** (not a technical audit log). "
            "Admin audit actions are in Settings → Team.",
            "",
        ],
    )
    return "\n".join(lines)


def build_operator_work_digest_email_text(
    *,
    tenant_name: str,
    window_hours: int,
    sessions: list[SupervisorSession],
    routine_lane: dict[str, FourLaneId],
    generated_at: datetime,
    auto_approve_enabled: bool = False,
) -> str:
    """Plain-text email body — no markdown asterisks or backticks."""

    labels = _bucket_labels(auto_approve_enabled=auto_approve_enabled)
    grouped: dict[WorkDigestBucket, list[SupervisorSession]] = {key: [] for key in _BUCKET_ORDER}
    for row in sessions:
        grouped[session_status_bucket(row, auto_approve_enabled=auto_approve_enabled)].append(row)

    done_count = len(grouped["done"])
    needs_count = len(grouped["needs_you"])
    running_count = len(grouped["running"])
    failed_count = len(grouped["failed"])
    needs_label = "Manual approval" if auto_approve_enabled else "Waiting on you"

    lines = [
        f"Queenswarm · Daily work digest — {tenant_name}",
        "",
        f"Generated: {generated_at.astimezone(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Window: last {window_hours} hours",
        f"Approval mode: {'auto-approve enabled' if auto_approve_enabled else 'manual approval'}",
        "",
        "SUMMARY",
        f"Done: {done_count} · {needs_label}: {needs_count} · "
        f"In progress: {running_count} · Failed: {failed_count}",
        f"Open hive: {_base_url()}/agents#sessions",
        f"Four Lanes inbox: {_base_url()}/agentic-os#lanes",
        "",
    ]

    if not sessions:
        lines.extend(
            [
                "No supervisor session reports in this window.",
                "",
                "Tip: check Agents → Sessions or run a lane digest from Agentic OS → Lanes.",
                "",
            ],
        )
        return "\n".join(lines)

    for bucket in _BUCKET_ORDER:
        rows = grouped[bucket]
        if not rows:
            continue
        lines.extend([f"{labels[bucket].upper()} ({len(rows)})", ""])
        for session_row in rows[:12]:
            lane_label = resolve_lane_label(session_row, routine_lane=routine_lane)
            lines.extend(
                _format_session_block(
                    session_row,
                    lane_label=lane_label,
                    bucket=bucket,
                    labels=labels,
                    plain_text=True,
                ),
            )
        if len(rows) > 12:
            lines.append(f"… and {len(rows) - 12} more sessions.")
            lines.append("")

    lines.extend(
        [
            "—",
            "",
            "This is a swarm work summary (not a technical audit log).",
            "",
        ],
    )
    return "\n".join(lines)


def build_operator_work_digest_telegram_text(
    *,
    tenant_name: str,
    window_hours: int,
    sessions: list[SupervisorSession],
    routine_lane: dict[str, FourLaneId],
    auto_approve_enabled: bool = False,
) -> str:
    """Compact Telegram digest — priority: manual approval, then done."""

    needs = [
        s
        for s in sessions
        if session_status_bucket(s, auto_approve_enabled=auto_approve_enabled) == "needs_you"
    ]
    done = [
        s for s in sessions if session_status_bucket(s, auto_approve_enabled=auto_approve_enabled) == "done"
    ]
    running = [
        s
        for s in sessions
        if session_status_bucket(s, auto_approve_enabled=auto_approve_enabled) == "running"
    ]

    mode = "auto" if auto_approve_enabled else "manual"
    lines = [
        f"Queenswarm · Daily digest · {tenant_name}",
        f"Window {window_hours}h · done {len(done)} · manual {len(needs)} · running {len(running)} · {mode}",
        "",
    ]
    if not sessions:
        lines.append("No session reports in this window.")
        lines.append(f"{_base_url()}/agents#sessions")
        return "\n".join(lines)

    if needs:
        lines.append("Requires manual approval:")
        for row in needs[:5]:
            lane = resolve_lane_label(row, routine_lane=routine_lane)
            lines.append(f"• {short_session_id(row.id)} · {lane}")
            lines.append(f"  {human_session_goal(row, max_len=120)}")
            lines.append(f"  {session_report_href(row.id)}")
        lines.append("")

    if done:
        lines.append("Done — view results:")
        for row in done[:5]:
            lane = resolve_lane_label(row, routine_lane=routine_lane)
            excerpt = _strip_mission_noise(_extract_excerpt(row, max_len=100))
            lines.append(f"• {short_session_id(row.id)} · {lane}")
            if excerpt:
                lines.append(f"  {excerpt}")
            lines.append(f"  {session_report_href(row.id)}")
        lines.append("")

    if running and not needs:
        lines.append("Swarm working:")
        for row in running[:3]:
            lane = resolve_lane_label(row, routine_lane=routine_lane)
            lines.append(f"• {short_session_id(row.id)} · {lane}")
            lines.append(f"  {human_session_goal(row, max_len=100)}")
        lines.append("")

    lines.append(f"Full digest: {_base_url()}/agentic-os#lanes")
    return "\n".join(lines)


async def compose_operator_work_digest(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    tenant_name: str,
    window_hours: int,
    generated_at: datetime | None = None,
) -> dict[str, Any]:
    """Build markdown + telegram bodies for one tenant work digest."""

    when = generated_at or datetime.now(tz=UTC)
    since = when - timedelta(hours=window_hours)
    sessions = await list_operator_work_sessions_since(db, tenant_id=tenant_id, since=since)
    routines = await _load_tenant_routines(db, tenant_id=tenant_id)
    routine_lane = _routine_lane_map(routines)

    from app.application.services.supervisor_session_control import resolve_supervisor_sessions_auto_approve
    from app.infrastructure.persistence.models.tenant import Tenant

    tenant_row = await db.get(Tenant, tenant_id)
    auto_approve_enabled = resolve_supervisor_sessions_auto_approve(tenant_row)

    markdown = build_operator_work_digest_markdown(
        tenant_name=tenant_name,
        window_hours=window_hours,
        sessions=sessions,
        routine_lane=routine_lane,
        generated_at=when,
        auto_approve_enabled=auto_approve_enabled,
    )
    email_text = build_operator_work_digest_email_text(
        tenant_name=tenant_name,
        window_hours=window_hours,
        sessions=sessions,
        routine_lane=routine_lane,
        generated_at=when,
        auto_approve_enabled=auto_approve_enabled,
    )
    telegram = build_operator_work_digest_telegram_text(
        tenant_name=tenant_name,
        window_hours=window_hours,
        sessions=sessions,
        routine_lane=routine_lane,
        auto_approve_enabled=auto_approve_enabled,
    )
    return {
        "markdown": markdown,
        "email_text": email_text,
        "telegram": telegram,
        "session_count": len(sessions),
        "done_count": sum(
            1 for s in sessions if session_status_bucket(s, auto_approve_enabled=auto_approve_enabled) == "done"
        ),
        "needs_count": sum(
            1
            for s in sessions
            if session_status_bucket(s, auto_approve_enabled=auto_approve_enabled) == "needs_you"
        ),
        "running_count": sum(
            1 for s in sessions if session_status_bucket(s, auto_approve_enabled=auto_approve_enabled) == "running"
        ),
        "auto_approve_enabled": auto_approve_enabled,
    }


__all__ = [
    "build_operator_work_digest_email_text",
    "build_operator_work_digest_markdown",
    "build_operator_work_digest_telegram_text",
    "compose_operator_work_digest",
    "human_session_goal",
    "list_operator_work_sessions_since",
    "session_status_bucket",
    "short_session_id",
]
