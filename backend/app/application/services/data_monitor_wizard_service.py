"""DG1 — Data Monitor wizard: one-line intent → scheduled forager + extract schema."""

from __future__ import annotations

import re
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.forager_goldmine_dispatch_service import derive_forager_skill_bundle
from app.application.services.forager_service import ForagerService
from app.core.config import settings
from app.core.logging import get_logger

_logger = get_logger(__name__)

_URL_RE = re.compile(r"https?://[^\s<>\"')\],]+", re.IGNORECASE)
_X_HANDLE_RE = re.compile(r"(?:^|\s)@([A-Za-z0-9_]{1,15})(?:\s|$)")

MonitorNiche = Literal[
    "jobs",
    "prices",
    "listings",
    "news",
    "repos",
    "events",
    "social",
    "general",
]

SchedulePreset = Literal["6h", "12h", "24h", "daily_6utc"]


class DataMonitorExampleOut(BaseModel):
    """One example intent for operator inspiration."""

    model_config = ConfigDict(extra="ignore")

    intent: str
    niche: MonitorNiche
    label: str


class DataMonitorNicheOut(BaseModel):
    """Monitor niche metadata for UI chips."""

    model_config = ConfigDict(extra="ignore")

    id: MonitorNiche
    label: str
    description: str
    extract_schema: str


