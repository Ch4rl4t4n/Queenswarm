"""SIG3 — Capabilities Atlas auto-highlight after external synthesis (social intel diff)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.social_intel_roadmap_refresh_service import (
    _has_social_intel_tag,
    _signal_title,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.knowledge import KnowledgeItem
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

SETTINGS_KEY = "capabilities_atlas_highlights"
HighlightKind = Literal["live", "planned"]


class CapabilityHighlightOut(BaseModel):
    """One atlas row to highlight from external synthesis."""

    model_config = ConfigDict(extra="forbid")

    capability_id: str
    kind: HighlightKind
    reason: str
    signal_title: str
    signal_id: str | None = None
    synthesized_at: datetime | None = None


class CapabilitiesAtlasHighlightsOut(BaseModel):
    """Operator snapshot for SIG3 atlas diff strip."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    window_days: int = 90
    signal_count: int = 0
    highlight_count: int = 0
    unseen_count: int = 0
    highlights: list[CapabilityHighlightOut] = Field(default_factory=list)
    operator_hint: str = ""
    settings_href: str = "/settings/capabilities"


class CapabilitiesAtlasHighlightAckIn(BaseModel):
    """Mark highlighted rows as reviewed."""

    model_config = ConfigDict(extra="forbid")

    highlight_keys: list[str] | None = None
    ack_all: bool = False


class CapabilitiesAtlasHighlightAckOut(BaseModel):
    """Ack result."""

    model_config = ConfigDict(extra="ignore")

    ok: bool = True
    acked_count: int = 0


class _SignalRule:
    """Keyword rule mapping external intel to atlas capability ids."""

    __slots__ = ("keywords", "live_ids", "planned_ids")

    def __init__(
        self,
        *,
        keywords: tuple[str, ...],
        live_ids: tuple[str, ...] = (),
        planned_ids: tuple[str, ...] = (),
    ) -> None:
        self.keywords = keywords
        self.live_ids = live_ids
        self.planned_ids = planned_ids


_SIGNAL_RULES: tuple[_SignalRule, ...] = (
    _SignalRule(
        keywords=("memory", "hermes", "memsearch", "recall", "hive mind", "gbrain"),
        live_ids=("hivemind", "learning-loop"),
        planned_ids=("behavioral-memory-editor", "episodic-memory-layer"),
    ),
    _SignalRule(
        keywords=("agent loop", "closed loop", "greptile", "rubric", "self-heal"),
        live_ids=("supervisor-sessions", "learning-loop", "simulations"),
        planned_ids=("closed-review-loop", "loop-guardrails-panel"),
    ),
    _SignalRule(
        keywords=("trading journal", "obsidian", "journal studio", "pre-trade"),
        live_ids=("trading-cockpit-live",),
        planned_ids=("trading-journal-studio",),
    ),
    _SignalRule(
        keywords=("analytics", "codex", "data science", "business question"),
        live_ids=("operator-control-plane-live",),
        planned_ids=("analytics-workspace", "business-analytics-report"),
    ),
    _SignalRule(
        keywords=("forager", "scrape", "goldmine", "public data", "monitor"),
        live_ids=("foragers-launch-live",),
        planned_ids=("forager-intelligence-v2", "forager-intelligence-loop", "data-monitor-wizard"),
    ),
    _SignalRule(
        keywords=("ollama", "local llm", "air gap", "fine-tune", "unsloth", "sovereign"),
        live_ids=("integrations-hub",),
        planned_ids=("local-inference-panel", "local-sovereign-routing"),
    ),
    _SignalRule(
        keywords=("sub-swarm", "hive mind sync", "local hive", "bee group"),
        live_ids=("sub-swarm-mind-live",),
        planned_ids=("sub-swarm-mind-ui",),
    ),
    _SignalRule(
        keywords=("recipe", "cosine", "imitation", "rapid loop"),
        live_ids=("recipes", "rapid-loop-widget", "recipe-cosine-match-live"),
        planned_ids=("recipe-cosine-match-ui",),
    ),
    _SignalRule(
        keywords=("publish", "content flywheel", "seo bulk", "hook"),
        live_ids=("publish-performance-live", "operator-loop-live"),
        planned_ids=("content-flywheel-v2", "ab-hook-optimizer"),
    ),
    _SignalRule(
        keywords=("mcp", "connector", "tool hub", "robinhood", "broker"),
        live_ids=("connectors", "integrations-hub", "trading-cockpit-live"),
        planned_ids=("robinhood-mcp-preset",),
    ),
    _SignalRule(
        keywords=("wiki", "second brain", "obsidian", "wikilink", "capture"),
        live_ids=("hivemind", "ballroom"),
        planned_ids=("wiki-layer-capture",),
    ),
    _SignalRule(
        keywords=("capabilities atlas", "roadmap", "competitive", "tech scv"),
        live_ids=("capabilities-atlas", "operator-control-plane-live"),
        planned_ids=("competitive-signal-pipeline",),
    ),
)


def _settings_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    bucket = root.get(SETTINGS_KEY)
    return dict(bucket) if isinstance(bucket, dict) else {}


def _highlight_key(*, kind: HighlightKind, capability_id: str) -> str:
    return f"{kind}:{capability_id}"


def _signal_blob(row: KnowledgeItem) -> str:
    parts = [
        _signal_title(row),
        str(row.content_text or "")[:2000],
        " ".join(str(tag) for tag in list(row.topic_tags or [])),
    ]
    return " ".join(parts).lower()


