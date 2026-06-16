"""Track O TJ6 — 30/90-day journal pattern strip (win rate by tag · repeat-mistake alerts)."""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.journal_studio_entry_service import list_journal_trade_entries
from app.application.services.journal_studio_settings_service import get_journal_studio_settings
from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger(__name__)

EntryOutcome = Literal["win", "loss", "breakeven", "open", "unknown"]
PATTERN_WINDOWS: tuple[int, ...] = (30, 90)


class JournalTagWinRateOut(BaseModel):
    """Win rate rollup for one tag in a rolling window."""

    model_config = ConfigDict(extra="ignore")

    tag: str
    window_days: int
    entry_count: int = 0
    win_count: int = 0
    loss_count: int = 0
    breakeven_count: int = 0
    win_rate: float | None = None
    repeat_mistake_alert: bool = False


class JournalPatternWindowOut(BaseModel):
    """One rolling window (30d or 90d) of journal patterns."""

    model_config = ConfigDict(extra="ignore")

    window_days: int
    entry_count: int = 0
    resolved_count: int = 0
    overall_win_rate: float | None = None
    tag_stats: list[JournalTagWinRateOut] = Field(default_factory=list)
    edge_tags: list[str] = Field(default_factory=list)
    repeat_mistakes: list[str] = Field(default_factory=list)


class JournalPatternStripOut(BaseModel):
    """TJ6 full pattern strip for journal UI."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    windows: list[JournalPatternWindowOut] = Field(default_factory=list)
    repeat_mistake_alerts: list[str] = Field(default_factory=list)
    operator_hint: str = ""
    morning_brief_line: str = ""
    workspace_href: str = "/apps-tools/trading-journal?section=patterns#journal-studio-pattern-strip"


class JournalPatternStripKpiOut(BaseModel):
    """Compact TJ6 rollup for CBO snapshot and morning brief."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    window_30_win_rate: float | None = None
    window_90_win_rate: float | None = None
    repeat_mistake_count: int = 0
    repeat_mistakes: list[str] = Field(default_factory=list)
    edge_tags: list[str] = Field(default_factory=list)
    operator_hint: str = ""
    morning_brief_line: str = ""
    workspace_href: str = "/apps-tools/trading-journal?section=patterns#journal-studio-pattern-strip"


def _infer_tag(entry: Any, configured_tags: list[str]) -> str | None:
    if entry.mistake_tag:
        return str(entry.mistake_tag).lower()
    lowered = {str(t).lower() for t in entry.tags or []}
    for tag in configured_tags:
        if tag.lower() in lowered:
            return tag.lower()
    for tag in entry.tags or []:
        cleaned = str(tag).strip().lower()
        if cleaned and cleaned not in {"paper", "buy", "sell"}:
            return cleaned
    return None


def _compute_window_patterns(
    entries: list[Any],
    *,
    window_days: int,
    configured_tags: list[str],
) -> JournalPatternWindowOut:
    cutoff = datetime.now(tz=UTC) - timedelta(days=max(7, min(window_days, 120)))
    in_window = [row for row in entries if row.occurred_at >= cutoff]

    wins = 0
    losses = 0
    breakevens = 0
    tag_buckets: dict[str, list[Any]] = defaultdict(list)

    for entry in in_window:
        tag = _infer_tag(entry, configured_tags)
        if tag:
            tag_buckets[tag].append(entry)
        outcome = str(entry.outcome or "unknown")
        if outcome == "win":
            wins += 1
        elif outcome == "loss":
            losses += 1
        elif outcome == "breakeven":
            breakevens += 1

    resolved = wins + losses
    overall_win_rate = round(wins / resolved, 4) if resolved > 0 else None

    tag_stats: list[JournalTagWinRateOut] = []
    repeat_mistakes: list[str] = []
    for tag, rows in sorted(tag_buckets.items(), key=lambda item: len(item[1]), reverse=True)[:12]:
        tag_wins = sum(1 for row in rows if row.outcome == "win")
        tag_losses = sum(1 for row in rows if row.outcome == "loss")
        tag_breakeven = sum(1 for row in rows if row.outcome == "breakeven")
        tag_resolved = tag_wins + tag_losses
        win_rate = round(tag_wins / tag_resolved, 4) if tag_resolved > 0 else None
        repeat_alert = window_days <= 30 and len(rows) >= 2 and tag_losses >= 1
        if repeat_alert:
            repeat_mistakes.append(tag)
        tag_stats.append(
            JournalTagWinRateOut(
                tag=tag,
                window_days=window_days,
                entry_count=len(rows),
                win_count=tag_wins,
                loss_count=tag_losses,
                breakeven_count=tag_breakeven,
                win_rate=win_rate,
                repeat_mistake_alert=repeat_alert,
            ),
        )

    edge_counter: Counter[str] = Counter()
    for entry in in_window:
        if entry.outcome not in {"win", "breakeven"} and not (
            entry.pnl_usd is not None and float(entry.pnl_usd) > 0
        ):
            continue
        for tag in entry.tags or []:
            cleaned = str(tag).strip().lower()
            if cleaned and cleaned not in {"paper", "buy", "sell", "fomo", "revenge_trade"}:
                edge_counter[cleaned] += 1

    return JournalPatternWindowOut(
        window_days=window_days,
        entry_count=len(in_window),
        resolved_count=resolved,
        overall_win_rate=overall_win_rate,
        tag_stats=tag_stats,
        edge_tags=[tag for tag, _count in edge_counter.most_common(5)],
        repeat_mistakes=repeat_mistakes,
    )


