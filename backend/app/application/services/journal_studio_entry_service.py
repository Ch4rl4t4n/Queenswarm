"""Track O TJ2 — Journal trade entry schema (manual + paper fill import)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.journal_studio_settings_service import (
    JOURNAL_STUDIO_SETTINGS_KEY,
    get_journal_studio_settings,
)
from app.application.services.trading_cockpit import ensure_primary_trading_project
from app.core.logging import get_logger
from app.infrastructure.persistence.models.paper_trading import PaperTradingFill
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

EntrySource = Literal["manual", "paper_fill"]
EntryOutcome = Literal["win", "loss", "breakeven", "open", "unknown"]


class JournalTradeEntryOut(BaseModel):
    """Validated trade journal entry row."""

    model_config = ConfigDict(extra="ignore")

    id: str
    source: EntrySource = "manual"
    fill_id: str | None = None
    thesis: str = ""
    setup: str = ""
    entry_price: float | None = None
    exit_price: float | None = None
    position_size: float | None = None
    outcome: EntryOutcome = "unknown"
    pnl_usd: float | None = None
    emotion: str = ""
    lesson: str = ""
    tags: list[str] = Field(default_factory=list)
    mistake_tag: str | None = None
    symbol: str | None = None
    side: str | None = None
    venue: str | None = None
    occurred_at: datetime
    created_at: datetime
    updated_at: datetime


class JournalTradeEntryListOut(BaseModel):
    """List envelope for journal entries."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True
    entry_count: int = 0
    enabled_fields: list[str] = Field(default_factory=list)
    items: list[JournalTradeEntryOut] = Field(default_factory=list)
    operator_hint: str = ""


class JournalTradeEntryCreateIn(BaseModel):
    """Create manual journal entry."""

    model_config = ConfigDict(extra="forbid")

    thesis: str = Field(default="", max_length=2000)
    setup: str = Field(default="", max_length=1000)
    entry_price: float | None = None
    exit_price: float | None = None
    position_size: float | None = None
    outcome: EntryOutcome = "unknown"
    pnl_usd: float | None = None
    emotion: str = Field(default="", max_length=200)
    lesson: str = Field(default="", max_length=2000)
    tags: list[str] = Field(default_factory=list, max_length=12)
    mistake_tag: str | None = Field(default=None, max_length=64)
    symbol: str | None = Field(default=None, max_length=32)
    side: str | None = Field(default=None, max_length=8)
    venue: str | None = Field(default=None, max_length=32)
    occurred_at: datetime | None = None

    @field_validator("tags")
    @classmethod
    def _normalize_tags(cls, value: list[str]) -> list[str]:
        cleaned = [str(tag).strip().lower()[:48] for tag in value if str(tag).strip()]
        return cleaned[:12]


class JournalTradeEntryPatchIn(BaseModel):
    """Patch existing journal entry."""

    model_config = ConfigDict(extra="forbid")

    thesis: str | None = Field(default=None, max_length=2000)
    setup: str | None = Field(default=None, max_length=1000)
    entry_price: float | None = None
    exit_price: float | None = None
    position_size: float | None = None
    outcome: EntryOutcome | None = None
    pnl_usd: float | None = None
    emotion: str | None = Field(default=None, max_length=200)
    lesson: str | None = Field(default=None, max_length=2000)
    tags: list[str] | None = Field(default=None, max_length=12)
    mistake_tag: str | None = Field(default=None, max_length=64)
    symbol: str | None = Field(default=None, max_length=32)
    side: str | None = Field(default=None, max_length=8)
    venue: str | None = Field(default=None, max_length=32)
    occurred_at: datetime | None = None

    @field_validator("tags")
    @classmethod
    def _normalize_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned = [str(tag).strip().lower()[:48] for tag in value if str(tag).strip()]
        return cleaned[:12]


class JournalTradeEntryImportIn(BaseModel):
    """Optional overrides when importing from paper fill."""

    model_config = ConfigDict(extra="forbid")

    thesis: str | None = Field(default=None, max_length=2000)
    lesson: str | None = Field(default=None, max_length=2000)
    outcome: EntryOutcome | None = None
    tags: list[str] = Field(default_factory=list, max_length=12)
    mistake_tag: str | None = Field(default=None, max_length=64)


def _entries_bucket(operator_settings: dict[str, Any] | None) -> list[dict[str, Any]]:
    root = dict(operator_settings or {})
    bucket = root.get(JOURNAL_STUDIO_SETTINGS_KEY)
    if not isinstance(bucket, dict):
        return []
    raw = bucket.get("manual_entries")
    if not isinstance(raw, list):
        return []
    return [dict(row) for row in raw if isinstance(row, dict)]