class DataMonitorWizardOut(BaseModel):
    """Wizard snapshot for Foragers page."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = True
    generated_at: datetime
    min_intent_chars: int = 12
    examples: list[DataMonitorExampleOut] = Field(default_factory=list)
    niches: list[DataMonitorNicheOut] = Field(default_factory=list)
    schedule_presets: list[str] = Field(default_factory=list)
    operator_hint: str = "One sentence → scheduled forager with extract schema and Celery routine."


class DataMonitorPlanOut(BaseModel):
    """Derived plan preview before commit."""

    model_config = ConfigDict(extra="ignore")

    niche: MonitorNiche
    niche_label: str
    source_type: str
    forager_name: str
    description: str
    extract_schema: str
    topic_tags: list[str] = Field(default_factory=list)
    skill_bundle: list[str] = Field(default_factory=list)
    schedule_label: str
    interval_seconds: int
    source_config_summary: str
    prompt_template: str


class DataMonitorSubmitIn(BaseModel):
    """Operator monitor intent."""

    model_config = ConfigDict(extra="forbid")

    intent: str = Field(min_length=12, max_length=2000)
    schedule_preset: SchedulePreset = Field(default="24h")
    trigger_first_run: bool = Field(default=True)


class DataMonitorSubmitOut(BaseModel):
    """Created forager acknowledgement."""

    model_config = ConfigDict(extra="ignore")

    ok: bool
    forager_id: str
    forager_name: str
    niche: MonitorNiche
    source_type: str
    extract_schema: str
    schedule_label: str
    skill_bundle: list[str] = Field(default_factory=list)
    routine_triggered: bool = False
    routine_session_id: str | None = None
    href: str = "/foragers"
    message: str = ""


_NICHE_META: dict[MonitorNiche, dict[str, Any]] = {
    "jobs": {
        "label": "Jobs & hiring",
        "description": "Job boards, career pages, hiring announcements.",
        "keywords": ("job", "jobs", "hiring", "career", "vacancy", "openings", "recruit"),
        "extract_schema": "jobs",
        "topic_tags": ["jobs", "monitor", "goldmine"],
        "source_type": "rss",
        "tools": ["rss", "web_search"],
        "prompt": "Extract employer, role title, location, compensation band, and apply URL when present.",
    },
    "prices": {
        "label": "Prices & pricing",
        "description": "Product pricing, competitor price pages, market quotes.",
        "keywords": ("price", "prices", "pricing", "cost", "quote", "tariff"),
        "extract_schema": "prices",
        "topic_tags": ["prices", "monitor", "goldmine"],
        "source_type": "rss",
        "tools": ["rss", "web_search", "scrape_url"],
        "prompt": "Extract product or SKU, price, currency, delta vs prior scrape, and source URL.",
    },
    "listings": {
        "label": "Listings",
        "description": "Real estate, classifieds, marketplace listings.",
        "keywords": ("listing", "listings", "apartment", "rent", "real estate", "classified"),
        "extract_schema": "listings",
        "topic_tags": ["listings", "monitor", "goldmine"],
        "source_type": "rss",
        "tools": ["rss", "web_search", "scrape_url"],
        "prompt": "Extract title, location, price, key attributes, and listing URL.",
    },
    "news": {
        "label": "News & headlines",
        "description": "Industry news, press, topic feeds.",
        "keywords": ("news", "headline", "press", "article", "media"),
        "extract_schema": "news",
        "topic_tags": ["news", "monitor", "goldmine"],
        "source_type": "rss",
        "tools": ["rss", "web_search"],
        "prompt": "Summarize headline, entities, sentiment, and why it matters for the monitor intent.",
    },
    "repos": {
        "label": "Repos & OSS",
        "description": "GitHub releases, stars, open-source activity.",
        "keywords": ("github", "repo", "repos", "repository", "open source", "release"),
        "extract_schema": "repos",
        "topic_tags": ["repos", "monitor", "goldmine"],
        "source_type": "rss",
        "tools": ["rss", "web_search"],
        "prompt": "Extract repo name, activity signal, version or release notes, and relevance to intent.",
    },
    "events": {
        "label": "Events",
        "description": "Conferences, launches, calendars.",
        "keywords": ("event", "events", "conference", "summit", "launch", "calendar"),
        "extract_schema": "events",
        "topic_tags": ["events", "monitor", "goldmine"],
        "source_type": "rss",
        "tools": ["rss", "web_search"],
        "prompt": "Extract event name, date, location, registration URL, and relevance.",
    },
    "social": {
        "label": "Social channels",
        "description": "YouTube or X/Twitter channel monitoring.",
        "keywords": ("youtube", "twitter", "channel", "influencer"),
        "extract_schema": "social_intel",
        "topic_tags": ["social", "monitor", "goldmine"],
        "source_type": "youtube",
        "tools": ["youtube", "web_search"],
        "prompt": "Summarize new posts with key claims — simulate-first before downstream spawn.",
    },
    "general": {
        "label": "General monitor",
        "description": "Catch-all public data monitor.",
        "keywords": (),
        "extract_schema": "general",
        "topic_tags": ["monitor", "goldmine"],
        "source_type": "rss",
        "tools": ["rss", "web_search"],
        "prompt": "Extract structured facts aligned to the operator intent — cite source URLs.",
    },
}

_EXAMPLES: tuple[DataMonitorExampleOut, ...] = (
    DataMonitorExampleOut(
        intent="Track senior Python remote jobs in EU on public job boards",
        niche="jobs",
        label="EU Python jobs",
    ),
    DataMonitorExampleOut(
        intent="Monitor competitor SaaS pricing pages for plan changes",
        niche="prices",
        label="Competitor pricing",
    ),
    DataMonitorExampleOut(
        intent="Watch Berlin apartment listings under €1500 on public RSS feeds",
        niche="listings",
        label="Berlin rentals",
    ),
    DataMonitorExampleOut(
        intent="Daily AI industry news headlines for product strategy",
        niche="news",
        label="AI news radar",
    ),
    DataMonitorExampleOut(
        intent="Track GitHub releases for LangGraph and Celery ecosystem repos",
        niche="repos",
        label="OSS releases",
    ),
)

_SCHEDULE_PRESETS: dict[SchedulePreset, tuple[int, str]] = {
    "6h": (21_600, "every 6h"),
    "12h": (43_200, "every 12h"),
    "24h": (86_400, "every 24h"),
    "daily_6utc": (86_400, "daily · 06:00 UTC cron"),
}


def _extract_urls(text: str) -> list[str]:
    """Return unique HTTP(S) URLs from free text."""

    seen: set[str] = set()
    urls: list[str] = []
    for match in _URL_RE.finditer(text):
        url = match.group(0).rstrip(".,;")
        key = url.lower()
        if key in seen:
            continue
        seen.add(key)
        urls.append(url)
    return urls


def _detect_source_type(intent: str, niche: MonitorNiche) -> str:
    """Infer forager source_type from intent keywords."""

    lower = intent.lower()
    if "youtube.com" in lower or "youtu.be" in lower or re.search(r"\byoutube\b", lower):
        return "youtube"
    if "twitter.com" in lower or "x.com" in lower or _X_HANDLE_RE.search(intent):
        return "twitter"
    if niche == "social":
        return "youtube"
    meta = _NICHE_META.get(niche, _NICHE_META["general"])
    return str(meta.get("source_type") or "rss")


def classify_monitor_niche(intent: str) -> MonitorNiche:
    """Score keyword hits to pick the best monitor niche."""

    lower = intent.lower()
    best: MonitorNiche = "general"
    best_score = 0
    for niche_id, meta in _NICHE_META.items():
        if niche_id == "general":
            continue
        score = sum(1 for kw in meta["keywords"] if kw in lower)
        if score > best_score:
            best_score = score
            best = niche_id
    if re.search(r"\byoutube\b", lower) or re.search(r"\btwitter\b", lower) or "@ " in lower:
        return "social"
    return best


def _build_source_config(intent: str, source_type: str) -> tuple[dict[str, Any], str]:
    """Build source_config and a short operator summary string."""

    urls = _extract_urls(intent)
    if source_type == "youtube":
        channels = [url for url in urls if "youtube.com" in url.lower() or "youtu.be" in url.lower()]
        cfg: dict[str, Any] = {
            "channels": channels,
            "backfill_limit": 30,
            "delta_limit": 15,
        }
        summary = f"YouTube channels: {len(channels)} bound" if channels else "Add YouTube channel URLs in Edit"
        return cfg, summary
    if source_type in {"twitter", "x"}:
        accounts: list[str] = []
        for handle in _X_HANDLE_RE.findall(intent):
            accounts.append(handle)
        for url in urls:
            if "twitter.com" in url.lower() or "x.com" in url.lower():
                accounts.append(url.rsplit("/", maxsplit=1)[-1])
        cfg = {
            "accounts": accounts,
            "backfill_limit": 30,
            "delta_limit": 20,
        }
        summary = f"X accounts: {len(accounts)} bound" if accounts else "Add @handles or profile URLs in Edit"
        return cfg, summary
    feeds = [url for url in urls if url.endswith(".xml") or "/feed" in url.lower() or "rss" in url.lower()]
    if not feeds and urls:
        feeds = urls[:3]
    cfg = {"feeds": feeds}
    summary = f"RSS feeds: {len(feeds)} bound" if feeds else "Add RSS feed URLs in Edit after create"
    return cfg, summary


def _schedule_from_preset(preset: SchedulePreset) -> tuple[dict[str, Any], str, int]:
    """Map UI preset to forager schedule payload."""

    interval_seconds, label = _SCHEDULE_PRESETS.get(preset, _SCHEDULE_PRESETS["24h"])
    if preset == "daily_6utc":
        schedule = {
            "enabled": True,
            "schedule_kind": "cron",
            "cron_expr": "0 6 * * *",
            "interval_seconds": interval_seconds,
            "runtime_mode": "durable",
        }
    else:
        schedule = {
            "enabled": True,
            "schedule_kind": "interval",
            "interval_seconds": interval_seconds,
            "cron_expr": None,
            "runtime_mode": "durable",
        }
    return schedule, label, interval_seconds


def _forager_name_from_intent(intent: str, niche: MonitorNiche) -> str:
    """Derive a short forager display name."""

    cleaned = re.sub(r"\s+", " ", intent.strip())
    niche_label = str(_NICHE_META[niche]["label"])
    snippet = cleaned[:48] + ("…" if len(cleaned) > 48 else "")
    return f"Monitor · {niche_label} · {snippet}"[:140]


def derive_data_monitor_plan(
    intent: str,
    *,
    schedule_preset: SchedulePreset = "24h",
) -> DataMonitorPlanOut:
    """Derive forager plan from operator intent without DB writes."""

    trimmed = intent.strip()
    niche = classify_monitor_niche(trimmed)
    meta = _NICHE_META[niche]
    source_type = _detect_source_type(trimmed, niche)
    source_config, source_summary = _build_source_config(trimmed, source_type)
    _, schedule_label, interval_seconds = _schedule_from_preset(schedule_preset)
    skill_bundle = derive_forager_skill_bundle(source_type)
    filter_config = {
        "monitor_niche": niche,
        "extract_schema": meta["extract_schema"],
        "default_tags": list(meta["topic_tags"]),
        "data_monitor_wizard": True,
        "intent": trimmed[:500],
    }
    if source_config:
        filter_config["source_config_hint"] = source_summary

    return DataMonitorPlanOut(
        niche=niche,
        niche_label=str(meta["label"]),
        source_type=source_type,
        forager_name=_forager_name_from_intent(trimmed, niche),
        description=trimmed,
        extract_schema=str(meta["extract_schema"]),
        topic_tags=list(meta["topic_tags"]),
        skill_bundle=skill_bundle,
        schedule_label=schedule_label,
        interval_seconds=interval_seconds,
        source_config_summary=source_summary,
        prompt_template=str(meta["prompt"]),
    )


def compose_data_monitor_wizard_snapshot() -> DataMonitorWizardOut:
    """Return static wizard metadata for UI."""

    if not settings.data_monitor_wizard_enabled:
        return DataMonitorWizardOut(
            enabled=False,
            generated_at=datetime.now(tz=UTC),
        )
    niches = [
        DataMonitorNicheOut(
            id=niche_id,
            label=str(meta["label"]),
            description=str(meta["description"]),
            extract_schema=str(meta["extract_schema"]),
        )
        for niche_id, meta in _NICHE_META.items()
    ]
    return DataMonitorWizardOut(
        enabled=True,
        generated_at=datetime.now(tz=UTC),
        examples=list(_EXAMPLES),
        niches=niches,
        schedule_presets=list(_SCHEDULE_PRESETS.keys()),
        operator_hint="Describe what to monitor in one sentence — we spawn a scheduled forager with schema.",
    )


async def submit_data_monitor_wizard(
    session: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    body: DataMonitorSubmitIn,
    created_by_subject: str | None,
) -> DataMonitorSubmitOut:
    """Create forager + Celery routine from one-line monitor intent."""

    if not settings.data_monitor_wizard_enabled:
        raise ValueError("data_monitor_wizard_disabled")

    plan = derive_data_monitor_plan(body.intent, schedule_preset=body.schedule_preset)
    meta = _NICHE_META[plan.niche]
    source_config, _ = _build_source_config(body.intent.strip(), plan.source_type)
    schedule, schedule_label, _ = _schedule_from_preset(body.schedule_preset)

    service = ForagerService(db=session)
    row = await service.create(
        tenant_id=tenant_id,
        name=plan.forager_name,
        description=plan.description,
        source_type=plan.source_type,
        source_config=source_config,
        filter_config={
            "monitor_niche": plan.niche,
            "extract_schema": plan.extract_schema,
            "default_tags": plan.topic_tags,
            "data_monitor_wizard": True,
            "intent": body.intent.strip()[:500],
            "skill_bundle_hint": plan.skill_bundle,
        },
        prompt_template=plan.prompt_template,
        tools=list(meta["tools"]),
        is_active=True,
        agent_template_id=None,
        schedule=schedule,
        created_by_subject=created_by_subject,
    )
    await session.flush()

    routine_triggered = False
    routine_session_id: str | None = None
    if body.trigger_first_run:
        trigger_out = await service.trigger_manual_run(
            tenant_id=tenant_id,
            forager_id=row.id,
            records=[],
        )
        routine_triggered = bool(trigger_out.get("routine_triggered"))
        raw_session = trigger_out.get("routine_session_id")
        routine_session_id = str(raw_session) if raw_session else None

    _logger.info(
        "data_monitor.wizard_submit",
        agent_id="forager_hub",
        swarm_id=str(tenant_id),
        forager_id=str(row.id),
        niche=plan.niche,
        source_type=plan.source_type,
    )
    return DataMonitorSubmitOut(
        ok=True,
        forager_id=str(row.id),
        forager_name=row.name,
        niche=plan.niche,
        source_type=plan.source_type,
        extract_schema=plan.extract_schema,
        schedule_label=schedule_label,
        skill_bundle=plan.skill_bundle,
        routine_triggered=routine_triggered,
        routine_session_id=routine_session_id,
        message=f"Data monitor created — {schedule_label}. Tune feeds in Forager Edit if needed.",
    )


__all__ = [
    "compose_data_monitor_wizard_snapshot",
    "classify_monitor_niche",
    "derive_data_monitor_plan",
    "submit_data_monitor_wizard",
    "DataMonitorSubmitIn",
    "DataMonitorSubmitOut",
    "DataMonitorWizardOut",
]
