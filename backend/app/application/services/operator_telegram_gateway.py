"""Telegram inbound gateway for Zero-UI Operator Control Plane."""

from __future__ import annotations

import uuid
from typing import Any, Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.execution_studio_notifications import _resolve_telegram_credentials
from app.application.services.operator_control_plane import (
    OperatorActRequest,
    OperatorCockpitSnapshotOut,
    compose_operator_cockpit_snapshot,
    execute_operator_action,
)
from app.core.config import settings
from app.core.notifications import notify_telegram
from app.infrastructure.persistence.models.tenant import DashboardUserTenantMembership, Tenant

logger = structlog.get_logger(__name__)

ZeroUiPriority = Literal["critical", "simulate", "info"]

TELEGRAM_COMMANDS_HELP: tuple[str, ...] = (
    "/day — Spusti deň (trio cycle)",
    "/status — Cockpit snapshot",
    "/hotline <text> — Bee Hotline → Queen goal",
    "/factory <text> — Factory Spark",
    "/crystal <text> — Intent Crystallizer",
    "/help — Príkazy",
)


class TelegramCommandParseOut(BaseModel):
    """Parsed Telegram message → control-plane action."""

    model_config = ConfigDict(extra="ignore")

    kind: Literal["help", "status", "act"]
    action: OperatorActRequest | None = None


