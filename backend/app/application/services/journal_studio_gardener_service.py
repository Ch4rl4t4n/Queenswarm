"""Track O TJ3 — Overnight journal gardener (fills → draft lesson → HITL → wiki)."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.journal_studio_entry_service import (
    JournalTradeEntryImportIn,
    import_journal_entry_from_fill,
    update_journal_trade_entry,
)
from app.application.services.journal_studio_settings_service import (
    JOURNAL_STUDIO_SETTINGS_KEY,
    get_journal_studio_settings,
)
from app.application.services.trading_cockpit import ensure_primary_trading_project
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.paper_trading import PaperTradingFill
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

JournalDraftStatus = Literal["pending", "approved", "rejected", "published"]
JournalDraftDecision = Literal["approve", "reject"]
MAX_DRAFTS_STORED = 60
MAX_PENDING_DRAFTS = 25
CRITIC_PASS_THRESHOLD = 3.5


class JournalDraftOut(BaseModel):
    """Draft lesson awaiting operator approval."""

    model_config = ConfigDict(extra="ignore")

    id: str
    status: JournalDraftStatus = "pending"
    fill_id: str | None = None
    entry_id: str | None = None
    symbol: str | None = None
    side: str | None = None
    thesis: str = ""
    draft_lesson: str = ""
    markdown_preview: str = ""
    critic_score: float = 0.0
    critic_pass: bool = False
    tags: list[str] = Field(default_factory=list)
    mistake_tag: str | None = None
    created_at: datetime
    reviewed_at: datetime | None = None
    reviewed_by: str | None = None
    wiki_slug: str | None = None
    workspace_href: str = "/apps-tools/trading-journal?section=gardener#journal-studio-gardener"


class JournalGardenerSnapshotOut(BaseModel):
    """TJ3 gardener workspace snapshot."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    pending_count: int = 0
    published_count: int = 0
    rejected_count: int = 0
    last_run_at: datetime | None = None
    last_run_drafts_created: int = 0
    items: list[JournalDraftOut] = Field(default_factory=list)
    operator_hint: str = ""
    workspace_href: str = "/apps-tools/trading-journal?section=gardener#journal-studio-gardener"


class JournalDraftReviewIn(BaseModel):
    """Approve or reject a pending journal draft."""

    model_config = ConfigDict(extra="forbid")

    decision: JournalDraftDecision
    note: str = Field(default="", max_length=500)


class JournalDraftReviewOut(BaseModel):
    """Review action result."""

    model_config = ConfigDict(extra="ignore")

    id: str
    status: JournalDraftStatus
    wiki_slug: str | None = None
    reviewed_at: datetime


def _journal_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    bucket = root.get(JOURNAL_STUDIO_SETTINGS_KEY)
    return dict(bucket) if isinstance(bucket, dict) else {}


def _drafts_list(operator_settings: dict[str, Any] | None) -> list[dict[str, Any]]:
    bucket = _journal_bucket(operator_settings)
    raw = bucket.get("pending_drafts")
    if not isinstance(raw, list):
        return []
    return [dict(row) for row in raw if isinstance(row, dict)]


async def _persist_journal_bucket(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    mutator: Any,
) -> dict[str, Any]:
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        msg = f"Tenant {tenant_id} not found"
        raise ValueError(msg)
    root = dict(tenant.operator_settings or {})
    bucket = dict(root.get(JOURNAL_STUDIO_SETTINGS_KEY) or {})
    mutator(bucket)
    root[JOURNAL_STUDIO_SETTINGS_KEY] = bucket
    tenant.operator_settings = root
    await session.flush()
    return bucket


def _slugify(text: str) -> str:
    cleaned = re.sub(r"[^\w\-]+", "-", text.strip().lower()).strip("-")
    return cleaned[:64] or "journal-entry"