def _parse_entry(raw: dict[str, Any]) -> JournalTradeEntryOut | None:
    entry_id = str(raw.get("id") or "").strip()
    if not entry_id:
        return None
    occurred_raw = raw.get("occurred_at") or raw.get("created_at")
    occurred_at = datetime.now(tz=UTC)
    if isinstance(occurred_raw, str):
        try:
            occurred_at = datetime.fromisoformat(occurred_raw.replace("Z", "+00:00"))
        except ValueError:
            occurred_at = datetime.now(tz=UTC)
    created_raw = raw.get("created_at")
    created_at = occurred_at
    if isinstance(created_raw, str):
        try:
            created_at = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
        except ValueError:
            created_at = occurred_at
    updated_raw = raw.get("updated_at")
    updated_at = created_at
    if isinstance(updated_raw, str):
        try:
            updated_at = datetime.fromisoformat(updated_raw.replace("Z", "+00:00"))
        except ValueError:
            updated_at = created_at
    source_raw = str(raw.get("source") or "manual")
    source: EntrySource = "paper_fill" if source_raw == "paper_fill" else "manual"
    outcome_raw = str(raw.get("outcome") or "unknown")
    outcome: EntryOutcome = outcome_raw if outcome_raw in {"win", "loss", "breakeven", "open", "unknown"} else "unknown"
    tags_raw = raw.get("tags")
    tags = [str(t).strip() for t in tags_raw][:12] if isinstance(tags_raw, list) else []
    return JournalTradeEntryOut(
        id=entry_id,
        source=source,
        fill_id=str(raw["fill_id"]) if raw.get("fill_id") else None,
        thesis=str(raw.get("thesis") or raw.get("title") or "")[:2000],
        setup=str(raw.get("setup") or "")[:1000],
        entry_price=float(raw["entry_price"]) if raw.get("entry_price") is not None else None,
        exit_price=float(raw["exit_price"]) if raw.get("exit_price") is not None else None,
        position_size=float(raw["position_size"]) if raw.get("position_size") is not None else None,
        outcome=outcome,
        pnl_usd=float(raw["pnl_usd"]) if raw.get("pnl_usd") is not None else None,
        emotion=str(raw.get("emotion") or "")[:200],
        lesson=str(raw.get("lesson") or raw.get("detail") or "")[:2000],
        tags=tags,
        mistake_tag=str(raw["mistake_tag"]) if raw.get("mistake_tag") else None,
        symbol=str(raw["symbol"]) if raw.get("symbol") else None,
        side=str(raw["side"]) if raw.get("side") else None,
        venue=str(raw["venue"]) if raw.get("venue") else None,
        occurred_at=occurred_at,
        created_at=created_at,
        updated_at=updated_at,
    )


async def _persist_entries(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    entries: list[dict[str, Any]],
) -> None:
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        msg = f"Tenant {tenant_id} not found"
        raise ValueError(msg)
    root = dict(tenant.operator_settings or {})
    bucket = dict(root.get(JOURNAL_STUDIO_SETTINGS_KEY) or {})
    bucket["manual_entries"] = entries
    root[JOURNAL_STUDIO_SETTINGS_KEY] = bucket
    tenant.operator_settings = root
    await session.flush()


def _entry_to_storage(entry: JournalTradeEntryOut) -> dict[str, Any]:
    return {
        "id": entry.id,
        "source": entry.source,
        "fill_id": entry.fill_id,
        "thesis": entry.thesis,
        "title": entry.thesis[:200] or "Journal entry",
        "setup": entry.setup,
        "entry_price": entry.entry_price,
        "exit_price": entry.exit_price,
        "position_size": entry.position_size,
        "outcome": entry.outcome,
        "pnl_usd": entry.pnl_usd,
        "emotion": entry.emotion,
        "lesson": entry.lesson,
        "detail": entry.lesson,
        "tags": entry.tags,
        "mistake_tag": entry.mistake_tag,
        "symbol": entry.symbol,
        "side": entry.side,
        "venue": entry.venue,
        "occurred_at": entry.occurred_at.isoformat(),
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat(),
    }


def _create_from_input(body: JournalTradeEntryCreateIn) -> JournalTradeEntryOut:
    now = datetime.now(tz=UTC)
    occurred = body.occurred_at or now
    return JournalTradeEntryOut(
        id=str(uuid.uuid4()),
        source="manual",
        thesis=body.thesis.strip(),
        setup=body.setup.strip(),
        entry_price=body.entry_price,
        exit_price=body.exit_price,
        position_size=body.position_size,
        outcome=body.outcome,
        pnl_usd=body.pnl_usd,
        emotion=body.emotion.strip(),
        lesson=body.lesson.strip(),
        tags=list(body.tags),
        mistake_tag=body.mistake_tag.strip() if body.mistake_tag else None,
        symbol=body.symbol.strip().upper() if body.symbol else None,
        side=body.side.strip().lower() if body.side else None,
        venue=body.venue.strip() if body.venue else None,
        occurred_at=occurred,
        created_at=now,
        updated_at=now,
    )


