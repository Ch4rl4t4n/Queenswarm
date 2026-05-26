"""Trade → Content pipeline — verified paper fill → publish pack draft (P8)."""

from __future__ import annotations

import uuid
from typing import Any

import structlog
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.publish_hook_variants import generate_publish_hook_variants
from app.application.services.publish_pack import (
    TAG_PUBLISH_PACK,
    TAG_PUBLISH_PACK_VERIFIED,
    TAG_READY_TO_PUBLISH,
    TAG_SIMULATE_ONLY,
    PublishPackArtifact,
    build_publish_pack_markdown,
)
from app.core.config import settings
from app.domain.outputs.engine import OutputEngine
from app.domain.outputs.service import slugify_fragment
from app.infrastructure.persistence.models.external_project import ExternalProject
from app.infrastructure.persistence.models.paper_trading import PaperTradingFill

logger = structlog.get_logger(__name__)

TAG_TRADE_TO_CONTENT = "trade-to-content"


class TradeContentResultOut(BaseModel):
    """Outcome of trade → content draft."""

    model_config = ConfigDict(extra="ignore")

    created: bool
    deliverable_id: str | None = None
    title: str | None = None
    reason: str | None = None


def _build_pack_from_fill(*, fill: PaperTradingFill, project: ExternalProject) -> PublishPackArtifact:
    """Build simulate-only publish pack from paper fill."""

    side = fill.side.upper()
    pnl_hint = "paper trade" if (project.settings or {}).get("trading_mode") == "paper" else "trade"
    title = f"{side} {fill.symbol} — {pnl_hint} update"
    body = (
        f"Signal: {fill.signal_note}\n\n"
        f"Executed {side} {float(fill.quantity):.4f} {fill.symbol} @ ${float(fill.fill_price_usd):.2f} "
        f"(notional ${float(fill.notional_usd):.2f}).\n\n"
        "Paper mode — educational content only. Not financial advice."
    )
    return PublishPackArtifact(
        channel="twitter",
        title=title[:200],
        body=body[:8000],
        hashtags=["trading", "papertrading", "polymarket", "queenswarm"],
        cta="Follow for verified swarm updates.",
        simulate_only=True,
    )


async def create_publish_draft_from_paper_fill(
    session: AsyncSession,
    *,
    fill: PaperTradingFill,
    project: ExternalProject,
) -> TradeContentResultOut:
    """Archive verified publish pack draft after paper fill (best-effort)."""

    if not settings.trade_to_content_enabled:
        return TradeContentResultOut(created=False, reason="trade_to_content_disabled")

    pack = _build_pack_from_fill(fill=fill, project=project)
    hook_variants = generate_publish_hook_variants(
        title=pack.title,
        body=pack.body,
        channel=pack.channel,
    ) if settings.publish_hook_variants_enabled else []

    structured = pack.model_dump()
    structured["verified"] = True
    structured["source"] = TAG_TRADE_TO_CONTENT
    structured["paper_fill_id"] = str(fill.id)
    structured["project_id"] = str(project.id)
    if hook_variants:
        structured["hook_variants"] = hook_variants

    markdown = build_publish_pack_markdown(pack, critic_excerpt="Auto-generated from verified paper fill.")
    tags = sorted(
        dict.fromkeys(
            [
                TAG_PUBLISH_PACK,
                TAG_SIMULATE_ONLY,
                TAG_PUBLISH_PACK_VERIFIED,
                TAG_READY_TO_PUBLISH,
                TAG_TRADE_TO_CONTENT,
                pack.channel,
                "trading",
            ],
        ),
    )

    row = await OutputEngine.create_final_deliverable(
        session,
        lineage_id=project.id,
        markdown_body=markdown,
        structured=structured,
        title_hint=pack.title[:200],
        slug_hint=slugify_fragment(pack.title[:120]),
        tags=tags,
        voice_script=None,
        dashboard_user_id=project.owner_dashboard_user_id,
        ballroom_session_id=None,
        mission_id=None,
        source_task_id=None,
    )
    await session.flush()

    logger.info(
        "trade_to_content.created",
        agent_id="trade_to_content",
        task_id=str(row.id),
        fill_id=str(fill.id),
        project_id=str(project.id),
    )

    from app.application.services.trust_autopilot_notify import notify_publish_pack_simulate_ready

    await notify_publish_pack_simulate_ready(
        session,
        row=row,
        dashboard_user_id=project.owner_dashboard_user_id,
    )

    return TradeContentResultOut(created=True, deliverable_id=str(row.id), title=pack.title)


__all__ = ["TradeContentResultOut", "create_publish_draft_from_paper_fill"]