class ZeroUiStatusOut(BaseModel):
    """Zero-UI / Telegram gateway status for cockpit."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool
    telegram_configured: bool
    webhook_secret_configured: bool
    webhook_url: str | None = None
    commands: list[str] = Field(default_factory=list)


def build_operator_telegram_webhook_url() -> str | None:
    """Public webhook URL when secret + domain configured."""

    secret = (settings.operator_telegram_webhook_secret or "").strip()
    if not secret:
        return None
    domain = str(settings.domain or "queenswarm.love").strip().rstrip("/")
    base = domain if domain.startswith("http") else f"https://{domain}"
    return f"{base.rstrip('/')}/api/v1/operator/telegram/webhook/{secret}"


def verify_operator_telegram_webhook_secret(
    *,
    path_secret: str,
    header_secret: str | None = None,
) -> bool:
    """Verify path secret and optional Telegram ``secret_token`` header."""

    expected = (settings.operator_telegram_webhook_secret or "").strip()
    if not expected:
        return False
    if path_secret.strip() != expected:
        return False
    if header_secret is not None and header_secret.strip() and header_secret.strip() != expected:
        return False
    return True


def compose_zero_ui_status(*, tenant: Tenant | None) -> ZeroUiStatusOut:
    """Zero-UI block for cockpit snapshot."""

    token, chat_id = _resolve_telegram_credentials(tenant)
    configured = bool(token and chat_id)
    inbound = bool(
        settings.operator_control_plane_enabled
        and settings.operator_telegram_inbound_enabled,
    )
    webhook_url = build_operator_telegram_webhook_url() if configured and inbound else None
    return ZeroUiStatusOut(
        enabled=inbound,
        telegram_configured=configured,
        webhook_secret_configured=bool((settings.operator_telegram_webhook_secret or "").strip()),
        webhook_url=webhook_url,
        commands=list(TELEGRAM_COMMANDS_HELP),
    )


def parse_telegram_command(text: str) -> TelegramCommandParseOut:
    """Map Telegram text to control-plane action or status/help."""

    raw = (text or "").strip()
    if not raw:
        return TelegramCommandParseOut(kind="help")

    lowered = raw.lower()
    if lowered in {"/start", "/help"}:
        return TelegramCommandParseOut(kind="help")

    if lowered in {"/day", "/start_day", "/startday"}:
        return TelegramCommandParseOut(
            kind="act",
            action=OperatorActRequest(action="start_day"),
        )

    if lowered.startswith("/status"):
        return TelegramCommandParseOut(kind="status")

    if lowered.startswith("/hotline") or lowered.startswith("/goal"):
        payload = raw.split(maxsplit=1)[1].strip() if " " in raw else ""
        if len(payload) < 8:
            return TelegramCommandParseOut(kind="help")
        return TelegramCommandParseOut(
            kind="act",
            action=OperatorActRequest(action="hotline", text=payload),
        )

    if lowered.startswith("/factory"):
        payload = raw.split(maxsplit=1)[1].strip() if " " in raw else ""
        if len(payload) < 8:
            return TelegramCommandParseOut(kind="help")
        return TelegramCommandParseOut(
            kind="act",
            action=OperatorActRequest(action="factory_spark", text=payload),
        )

    if lowered.startswith("/crystal"):
        payload = raw.split(maxsplit=1)[1].strip() if " " in raw else ""
        if len(payload) < 8:
            return TelegramCommandParseOut(kind="help")
        return TelegramCommandParseOut(
            kind="act",
            action=OperatorActRequest(action="crystallize_intent", text=payload),
        )

    if lowered.startswith("/approve"):
        return TelegramCommandParseOut(kind="status")

    if raw.startswith("/"):
        return TelegramCommandParseOut(kind="help")

    if len(raw) >= 8:
        return TelegramCommandParseOut(
            kind="act",
            action=OperatorActRequest(action="hotline", text=raw),
        )

    return TelegramCommandParseOut(kind="help")


def format_telegram_help() -> str:
    """Help text for Telegram commands."""

    lines = ["🐝 *Zero-UI Hive Mode*", "", "Príkazy:"]
    lines.extend(f"• {row}" for row in TELEGRAM_COMMANDS_HELP)
    lines.append("")
    lines.append("Plain text (8+ znakov) → Bee Hotline.")
    return "\n".join(lines)


def format_cockpit_status_text(*, snapshot: OperatorCockpitSnapshotOut, base_url: str) -> str:
    """Compact cockpit status for Telegram /status."""

    trio_bound = int(snapshot.trio.get("lanes_bound") or snapshot.trio.get("bound_lane_count") or 0)
    pending = int(snapshot.innovation_lab.get("pending_count") or 0)
    publish_pending = int(
        (snapshot.operator_loop.get("publish_pipeline") or {}).get("pending_publish_count") or 0,
    )
    lines = [
        "📊 *Hive Cockpit*",
        f"3 Bees: {trio_bound}/3 · Innovation pending: {pending}",
        f"Publish pending: {publish_pending}",
    ]
    if snapshot.oracle_warnings:
        lines.append("")
        lines.append("*Oracle:*")
        for warning in snapshot.oracle_warnings[:3]:
            lines.append(f"• {warning.get('message', '')}")
    if snapshot.now_actions:
        lines.append("")
        lines.append("*Next:*")
        for action in snapshot.now_actions[:4]:
            lines.append(f"• {action.label}")
    lines.append(f"\n{base_url.rstrip('/')}/cockpit")
    return "\n".join(lines)


def _priority_emoji(priority: ZeroUiPriority) -> str:
    if priority == "critical":
        return "🔴"
    if priority == "simulate":
        return "🟡"
    return "🟢"


def _base_url() -> str:
    domain = str(settings.domain or "queenswarm.love").strip().rstrip("/")
    return domain if domain.startswith("http") else f"https://{domain}"


async def find_tenant_by_telegram_chat_id(
    db: AsyncSession,
    *,
    chat_id: str | int,
) -> tuple[Tenant, uuid.UUID] | None:
    """Resolve tenant + owner/admin dashboard user from registered Telegram chat id."""

    target = str(chat_id).strip()
    if not target:
        return None

    tenants = list((await db.scalars(select(Tenant).limit(200))).all())
    for tenant in tenants:
        _token, registered_chat = _resolve_telegram_credentials(tenant)
        if registered_chat != target:
            continue
        membership = await db.scalar(
            select(DashboardUserTenantMembership)
            .where(
                DashboardUserTenantMembership.tenant_id == tenant.id,
                DashboardUserTenantMembership.role.in_(("owner", "admin")),
            )
            .order_by(DashboardUserTenantMembership.created_at.asc())
            .limit(1),
        )
        if membership is not None:
            return tenant, membership.dashboard_user_id
    return None


async def notify_zero_ui_ping(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    dashboard_user_id: uuid.UUID,
    priority: ZeroUiPriority,
    title: str,
    detail: str = "",
    href: str | None = None,
) -> dict[str, bool]:
    """Priority Telegram ping for verified operator outcomes."""

    if not settings.operator_zero_ui_notify_enabled:
        return {"telegram": False}

    tenant = await db.get(Tenant, tenant_id)
    token, chat_id = _resolve_telegram_credentials(tenant)
    if not token or not chat_id:
        return {"telegram": False}

    emoji = _priority_emoji(priority)
    lines = [f"{emoji} *{title}*"]
    if detail.strip():
        lines.append(detail.strip()[:500])
    if href:
        path = href if href.startswith("http") else f"{_base_url().rstrip('/')}{href}"
        lines.append(f"\n{path}")
    else:
        lines.append(f"\n{_base_url().rstrip('/')}/cockpit")

    ok = await notify_telegram("\n".join(lines), bot_token=token, chat_id=chat_id)
    logger.info(
        "operator_telegram.zero_ui_ping",
        agent_id="operator_telegram_gateway",
        task_id=str(tenant_id),
        priority=priority,
        sent=ok,
    )
    return {"telegram": ok}


async def handle_telegram_update(
    db: AsyncSession,
    *,
    update: dict[str, Any],
) -> str:
    """Process one Telegram update and return reply text."""

    if not settings.operator_telegram_inbound_enabled or not settings.operator_control_plane_enabled:
        return "Zero-UI gateway disabled."

    message = update.get("message") or update.get("edited_message")
    if not isinstance(message, dict):
        return ""

    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    text_raw = message.get("text")
    if chat_id is None or not isinstance(text_raw, str):
        return ""

    resolved = await find_tenant_by_telegram_chat_id(db, chat_id=chat_id)
    if resolved is None:
        logger.warning(
            "operator_telegram.unknown_chat",
            agent_id="operator_telegram_gateway",
            task_id=str(chat_id),
        )
        return "Neznámy chat — nastav Telegram v Execution Studio notifications."

    tenant, dashboard_user_id = resolved
    parsed = parse_telegram_command(text_raw)

    if parsed.kind == "help":
        return format_telegram_help()

    if parsed.kind == "status":
        snapshot = await compose_operator_cockpit_snapshot(
            db,
            tenant_id=tenant.id,
            dashboard_user_id=dashboard_user_id,
            tenant=tenant,
            phase="anytime",
        )
        return format_cockpit_status_text(snapshot=snapshot, base_url=_base_url())

    if parsed.kind == "act" and parsed.action is not None:
        from_user = message.get("from") or {}
        reviewer = str(from_user.get("username") or from_user.get("first_name") or "telegram-operator")
        if parsed.action.action == "crystallize_intent" and parsed.action.text:
            from app.application.services.intent_crystallizer import crystallize_intent, format_crystallized_telegram

            plan = crystallize_intent(parsed.action.text)
            return format_crystallized_telegram(plan, base_url=_base_url())
        result = await execute_operator_action(
            db,
            tenant_id=tenant.id,
            dashboard_user_id=dashboard_user_id,
            tenant=tenant,
            reviewer_subject=f"telegram:{reviewer}",
            body=parsed.action,
        )
        await db.commit()
        lines = [result.message]
        if result.href:
            lines.append(f"{_base_url().rstrip('/')}{result.href}")
        return "\n".join(lines)

    return format_telegram_help()


async def process_telegram_webhook(
    db: AsyncSession,
    *,
    update: dict[str, Any],
) -> None:
    """Handle webhook update and send Telegram reply."""

    message = update.get("message") or update.get("edited_message")
    if not isinstance(message, dict):
        return

    chat = message.get("chat") or {}
    chat_id = chat.get("id")
    if chat_id is None:
        return

    reply = await handle_telegram_update(db, update=update)
    if not reply.strip():
        return

    resolved = await find_tenant_by_telegram_chat_id(db, chat_id=chat_id)
    if resolved is None:
        return

    tenant, _user_id = resolved
    token, registered_chat = _resolve_telegram_credentials(tenant)
    if not token or not registered_chat:
        return

    await notify_telegram(reply, bot_token=token, chat_id=registered_chat)


__all__ = [
    "TELEGRAM_COMMANDS_HELP",
    "ZeroUiStatusOut",
    "build_operator_telegram_webhook_url",
    "compose_zero_ui_status",
    "find_tenant_by_telegram_chat_id",
    "format_cockpit_status_text",
    "format_telegram_help",
    "handle_telegram_update",
    "notify_zero_ui_ping",
    "parse_telegram_command",
    "process_telegram_webhook",
    "verify_operator_telegram_webhook_secret",
]