def _parse_draft(raw: dict[str, Any]) -> JournalDraftOut | None:
    draft_id = str(raw.get("id") or "").strip()
    if not draft_id:
        return None
    status_raw = str(raw.get("status") or "pending")
    status: JournalDraftStatus = status_raw if status_raw in {"pending", "approved", "rejected", "published"} else "pending"
    created_raw = raw.get("created_at")
    created_at = datetime.now(tz=UTC)
    if isinstance(created_raw, str):
        try:
            created_at = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        except ValueError:
            created_at = datetime.now(tz=UTC)
    reviewed_raw = raw.get("reviewed_at")
    reviewed_at: datetime | None = None
    if isinstance(reviewed_raw, str):
        try:
            reviewed_at = datetime.fromisoformat(reviewed_raw.replace("Z", "+00:00"))
        except ValueError:
            reviewed_at = None
    tags_raw = raw.get("tags")
    tags = [str(t).strip() for t in tags_raw][:12] if isinstance(tags_raw, list) else []
    return JournalDraftOut(
        id=draft_id,
        status=status,
        fill_id=str(raw["fill_id"]) if raw.get("fill_id") else None,
        entry_id=str(raw["entry_id"]) if raw.get("entry_id") else None,
        symbol=str(raw["symbol"]) if raw.get("symbol") else None,
        side=str(raw["side"]) if raw.get("side") else None,
        thesis=str(raw.get("thesis") or "")[:2000],
        draft_lesson=str(raw.get("draft_lesson") or "")[:2000],
        markdown_preview=str(raw.get("markdown_preview") or "")[:4000],
        critic_score=float(raw.get("critic_score") or 0.0),
        critic_pass=bool(raw.get("critic_pass")),
        tags=tags,
        mistake_tag=str(raw["mistake_tag"]) if raw.get("mistake_tag") else None,
        created_at=created_at,
        reviewed_at=reviewed_at,
        reviewed_by=str(raw["reviewed_by"]) if raw.get("reviewed_by") else None,
        wiki_slug=str(raw["wiki_slug"]) if raw.get("wiki_slug") else None,
    )


def _known_fill_ids(operator_settings: dict[str, Any] | None) -> set[str]:
    known: set[str] = set()
    bucket = _journal_bucket(operator_settings)
    for raw in _drafts_list(operator_settings):
        if raw.get("fill_id"):
            known.add(str(raw["fill_id"]))
    for raw in bucket.get("manual_entries") or []:
        if isinstance(raw, dict) and raw.get("fill_id"):
            known.add(str(raw["fill_id"]))
    return known


def score_journal_draft_critic(
    *,
    thesis: str,
    draft_lesson: str,
    symbol: str | None,
    tags: list[str],
) -> tuple[float, bool]:
    """Deterministic critic (SB1-style simulate-first, no LLM in tests)."""

    score = 2.0
    if len(thesis.strip()) >= 12:
        score += 0.8
    if len(draft_lesson.strip()) >= 40:
        score += 1.0
    if symbol:
        score += 0.5
    if tags:
        score += 0.7
    score = min(5.0, score)
    return score, score >= CRITIC_PASS_THRESHOLD


def build_draft_markdown_preview(
    *,
    thesis: str,
    draft_lesson: str,
    symbol: str | None,
    side: str | None,
    tags: list[str],
    obsidian_subfolder: str,
) -> str:
    """Obsidian-ready markdown preview for operator HITL."""

    tag_line = ", ".join(f"#{tag}" for tag in tags[:8]) if tags else ""
    return (
        f"# Journal draft — {symbol or 'trade'}\n\n"
        f"**Subfolder:** `{obsidian_subfolder}`\n"
        f"**Side:** {side or 'n/a'}\n"
        f"**Thesis:** {thesis.strip()}\n\n"
        f"## Draft lesson\n\n{draft_lesson.strip()}\n\n"
        f"{tag_line}\n\n"
        f"---\n"
        f"Operator approve before wiki sync.\n"
    )


