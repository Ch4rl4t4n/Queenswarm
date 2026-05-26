"""Lead magnet copy generation — swarm output → shareable acquisition artifacts."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.dashboard_time_saved import build_time_saved_payload
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

TemplateId = Literal["exec-assistant", "lead-waterfall", "content-flywheel"]


@dataclass(frozen=True, slots=True)
class LeadMagnetDefinition:
    """Static lead magnet metadata aligned with swarm wizard templates."""

    template_id: TemplateId
    name: str
    tagline: str
    description: str
    estimated_minutes: int
    time_saved_hours_per_week: int
    accent_hex: str
    agent_count: int
    headline_sk: str
    bullets_sk: tuple[str, ...]


_LEAD_MAGNETS: tuple[LeadMagnetDefinition, ...] = (
    LeadMagnetDefinition(
        template_id="exec-assistant",
        name="Exec Assistant",
        tagline="Personal chief-of-staff swarm in ~10 minutes",
        description="Briefing, inbox triage, and calendar prep bees plus a morning supervisor routine.",
        estimated_minutes=10,
        time_saved_hours_per_week=8,
        accent_hex="#FFB800",
        agent_count=3,
        headline_sk="Postav si Exec Assistant za 10 min",
        bullets_sk=(
            "3 špecializované včely — briefing, inbox, calendar prep",
            "Verified morning routine — žiadny raw LLM výstup",
            "Ušetrí ~8 h/týždeň na exec admin práci",
        ),
    ),
    LeadMagnetDefinition(
        template_id="lead-waterfall",
        name="Lead Waterfall",
        tagline="Scrape → qualify → outreach pre agentúry a SMB sales",
        description="Pipeline manager, lead scout, and outreach draft bees plus daily waterfall review.",
        estimated_minutes=12,
        time_saved_hours_per_week=12,
        accent_hex="#00FFFF",
        agent_count=3,
        headline_sk="Lead Waterfall swarm za 12 min — pipeline na autopilote",
        bullets_sk=(
            "Lead scout + ICP scoring + outreach draft v jednom colony",
            "Simulation gate pred každým odoslaním",
            "Typicky ~12 h/týždeň menej manuálneho sales grindu",
        ),
    ),
    LeadMagnetDefinition(
        template_id="content-flywheel",
        name="Content Flywheel",
        tagline="Research → draft → social so simulation gate",
        description="Editor manager, topic research, and draft bees plus recurring flywheel routine.",
        estimated_minutes=12,
        time_saved_hours_per_week=10,
        accent_hex="#FF00AA",
        agent_count=3,
        headline_sk="Content Flywheel — verified obsah za 12 min setup",
        bullets_sk=(
            "Topic research → long-form → social snippets v jednom hive",
            "Každý draft prejde simulate → reward → recipe loop",
            "~10 h/týždeň ušetrené na content ops",
        ),
    ),
)

_MAGNET_BY_ID: dict[str, LeadMagnetDefinition] = {m.template_id: m for m in _LEAD_MAGNETS}


def ugc_content_engine_enabled() -> bool:
    """Return whether lead magnet generation is active."""

    return bool(settings.ugc_content_engine_enabled)


def _app_base() -> str:
    domain = (settings.domain or "queenswarm.love").strip()
    return f"https://{domain}"


def list_lead_magnets() -> list[dict[str, Any]]:
    """Catalog rows for marketing UI."""

    base = _app_base()
    rows: list[dict[str, Any]] = []
    for magnet in _LEAD_MAGNETS:
        rows.append(
            {
                "template_id": magnet.template_id,
                "name": magnet.name,
                "tagline": magnet.tagline,
                "description": magnet.description,
                "estimated_minutes": magnet.estimated_minutes,
                "time_saved_hours_per_week": magnet.time_saved_hours_per_week,
                "accent_hex": magnet.accent_hex,
                "agent_count": magnet.agent_count,
                "headline": magnet.headline_sk,
                "landing_url": f"{base}/magnet/{magnet.template_id}",
                "wizard_url": f"{base}/swarms/new?template={magnet.template_id}",
            },
        )
    return rows


def get_lead_magnet(template_id: str) -> LeadMagnetDefinition | None:
    """Resolve one lead magnet definition."""

    return _MAGNET_BY_ID.get(template_id.strip().lower())


def build_landing_payload(template_id: str) -> dict[str, Any]:
    """Public landing page payload (no tenant context)."""

    magnet = get_lead_magnet(template_id)
    if magnet is None:
        raise ValueError(f"Unknown lead magnet template: {template_id}")

    base = _app_base()
    return {
        "template_id": magnet.template_id,
        "name": magnet.name,
        "headline": magnet.headline_sk,
        "tagline": magnet.tagline,
        "description": magnet.description,
        "bullets": list(magnet.bullets_sk),
        "estimated_minutes": magnet.estimated_minutes,
        "time_saved_hours_per_week": magnet.time_saved_hours_per_week,
        "accent_hex": magnet.accent_hex,
        "agent_count": magnet.agent_count,
        "cta_label": "Spustiť wizard",
        "cta_url": f"{base}/swarms/new?template={magnet.template_id}&utm_source=lead_magnet",
        "landing_url": f"{base}/magnet/{magnet.template_id}",
    }


def _share_tiktok(magnet: LeadMagnetDefinition) -> str:
    base = _app_base()
    url = f"{base}/magnet/{magnet.template_id}?utm_source=tiktok"
    tags = "#aiagents #automation #productivity #queenswarm #buildinpublic"
    return (
        f"POV: {magnet.headline_sk.lower()} 🐝\n"
        f"{magnet.estimated_minutes} min setup · {magnet.agent_count} bees · simulation gate ✅\n"
        f"Link v bio 👇 {url}\n{tags}"
    )


def _share_twitter(magnet: LeadMagnetDefinition, *, hours_line: str) -> str:
    base = _app_base()
    url = f"{base}/magnet/{magnet.template_id}?utm_source=twitter"
    return (
        f"{magnet.headline_sk} — {magnet.tagline}. {hours_line} "
        f"Verified swarms on queenswarm.love 🐝 {url}"
    )


async def build_share_pack(
    session: AsyncSession,
    *,
    template_id: str,
    tenant_id: uuid.UUID | None,
    window_days: int = 30,
) -> dict[str, Any]:
    """Operator share pack with optional tenant-verified hours overlay."""

    magnet = get_lead_magnet(template_id)
    if magnet is None:
        raise ValueError(f"Unknown lead magnet template: {template_id}")

    verified_hours: float | None = None
    if tenant_id is not None:
        try:
            payload = await build_time_saved_payload(session, tenant_id=tenant_id, window_days=window_days)
            for row in payload.get("breakdown", []):
                if str(row.get("source_key")) == magnet.template_id:
                    verified_hours = float(row.get("hours_saved") or 0.0)
                    break
        except Exception as exc:  # noqa: BLE001 — best-effort enrichment
            logger.info(
                "ugc_content_engine.time_saved_overlay_failed",
                template_id=template_id,
                tenant_id=str(tenant_id),
                error_type=type(exc).__name__,
            )

    hours_line = (
        f"Na mojom hive som ušetril/a {verified_hours:.1f} h za {window_days} dní (verified tasks)."
        if verified_hours and verified_hours > 0
        else f"Typicky ~{magnet.time_saved_hours_per_week} h/týždeň podľa šablóny."
    )

    landing = build_landing_payload(template_id)
    channels = [
        {
            "id": "tiktok",
            "label": "TikTok / Reels caption",
            "text": _share_tiktok(magnet),
            "char_count": len(_share_tiktok(magnet)),
        },
        {
            "id": "twitter",
            "label": "X / Twitter",
            "text": _share_twitter(magnet, hours_line=hours_line),
            "char_count": len(_share_twitter(magnet, hours_line=hours_line)),
        },
    ]

    share_card_markdown = "\n".join(
        [
            f"# {magnet.headline_sk}",
            "",
            magnet.tagline,
            "",
            *[f"- {b}" for b in magnet.bullets_sk],
            "",
            hours_line,
            "",
            f"[Spustiť wizard]({landing['cta_url']})",
        ],
    )

    return {
        **landing,
        "verified_hours_saved": verified_hours,
        "hours_attribution_line": hours_line,
        "share_channels": channels,
        "share_card_markdown": share_card_markdown,
    }


__all__ = [
    "build_landing_payload",
    "build_share_pack",
    "get_lead_magnet",
    "list_lead_magnets",
    "ugc_content_engine_enabled",
]
