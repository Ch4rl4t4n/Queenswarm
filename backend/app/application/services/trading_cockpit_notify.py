"""Trading Cockpit Telegram notifications — fills + daily digest."""

from __future__ import annotations

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.execution_studio_notifications import _resolve_telegram_credentials
from app.application.services.paper_trading_service import build_dashboard_paper_summary
from app.application.services.publish_queue_notify import _resolve_tenant_for_user
from app.core.config import settings
from app.core.notifications import notify_telegram
from app.infrastructure.persistence.models.external_project import ExternalProject
from app.infrastructure.persistence.models.paper_trading import PaperTradingFill
from app.infrastructure.persistence.models.tenant import Tenant

logger = structlog.get_logger(__name__)


async def notify_trading_paper_fill(
    db: AsyncSession,
    *,
    fill: PaperTradingFill,
    project: ExternalProject,
    dashboard_user_id: uuid.UUID,
) -> dict[str, bool]:
    """Best-effort Telegram ping after verified paper fill."""

    if not settings.trading_cockpit_telegram_notify_on_fill:
        return {"telegram": False}

    tenant = await _resolve_tenant_for_user(db, dashboard_user_id=dashboard_user_id)
    token, chat_id = _resolve_telegram_credentials(tenant)
    if not token or not chat_id:
        return {"telegram": False}

    domain = str(settings.domain or "queenswarm.love").strip().rstrip("/")
    base = f"https://{domain}" if not domain.startswith("http") else domain.rstrip("/")
    message = (
        f"📊 Paper fill · {fill.side.upper()} {fill.symbol}\n"
        f"Qty {float(fill.quantity):.4f} @ ${float(fill.fill_price_usd):.2f}\n"
        f"_{fill.signal_note[:160]}_\n\n"
        f"{base}/integrations?tab=studio#trading-cockpit"
    )
    ok = await notify_telegram(message, bot_token=token, chat_id=chat_id)
    logger.info(
        "trading_cockpit.telegram_fill",
        agent_id="trading_cockpit",
        task_id=str(fill.id),
        project_id=str(project.id),
        sent=ok,
    )
    return {"telegram": ok}


async def compose_trading_daily_digest_md(db: AsyncSession) -> str:
    """Markdown digest for morning trading report."""

    summary = await build_dashboard_paper_summary(db)
    lines = [
        "# Trading daily digest",
        "",
        f"- Paper projects: **{summary.get('project_count', 0)}**",
        f"- Total equity: **${summary.get('total_equity_usd', 0):.2f}**",
        f"- Total P&L: **${summary.get('total_pnl_usd', 0):.2f}**",
        "",
    ]
    for proj in summary.get("projects") or []:
        lines.append(
            f"- {proj.get('display_name', 'Trader')}: "
            f"P&L ${proj.get('total_pnl_usd', 0):.2f} "
            f"({proj.get('total_pnl_pct', 0):.1f}%)",
        )
    return "\n".join(lines).strip() + "\n"


async def notify_operator_loop_morning_telegram(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
) -> dict[str, bool]:
    """Morning Telegram digest — Control Plane cockpit snapshot."""

    if not settings.operator_loop_telegram_morning_enabled:
        return {"telegram": False}

    from app.application.services.operator_control_plane import compose_operator_cockpit_snapshot

    tenant = await db.get(Tenant, tenant_id)
    snap = await compose_operator_cockpit_snapshot(
        db,
        tenant_id=tenant_id,
        dashboard_user_id=dashboard_user_id,
        tenant=tenant,
        phase="morning",
    )

    token, chat_id = _resolve_telegram_credentials(tenant)
    if not token or not chat_id:
        return {"telegram": False}

    loop = snap.operator_loop
    overnight = loop.get("overnight") or {}
    pending = int((loop.get("publish_pipeline") or {}).get("pending_publish_count") or 0)
    pnl = float((loop.get("trading") or {}).get("performance", {}).get("total_pnl_usd") or 0)
    onboard = int((loop.get("publish_onboarding") or {}).get("progress_pct") or 0)
    trio_bound = int(snap.trio.get("lanes_bound") or snap.trio.get("bound_lane_count") or 0)

    lines = [
        "☀️ *Hive Cockpit — morning*",
        f"3 Bees: {trio_bound}/3",
        f"Overnight ingested: {overnight.get('items_ingested', 0)} · stalled: {overnight.get('stalled_signals', 0)}",
        f"Publish pending: {pending} · onboarding: {onboard}%",
        f"Paper P&L: ${pnl:.2f}",
    ]
    if snap.now_actions:
        lines.append("")
        lines.append("*Next:*")
        for action in snap.now_actions[:4]:
            lines.append(f"• {action.label}")

    domain = str(settings.domain or "queenswarm.love").strip().rstrip("/")
    base = f"https://{domain}" if not domain.startswith("http") else domain.rstrip("/")
    lines.append(f"\n{base}/cockpit")

    ok = await notify_telegram("\n".join(lines), bot_token=token, chat_id=chat_id)
    logger.info(
        "operator_loop.telegram_morning",
        agent_id="operator_loop",
        task_id=str(tenant_id),
        sent=ok,
    )
    return {"telegram": ok}


__all__ = [
    "compose_trading_daily_digest_md",
    "notify_operator_loop_morning_telegram",
    "notify_trading_paper_fill",
]