def build_draft_from_fill(
    fill: PaperTradingFill,
    *,
    obsidian_subfolder: str,
    mistake_tags: list[str],
) -> dict[str, Any]:
    """Compose draft row from paper fill."""

    now = datetime.now(tz=UTC)
    side = str(fill.side or "").lower()
    symbol = str(fill.symbol or "")
    thesis = (fill.signal_note or f"{side.upper()} {symbol}").strip()[:2000]
    suggested_tag = mistake_tags[0] if mistake_tags else "review_needed"
    draft_lesson = (
        f"Paper {side.upper()} {symbol} @ ${float(fill.fill_price_usd):.2f}. "
        f"Signal: {fill.signal_note or 'n/a'}. "
        f"Review whether thesis held; tag repeat mistakes (e.g. {suggested_tag}). "
        f"Write one concrete rule for the next session."
    )
    tags = ["paper", side, symbol.lower()][:8]
    score, passed = score_journal_draft_critic(
        thesis=thesis,
        draft_lesson=draft_lesson,
        symbol=symbol,
        tags=tags,
    )
    markdown = build_draft_markdown_preview(
        thesis=thesis,
        draft_lesson=draft_lesson,
        symbol=symbol,
        side=side,
        tags=tags,
        obsidian_subfolder=obsidian_subfolder,
    )
    return {
        "id": str(uuid.uuid4()),
        "status": "pending",
        "fill_id": str(fill.id),
        "entry_id": None,
        "symbol": symbol,
        "side": side,
        "thesis": thesis,
        "draft_lesson": draft_lesson,
        "markdown_preview": markdown,
        "critic_score": score,
        "critic_pass": passed,
        "tags": tags,
        "mistake_tag": None,
        "created_at": now.isoformat(),
        "reviewed_at": None,
        "reviewed_by": None,
        "wiki_slug": None,
    }


async def run_journal_studio_gardener_sweep(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    window_hours: int = 24,
) -> dict[str, Any]:
    """Scan recent fills without lessons and queue draft rows for HITL."""

    if not settings.journal_studio_enabled or not settings.journal_studio_gardener_enabled:
        return {"enabled": False, "drafts_created": 0}

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        return {"enabled": False, "drafts_created": 0, "reason": "tenant_missing"}

    studio = await get_journal_studio_settings(session, tenant_id=tenant_id)
    if not studio.review_cron_enabled and not studio.enabled:
        return {"enabled": True, "drafts_created": 0, "reason": "studio_review_off"}

    known_fills = _known_fill_ids(tenant.operator_settings)
    drafts = _drafts_list(tenant.operator_settings)
    pending_count = sum(1 for row in drafts if str(row.get("status") or "pending") == "pending")
    if pending_count >= MAX_PENDING_DRAFTS:
        return {"enabled": True, "drafts_created": 0, "reason": "pending_cap"}

    since = datetime.now(tz=UTC) - timedelta(hours=max(1, min(window_hours, 168)))
    lane = dict(tenant.operator_settings or {}).get("trading_lane")
    lane_dict = dict(lane) if isinstance(lane, dict) else {}
    try:
        project = await ensure_primary_trading_project(
            session,
            owner_id=dashboard_user_id,
            tenant=tenant,
            lane=lane_dict,
        )
    except Exception as exc:  # noqa: BLE001
        _logger.warning(
            "journal_gardener.project_load_failed",
            agent_id="journal_gardener",
            swarm_id=str(tenant_id),
            error=str(exc)[:200],
        )
        return {"enabled": True, "drafts_created": 0, "reason": "no_project"}

    fill_rows = await session.scalars(
        select(PaperTradingFill)
        .where(
            PaperTradingFill.tenant_id == tenant_id,
            PaperTradingFill.project_id == project.id,
            PaperTradingFill.created_at >= since,
        )
        .order_by(desc(PaperTradingFill.created_at))
        .limit(20),
    )

    created = 0
    for fill in fill_rows:
        fill_key = str(fill.id)
        if fill_key in known_fills:
            continue
        draft_raw = build_draft_from_fill(
            fill,
            obsidian_subfolder=studio.obsidian_subfolder,
            mistake_tags=studio.mistake_tags,
        )
        drafts.insert(0, draft_raw)
        known_fills.add(fill_key)
        created += 1
        if pending_count + created >= MAX_PENDING_DRAFTS:
            break

    drafts = drafts[:MAX_DRAFTS_STORED]
    now = datetime.now(tz=UTC)

    def _mutator(bucket: dict[str, Any]) -> None:
        bucket["pending_drafts"] = drafts
        bucket["gardener_last_run_at"] = now.isoformat()
        bucket["gardener_last_run_drafts_created"] = created

    await _persist_journal_bucket(session, tenant_id=tenant_id, mutator=_mutator)
    _logger.info(
        "journal_gardener.sweep_complete",
        agent_id="journal_gardener",
        swarm_id=str(tenant_id),
        drafts_created=created,
    )
    return {"enabled": True, "drafts_created": created, "pending_total": pending_count + created}