async def list_journal_trade_entries(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
) -> JournalTradeEntryListOut:
    """Return tenant journal entries ordered newest first."""

    settings = await get_journal_studio_settings(session, tenant_id=tenant_id)
    tenant = await session.get(Tenant, tenant_id)
    raw_rows = _entries_bucket(tenant.operator_settings if tenant else None)
    items: list[JournalTradeEntryOut] = []
    for raw in raw_rows:
        parsed = _parse_entry(raw)
        if parsed is not None:
            items.append(parsed)
    items.sort(key=lambda row: row.occurred_at, reverse=True)
    enabled_fields = [key for key, on in settings.field_toggles.items() if on]
    hint = "No entries yet — create manual row or import from paper fill."
    if items:
        hint = f"{len(items)} journal entries — thesis, outcome, tags, and lesson tracked."
    return JournalTradeEntryListOut(
        enabled=True,
        entry_count=len(items),
        enabled_fields=enabled_fields,
        items=items,
        operator_hint=hint,
    )


async def create_journal_trade_entry(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    body: JournalTradeEntryCreateIn,
) -> JournalTradeEntryOut:
    """Create manual journal entry in tenant bucket."""

    tenant = await session.get(Tenant, tenant_id)
    rows = _entries_bucket(tenant.operator_settings if tenant else None)
    entry = _create_from_input(body)
    rows.append(_entry_to_storage(entry))
    await _persist_entries(session, tenant_id=tenant_id, entries=rows)
    _logger.info(
        "journal_entry.created",
        agent_id="journal_studio",
        swarm_id=str(tenant_id),
        entry_id=entry.id,
    )
    return entry


async def update_journal_trade_entry(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    entry_id: str,
    patch: JournalTradeEntryPatchIn,
) -> JournalTradeEntryOut:
    """Patch one journal entry by id."""

    tenant = await session.get(Tenant, tenant_id)
    rows = _entries_bucket(tenant.operator_settings if tenant else None)
    target_idx: int | None = None
    parsed: JournalTradeEntryOut | None = None
    for idx, raw in enumerate(rows):
        if str(raw.get("id")) == entry_id:
            target_idx = idx
            parsed = _parse_entry(raw)
            break
    if target_idx is None or parsed is None:
        msg = f"Journal entry {entry_id} not found"
        raise ValueError(msg)

    patch_data = patch.model_dump(exclude_unset=True)
    updated = parsed.model_copy(update=patch_data)
    updated = updated.model_copy(update={"updated_at": datetime.now(tz=UTC)})
    rows[target_idx] = _entry_to_storage(updated)
    await _persist_entries(session, tenant_id=tenant_id, entries=rows)
    _logger.info(
        "journal_entry.updated",
        agent_id="journal_studio",
        swarm_id=str(tenant_id),
        entry_id=entry_id,
    )
    return updated


async def import_journal_entry_from_fill(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    fill_id: uuid.UUID,
    overrides: JournalTradeEntryImportIn | None = None,
) -> JournalTradeEntryOut:
    """Import paper fill into journal entry schema."""

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        msg = f"Tenant {tenant_id} not found"
        raise ValueError(msg)

    rows = _entries_bucket(tenant.operator_settings)
    for raw in rows:
        if str(raw.get("fill_id")) == str(fill_id):
            msg = f"Fill {fill_id} already imported"
            raise ValueError(msg)

    lane = dict(tenant.operator_settings or {}).get("trading_lane")
    lane_dict = dict(lane) if isinstance(lane, dict) else {}
    project = await ensure_primary_trading_project(
        session,
        owner_id=dashboard_user_id,
        tenant=tenant,
        lane=lane_dict,
    )
    fill = await session.scalar(
        select(PaperTradingFill).where(
            PaperTradingFill.id == fill_id,
            PaperTradingFill.tenant_id == tenant_id,
            PaperTradingFill.project_id == project.id,
        ),
    )
    if fill is None:
        msg = f"Paper fill {fill_id} not found"
        raise ValueError(msg)

    override = overrides or JournalTradeEntryImportIn()
    now = datetime.now(tz=UTC)
    thesis = (override.thesis or fill.signal_note or f"{fill.side.upper()} {fill.symbol}").strip()
    entry = JournalTradeEntryOut(
        id=str(uuid.uuid4()),
        source="paper_fill",
        fill_id=str(fill.id),
        thesis=thesis[:2000],
        setup="",
        entry_price=float(fill.fill_price_usd),
        position_size=float(fill.quantity),
        outcome=override.outcome or "open",
        lesson=(override.lesson or "").strip(),
        tags=list(override.tags) or ["paper"],
        mistake_tag=override.mistake_tag,
        symbol=str(fill.symbol),
        side=str(fill.side).lower(),
        venue="paper",
        occurred_at=fill.created_at,
        created_at=now,
        updated_at=now,
    )
    rows.append(_entry_to_storage(entry))
    await _persist_entries(session, tenant_id=tenant_id, entries=rows)
    _logger.info(
        "journal_entry.imported_fill",
        agent_id="journal_studio",
        swarm_id=str(tenant_id),
        entry_id=entry.id,
        fill_id=str(fill_id),
    )
    return entry


__all__ = [
    "JournalTradeEntryCreateIn",
    "JournalTradeEntryImportIn",
    "JournalTradeEntryListOut",
    "JournalTradeEntryOut",
    "JournalTradeEntryPatchIn",
    "create_journal_trade_entry",
    "import_journal_entry_from_fill",
    "list_journal_trade_entries",
    "update_journal_trade_entry",
]