def _compose_hints(
    *,
    windows: list[JournalPatternWindowOut],
) -> tuple[str, str, list[str]]:
    window_30 = next((row for row in windows if row.window_days == 30), None)
    alerts = list(window_30.repeat_mistakes if window_30 else [])
    alert_labels = [f"{tag} ({next((s.entry_count for s in window_30.tag_stats if s.tag == tag), 0)}×)" for tag in alerts[:3]] if window_30 else []

    if window_30 and window_30.overall_win_rate is not None:
        brief = f"Journal 30d win rate {window_30.overall_win_rate:.0%}"
        if alert_labels:
            brief += f" · repeat mistakes: {', '.join(alert_labels)}"
    elif window_30 and window_30.entry_count > 0:
        brief = f"Journal 30d — {window_30.entry_count} entries logged; tag outcomes still open."
    else:
        brief = "Journal pattern strip — log tagged entries to unlock win-rate insights."

    if alerts:
        hint = f"{len(alerts)} repeat mistake pattern(s) in 30d — review before next live session."
    elif window_30 and window_30.overall_win_rate is not None:
        hint = f"30d win rate {window_30.overall_win_rate:.0%} across resolved entries."
    else:
        hint = "Tag entries with mistake tags to populate 30/90-day pattern strip."

    return hint, brief, alerts


async def compose_journal_pattern_strip(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
) -> JournalPatternStripOut:
    """Build TJ6 pattern strip for journal UI."""

    now = datetime.now(tz=UTC)
    if not settings.journal_studio_enabled or not settings.journal_studio_pattern_strip_enabled:
        return JournalPatternStripOut(
            enabled=False,
            generated_at=now,
            operator_hint="Journal pattern strip disabled.",
        )

    studio = await get_journal_studio_settings(session, tenant_id=tenant_id)
    listing = await list_journal_trade_entries(session, tenant_id=tenant_id)
    windows = [
        _compute_window_patterns(
            listing.items,
            window_days=window,
            configured_tags=studio.mistake_tags,
        )
        for window in PATTERN_WINDOWS
    ]
    hint, brief, alerts = _compose_hints(windows=windows)

    return JournalPatternStripOut(
        enabled=True,
        generated_at=now,
        windows=windows,
        repeat_mistake_alerts=alerts,
        operator_hint=hint,
        morning_brief_line=brief,
    )


async def compose_journal_pattern_strip_kpi(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
) -> JournalPatternStripKpiOut:
    """Compact TJ6 KPI for CBO and morning brief."""

    strip = await compose_journal_pattern_strip(
        session,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
    )
    window_30 = next((row for row in strip.windows if row.window_days == 30), None)
    window_90 = next((row for row in strip.windows if row.window_days == 90), None)
    return JournalPatternStripKpiOut(
        enabled=strip.enabled,
        generated_at=strip.generated_at,
        window_30_win_rate=window_30.overall_win_rate if window_30 else None,
        window_90_win_rate=window_90.overall_win_rate if window_90 else None,
        repeat_mistake_count=len(strip.repeat_mistake_alerts),
        repeat_mistakes=strip.repeat_mistake_alerts[:5],
        edge_tags=(window_30.edge_tags if window_30 else [])[:3],
        operator_hint=strip.operator_hint,
        morning_brief_line=strip.morning_brief_line,
        workspace_href=strip.workspace_href,
    )


__all__ = [
    "JournalPatternStripKpiOut",
    "JournalPatternStripOut",
    "JournalPatternWindowOut",
    "JournalTagWinRateOut",
    "compose_journal_pattern_strip",
    "compose_journal_pattern_strip_kpi",
]