async def compose_journal_gardener_snapshot(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> JournalGardenerSnapshotOut:
    """Return pending drafts and last gardener run metadata."""

    now = datetime.now(tz=UTC)
    if not settings.journal_studio_enabled or not settings.journal_studio_gardener_enabled:
        return JournalGardenerSnapshotOut(
            enabled=False,
            generated_at=now,
            operator_hint="Journal gardener disabled.",
        )

    tenant = await session.get(Tenant, tenant_id)
    bucket = _journal_bucket(tenant.operator_settings if tenant else None)
    items: list[JournalDraftOut] = []
    pending = published = rejected = 0
    for raw in _drafts_list(tenant.operator_settings if tenant else None):
        parsed = _parse_draft(raw)
        if parsed is None:
            continue
        items.append(parsed)
        if parsed.status == "pending":
            pending += 1
        elif parsed.status == "published":
            published += 1
        elif parsed.status == "rejected":
            rejected += 1
    items.sort(key=lambda row: row.created_at, reverse=True)

    last_run_raw = bucket.get("gardener_last_run_at")
    last_run_at: datetime | None = None
    if isinstance(last_run_raw, str):
        try:
            last_run_at = datetime.fromisoformat(last_run_raw.replace("Z", "+00:00"))
        except ValueError:
            last_run_at = None

    hint = "No pending drafts — overnight sweep creates lessons from paper fills."
    if pending:
        hint = f"{pending} draft lesson(s) await operator approve before wiki sync."

    return JournalGardenerSnapshotOut(
        enabled=True,
        generated_at=now,
        pending_count=pending,
        published_count=published,
        rejected_count=rejected,
        last_run_at=last_run_at,
        last_run_drafts_created=int(bucket.get("gardener_last_run_drafts_created") or 0),
        items=items[:30],
        operator_hint=hint,
    )


async def compose_journal_draft_inbox_items(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Pending journal drafts for unified Approval Inbox."""

    if not settings.journal_studio_enabled or not settings.journal_studio_gardener_enabled:
        return []
    snap = await compose_journal_gardener_snapshot(session, tenant_id=tenant_id)
    rows: list[dict[str, Any]] = []
    for item in snap.items:
        if item.status != "pending":
            continue
        rows.append(
            {
                "id": item.id,
                "title": f"Journal draft · {item.symbol or 'trade'}",
                "detail": item.draft_lesson[:320],
                "created_at": item.created_at,
                "critic_score": item.critic_score,
            },
        )
        if len(rows) >= limit:
            break
    return rows


async def review_journal_draft(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    draft_id: str,
    body: JournalDraftReviewIn,
    reviewed_by: str | None = None,
) -> JournalDraftReviewOut:
    """Approve (wiki + entry) or reject a pending journal draft."""

    if not settings.journal_studio_enabled or not settings.journal_studio_gardener_enabled:
        msg = "Journal gardener disabled"
        raise ValueError(msg)

    tenant = await session.get(Tenant, tenant_id)
    drafts = _drafts_list(tenant.operator_settings if tenant else None)
    target_idx: int | None = None
    parsed: JournalDraftOut | None = None
    for idx, raw in enumerate(drafts):
        if str(raw.get("id")) == draft_id:
            target_idx = idx
            parsed = _parse_draft(raw)
            break
    if target_idx is None or parsed is None:
        msg = f"Journal draft {draft_id} not found"
        raise ValueError(msg)
    if parsed.status != "pending":
        msg = f"Journal draft {draft_id} is not pending"
        raise ValueError(msg)

    now = datetime.now(tz=UTC)
    reviewer = reviewed_by or "operator"

    if body.decision == "reject":
        drafts[target_idx]["status"] = "rejected"
        drafts[target_idx]["reviewed_at"] = now.isoformat()
        drafts[target_idx]["reviewed_by"] = reviewer
        drafts[target_idx]["review_note"] = body.note[:500]

        def _reject(bucket: dict[str, Any]) -> None:
            bucket["pending_drafts"] = drafts

        await _persist_journal_bucket(session, tenant_id=tenant_id, mutator=_reject)
        return JournalDraftReviewOut(id=draft_id, status="rejected", reviewed_at=now)

    studio = await get_journal_studio_settings(session, tenant_id=tenant_id)
    wiki_slug: str | None = None
    entry_id = parsed.entry_id

    if parsed.fill_id and not entry_id:
        try:
            entry = await import_journal_entry_from_fill(
                session,
                tenant_id=tenant_id,
                dashboard_user_id=dashboard_user_id,
                fill_id=uuid.UUID(parsed.fill_id),
                overrides=JournalTradeEntryImportIn(
                    thesis=parsed.thesis,
                    lesson=parsed.draft_lesson,
                    tags=parsed.tags,
                    mistake_tag=parsed.mistake_tag,
                ),
            )
            entry_id = entry.id
        except ValueError:
            entry_id = entry_id or None

    if entry_id:
        from app.application.services.journal_studio_entry_service import JournalTradeEntryPatchIn

        await update_journal_trade_entry(
            session,
            tenant_id=tenant_id,
            entry_id=entry_id,
            patch=JournalTradeEntryPatchIn(
                lesson=parsed.draft_lesson,
                tags=parsed.tags,
                mistake_tag=parsed.mistake_tag,
            ),
        )

    if settings.wiki_layer_enabled:
        from app.application.services.wiki_layer_service import WikiLayerService

        wiki = WikiLayerService(db=session)
        slug_base = _slugify(f"journal-{parsed.symbol or 'trade'}-{draft_id[:8]}")
        wiki_slug = f"trading-journal-{slug_base}"
        title = f"Journal · {parsed.symbol or 'trade'} · {parsed.side or 'n/a'}"
        content_md = parsed.markdown_preview or build_draft_markdown_preview(
            thesis=parsed.thesis,
            draft_lesson=parsed.draft_lesson,
            symbol=parsed.symbol,
            side=parsed.side,
            tags=parsed.tags,
            obsidian_subfolder=studio.obsidian_subfolder,
        )
        await wiki.upsert_custom_page(
            tenant_id,
            slug=wiki_slug,
            title=title,
            content_md=content_md,
            source_refs=[{"type": "journal_gardener", "draft_id": draft_id, "fill_id": parsed.fill_id}],
        )

    drafts[target_idx]["status"] = "published"
    drafts[target_idx]["reviewed_at"] = now.isoformat()
    drafts[target_idx]["reviewed_by"] = reviewer
    drafts[target_idx]["review_note"] = body.note[:500]
    drafts[target_idx]["wiki_slug"] = wiki_slug
    drafts[target_idx]["entry_id"] = entry_id

    def _approve(bucket: dict[str, Any]) -> None:
        bucket["pending_drafts"] = drafts

    await _persist_journal_bucket(session, tenant_id=tenant_id, mutator=_approve)
    _logger.info(
        "journal_gardener.draft_approved",
        agent_id="journal_gardener",
        swarm_id=str(tenant_id),
        draft_id=draft_id,
        wiki_slug=wiki_slug,
    )
    return JournalDraftReviewOut(id=draft_id, status="published", wiki_slug=wiki_slug, reviewed_at=now)


__all__ = [
    "JournalDraftOut",
    "JournalDraftReviewIn",
    "JournalDraftReviewOut",
    "JournalGardenerSnapshotOut",
    "build_draft_from_fill",
    "compose_journal_draft_inbox_items",
    "compose_journal_gardener_snapshot",
    "review_journal_draft",
    "run_journal_studio_gardener_sweep",
    "score_journal_draft_critic",
]
