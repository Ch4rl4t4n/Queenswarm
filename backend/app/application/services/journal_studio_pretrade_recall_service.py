"""Track O TJ5 — Pre-trade recall (top mistakes + thesis + wiki edges before session)."""

from __future__ import annotations

import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.journal_studio_entry_service import list_journal_trade_entries
from app.application.services.journal_studio_settings_service import get_journal_studio_settings
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)


class PreTradeMistakeOut(BaseModel):
    """One ranked mistake tag with recall lesson."""

    model_config = ConfigDict(extra="ignore")

    tag: str
    count: int
    latest_lesson: str = ""
    last_seen_at: datetime | None = None


class PreTradeRecallOut(BaseModel):
    """TJ5 snapshot — inject before next trading session."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    window_days: int = 30
    mistake_count: int = 0
    top_mistakes: list[PreTradeMistakeOut] = Field(default_factory=list)
    edge_reminders: list[str] = Field(default_factory=list)
    thesis_title: str | None = None
    thesis_snippet: str = ""
    wiki_snippets: list[str] = Field(default_factory=list)
    injection_block: str = ""
    operator_hint: str = ""
    thesis_wizard_href: str = "/solo-operator/trading-thesis"
    journal_href: str = "/apps-tools/trading-journal?section=recall#journal-studio-pretrade-recall"
    cockpit_href: str = "/apps-tools/trading-automation?section=cockpit#trading-cockpit"


def _infer_mistake_tag(tags: list[str], configured: list[str]) -> str | None:
    lowered = {t.lower() for t in tags}
    for tag in configured:
        if tag.lower() in lowered:
            return tag
    for tag in tags:
        if tag in {"fomo", "revenge_trade", "no_stop", "oversized", "early_exit", "late_entry"}:
            return tag
    return tags[0] if tags else None


def _rank_mistakes(
    entries: list[Any],
    *,
    window_days: int,
    configured_tags: list[str],
) -> list[PreTradeMistakeOut]:
    """Rank mistake tags from journal entries in rolling window."""

    cutoff = datetime.now(tz=UTC) - timedelta(days=max(7, min(window_days, 90)))
    bucket: dict[str, list[Any]] = {}
    for entry in entries:
        if entry.occurred_at < cutoff:
            continue
        tag = entry.mistake_tag or _infer_mistake_tag(entry.tags, configured_tags)
        if not tag:
            continue
        bucket.setdefault(str(tag).lower(), []).append(entry)

    ranked: list[PreTradeMistakeOut] = []
    for tag, rows in sorted(bucket.items(), key=lambda item: len(item[1]), reverse=True)[:5]:
        rows_sorted = sorted(rows, key=lambda row: row.occurred_at, reverse=True)
        latest = rows_sorted[0]
        ranked.append(
            PreTradeMistakeOut(
                tag=tag,
                count=len(rows),
                latest_lesson=(latest.lesson or latest.thesis or "")[:500],
                last_seen_at=latest.occurred_at,
            ),
        )
    return ranked


def _edge_reminders(entries: list[Any], *, window_days: int) -> list[str]:
    """Positive tag patterns that appeared in winning or tagged entries."""

    cutoff = datetime.now(tz=UTC) - timedelta(days=max(7, min(window_days, 90)))
    tag_counter: Counter[str] = Counter()
    for entry in entries:
        if entry.occurred_at < cutoff:
            continue
        if entry.outcome in {"win", "breakeven"} or entry.source == "paper_fill":
            for tag in entry.tags[:6]:
                cleaned = str(tag).strip().lower()
                if cleaned and cleaned not in {"paper", "buy", "sell"}:
                    tag_counter[cleaned] += 1
    return [f"Edge tag «{tag}» appeared {count}× in last {window_days}d" for tag, count in tag_counter.most_common(3)]


async def _latest_thesis_snippet(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
) -> tuple[str | None, str]:
    """Load latest NP5 trading thesis brief excerpt."""

    if not settings.trading_thesis_wizard_enabled:
        return None, ""

    rows = await session.scalars(
        select(TaskFinalDeliverable)
        .where(TaskFinalDeliverable.dashboard_user_id == dashboard_user_id)
        .order_by(desc(TaskFinalDeliverable.created_at))
        .limit(24),
    )
    for row in rows:
        tags = list(row.tags or [])
        structured = dict(row.structured_json or {})
        if "trading_thesis" not in tags and structured.get("format") != "queenswarm.trading_thesis.v1":
            continue
        body = (row.markdown_body or "").strip()
        snippet = body[:1200] + ("…" if len(body) > 1200 else "")
        return str(row.title or "Trading thesis"), snippet
    return None, ""


async def _wiki_journal_snippets(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    limit: int = 2,
) -> list[str]:
    """Pull recent approved journal wiki pages from hot tier."""

    if not settings.wiki_layer_enabled:
        return []

    from app.application.services.wiki_layer_service import WikiLayerService

    wiki = WikiLayerService(db=session)
    pages = await wiki.list_wiki_pages(tenant_id)
    snippets: list[str] = []
    for page in sorted(pages, key=lambda row: row.updated_at or row.created_at, reverse=True):
        if not str(page.slug).startswith("trading-journal-"):
            continue
        preview = (page.content_md or "").strip().replace("\n", " ")[:240]
        if preview:
            snippets.append(f"{page.title}: {preview}")
        if len(snippets) >= limit:
            break
    return snippets


def render_pretrade_injection_block(
    *,
    top_mistakes: list[PreTradeMistakeOut],
    edge_reminders: list[str],
    thesis_title: str | None,
    thesis_snippet: str,
    wiki_snippets: list[str],
    window_days: int,
) -> str:
    """Hermes-style block injected before trading Queen sessions."""

    lines = ["=== PRE-TRADE RECALL (TJ5) ===", f"Window: last {window_days} days"]
    if top_mistakes:
        lines.append("Top mistakes — slow down if these apply:")
        for row in top_mistakes[:3]:
            lesson = row.latest_lesson or "Review journal for concrete rule."
            lines.append(f"- {row.tag} ({row.count}×): {lesson[:220]}")
    else:
        lines.append("No ranked mistakes yet — log lessons in Trading Journal after fills.")

    if edge_reminders:
        lines.append("Edge reminders:")
        lines.extend(f"- {item}" for item in edge_reminders[:3])

    if thesis_title and thesis_snippet:
        lines.append(f"Thesis brief (NP5) — {thesis_title}:")
        lines.append(thesis_snippet[:800])

    if wiki_snippets:
        lines.append("Wiki recall:")
        lines.extend(f"- {snippet[:200]}" for snippet in wiki_snippets[:2])

    lines.append("=== END PRE-TRADE RECALL ===")
    return "\n".join(lines)


async def compose_pretrade_recall(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    window_days: int = 30,
) -> PreTradeRecallOut:
    """Build TJ5 recall snapshot for cockpit and journal UI."""

    now = datetime.now(tz=UTC)
    if not settings.journal_studio_enabled or not settings.journal_studio_pretrade_recall_enabled:
        return PreTradeRecallOut(
            enabled=False,
            generated_at=now,
            operator_hint="Pre-trade recall disabled.",
        )

    studio = await get_journal_studio_settings(session, tenant_id=tenant_id)
    listing = await list_journal_trade_entries(session, tenant_id=tenant_id)
    window = max(7, min(window_days, 90))
    mistakes = _rank_mistakes(
        listing.items,
        window_days=window,
        configured_tags=studio.mistake_tags,
    )
    edges = _edge_reminders(listing.items, window_days=window)
    thesis_title, thesis_snippet = await _latest_thesis_snippet(session, dashboard_user_id=dashboard_user_id)
    wiki_snippets = await _wiki_journal_snippets(session, tenant_id=tenant_id)
    injection = render_pretrade_injection_block(
        top_mistakes=mistakes,
        edge_reminders=edges,
        thesis_title=thesis_title,
        thesis_snippet=thesis_snippet,
        wiki_snippets=wiki_snippets,
        window_days=window,
    )

    if mistakes:
        hint = f"{len(mistakes)} mistake pattern(s) ranked — review before live or paper session."
    elif thesis_snippet:
        hint = "Thesis brief loaded — confirm kill criteria before next order."
    else:
        hint = "Seed journal entries or NP5 thesis brief to activate recall."

    return PreTradeRecallOut(
        enabled=True,
        generated_at=now,
        window_days=window,
        mistake_count=len(mistakes),
        top_mistakes=mistakes,
        edge_reminders=edges,
        thesis_title=thesis_title,
        thesis_snippet=thesis_snippet[:1200],
        wiki_snippets=wiki_snippets,
        injection_block=injection,
        operator_hint=hint,
    )


def should_inject_pretrade_recall(
    *,
    context_seed: dict[str, object] | None,
    goal: str,
) -> bool:
    """Return True when trading lane session should receive TJ5 block."""

    if not settings.journal_studio_enabled or not settings.journal_studio_pretrade_recall_enabled:
        return False

    seed = dict(context_seed or {})
    lane = str(seed.get("lane") or "").lower()
    if lane in {"trading", "trading_lane", "journal_studio_review"}:
        return True
    profile = str(seed.get("harness_profile_id") or seed.get("harness_profile") or "").lower()
    if profile == "trading":
        return True
    if bool(seed.get("trading_harness")):
        return True
    goal_lower = goal.lower()
    return any(token in goal_lower for token in ("polymarket", "trading cockpit", "live trade", "paper fill"))


async def load_trading_pretrade_recall_injection(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    context_seed: dict[str, object] | None,
    goal: str,
) -> str:
    """Load TJ5 injection block for supervisor session bootstrap."""

    if not should_inject_pretrade_recall(context_seed=context_seed, goal=goal):
        return ""

    recall = await compose_pretrade_recall(
        session,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
    )
    block = recall.injection_block.strip()
    if block:
        _logger.debug(
            "pretrade_recall.injected",
            agent_id="journal_studio",
            swarm_id=str(tenant_id),
            mistakes=len(recall.top_mistakes),
        )
    return block


__all__ = [
    "PreTradeMistakeOut",
    "PreTradeRecallOut",
    "compose_pretrade_recall",
    "load_trading_pretrade_recall_injection",
    "render_pretrade_injection_block",
    "should_inject_pretrade_recall",
]