def match_signals_to_highlights(
    signals: list[KnowledgeItem],
) -> list[CapabilityHighlightOut]:
    """Map social intel rows to atlas capability highlight entries."""

    out: list[CapabilityHighlightOut] = []
    seen: set[str] = set()

    for row in signals:
        blob = _signal_blob(row)
        title = _signal_title(row)
        for rule in _SIGNAL_RULES:
            if not any(keyword in blob for keyword in rule.keywords):
                continue
            for cap_id in rule.live_ids:
                key = _highlight_key(kind="live", capability_id=cap_id)
                if key in seen:
                    continue
                seen.add(key)
                out.append(
                    CapabilityHighlightOut(
                        capability_id=cap_id,
                        kind="live",
                        reason=f"External signal matches «{rule.keywords[0]}» theme",
                        signal_title=title,
                        signal_id=str(row.id),
                        synthesized_at=row.scraped_at,
                    ),
                )
            for cap_id in rule.planned_ids:
                key = _highlight_key(kind="planned", capability_id=cap_id)
                if key in seen:
                    continue
                seen.add(key)
                out.append(
                    CapabilityHighlightOut(
                        capability_id=cap_id,
                        kind="planned",
                        reason=f"Roadmap gap flagged by «{rule.keywords[0]}» synthesis",
                        signal_title=title,
                        signal_id=str(row.id),
                        synthesized_at=row.scraped_at,
                    ),
                )
    out.sort(key=lambda item: item.synthesized_at or datetime.min.replace(tzinfo=UTC), reverse=True)
    return out[:24]


async def _load_synthesis_signals(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    window_days: int,
) -> list[KnowledgeItem]:
    """Load social intel knowledge rows for atlas diff."""

    from sqlalchemy import desc, select

    since = datetime.now(tz=UTC) - timedelta(days=max(30, min(window_days, 120)))
    rows = list(
        (
            await session.scalars(
                select(KnowledgeItem)
                .where(
                    KnowledgeItem.tenant_id == tenant_id,
                    KnowledgeItem.scraped_at >= since,
                )
                .order_by(desc(KnowledgeItem.scraped_at))
                .limit(80),
            )
        ).all(),
    )
    return [row for row in rows if _has_social_intel_tag(list(row.topic_tags or []))]


async def compose_capabilities_atlas_highlights(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    tenant: Tenant | None = None,
) -> CapabilitiesAtlasHighlightsOut:
    """SIG3 snapshot — which atlas rows changed per external synthesis."""

    now = datetime.now(tz=UTC)
    if not settings.capabilities_atlas_highlight_enabled:
        return CapabilitiesAtlasHighlightsOut(
            enabled=False,
            generated_at=now,
            operator_hint="Capabilities Atlas highlight diff disabled.",
        )

    window_days = int(settings.capabilities_atlas_highlight_window_days)
    signals = await _load_synthesis_signals(session, tenant_id=tenant_id, window_days=window_days)
    highlights = match_signals_to_highlights(signals)

    bucket = _settings_bucket(tenant.operator_settings if tenant else None)
    acked: set[str] = set(str(key) for key in list(bucket.get("acked_keys") or []))
    unseen = [row for row in highlights if _highlight_key(kind=row.kind, capability_id=row.capability_id) not in acked]

    if not signals:
        hint = "No social intel signals — run Foragers (YouTube/X) to populate synthesis diff."
    elif not highlights:
        hint = f"{len(signals)} signals ingested — no atlas row matches yet (expand keyword rules)."
    elif unseen:
        hint = f"🟡 {len(unseen)} atlas row(s) flagged from external synthesis — review highlighted cards."
    else:
        hint = "All synthesis highlights acknowledged — new signals will re-flag rows."

    return CapabilitiesAtlasHighlightsOut(
        enabled=True,
        generated_at=now,
        window_days=window_days,
        signal_count=len(signals),
        highlight_count=len(highlights),
        unseen_count=len(unseen),
        highlights=highlights,
        operator_hint=hint,
    )


async def acknowledge_capabilities_atlas_highlights(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    body: CapabilitiesAtlasHighlightAckIn,
) -> CapabilitiesAtlasHighlightAckOut:
    """Persist operator ack for highlighted atlas rows."""

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError("Tenant not found.")

    snapshot = await compose_capabilities_atlas_highlights(
        session,
        tenant_id=tenant_id,
        tenant=tenant,
    )
    keys_to_ack: set[str] = set()
    if body.ack_all:
        for row in snapshot.highlights:
            keys_to_ack.add(_highlight_key(kind=row.kind, capability_id=row.capability_id))
    elif body.highlight_keys:
        keys_to_ack.update(str(key).strip() for key in body.highlight_keys if str(key).strip())
    else:
        raise ValueError("Provide highlight_keys or ack_all=true.")

    root = dict(tenant.operator_settings or {})
    bucket = _settings_bucket(root)
    acked = set(str(key) for key in list(bucket.get("acked_keys") or []))
    acked.update(keys_to_ack)
    bucket["acked_keys"] = sorted(acked)
    bucket["last_ack_at"] = datetime.now(tz=UTC).isoformat()
    root[SETTINGS_KEY] = bucket
    tenant.operator_settings = root
    await session.flush()

    _logger.info(
        "capabilities_atlas.highlights_acked",
        agent_id="capabilities_atlas_highlight",
        swarm_id=str(tenant_id),
        acked_count=len(keys_to_ack),
    )
    return CapabilitiesAtlasHighlightAckOut(ok=True, acked_count=len(keys_to_ack))


__all__ = [
    "CapabilitiesAtlasHighlightAckIn",
    "CapabilitiesAtlasHighlightAckOut",
    "CapabilitiesAtlasHighlightsOut",
    "CapabilityHighlightOut",
    "acknowledge_capabilities_atlas_highlights",
    "compose_capabilities_atlas_highlights",
    "match_signals_to_highlights",
]
