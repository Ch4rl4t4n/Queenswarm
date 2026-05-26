"""Operator notifications for Execution Studio approval gates."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.supervisor.session_audit_digest_config import (
    get_tenant_audit_digest_config,
    normalize_extra_recipients,
)
from app.core.config import settings
from app.core.logging import get_logger
from app.core.notifications import notify_discord, notify_email, notify_slack, notify_teams, notify_telegram
from app.infrastructure.persistence.models.tenant import Tenant

logger = get_logger(__name__)

NOTIFICATION_TEST_CHANNELS = frozenset({"slack", "discord", "teams", "telegram", "email"})


def notification_value_fingerprint(value: str) -> str:
    """Fingerprint webhook URL or email list for cross-device test status matching."""

    trimmed = (value or "").strip()
    if not trimmed:
        return ""
    return trimmed if len(trimmed) <= 48 else trimmed[-48:]


def _notification_test_status_bucket(notifications: dict[str, Any]) -> dict[str, Any]:
    raw = notifications.get("webhook_test_status")
    return dict(raw) if isinstance(raw, dict) else {}


def record_notification_test_status(
    tenant: Tenant | None,
    *,
    channel: str,
    value: str,
    status: str,
) -> None:
    """Persist webhook/email test outcome on tenant operator settings."""

    if tenant is None or channel not in NOTIFICATION_TEST_CHANNELS:
        return
    if status not in {"ok", "fail"}:
        return
    fingerprint = notification_value_fingerprint(value)
    if not fingerprint:
        return

    root = dict(tenant.operator_settings or {})
    studio = dict(root.get("execution_studio") or {}) if isinstance(root.get("execution_studio"), dict) else {}
    notifications = dict(studio.get("notifications") or {}) if isinstance(studio.get("notifications"), dict) else {}
    test_status = _notification_test_status_bucket(notifications)
    tested_at = datetime.now(tz=UTC).isoformat()
    test_status[channel] = {
        "fingerprint": fingerprint,
        "status": status,
        "tested_at": tested_at,
    }
    notifications["webhook_test_status"] = test_status
    history = list(notifications.get("webhook_test_history") or [])
    history.append(
        {
            "channel": channel,
            "status": status,
            "tested_at": tested_at,
        },
    )
    notifications["webhook_test_history"] = history[-20:]
    studio["notifications"] = notifications
    root["execution_studio"] = studio
    tenant.operator_settings = root


def list_webhook_test_history(tenant: Tenant | None, *, limit: int = 10) -> list[dict[str, str]]:
    """Return recent webhook/email test attempts for operator UI."""

    notifications = _studio_notifications_bucket(tenant)
    raw = notifications.get("webhook_test_history")
    if not isinstance(raw, list):
        return []
    rows = [dict(item) for item in raw if isinstance(item, dict)]
    cap = max(1, min(limit, 20))
    return list(reversed(rows[-cap:]))


def clear_notification_test_status(notifications: dict[str, Any], channel: str) -> None:
    """Drop stored test status when operator edits the underlying field."""

    if channel not in NOTIFICATION_TEST_CHANNELS:
        return
    test_status = _notification_test_status_bucket(notifications)
    test_status.pop(channel, None)
    if test_status:
        notifications["webhook_test_status"] = test_status
    else:
        notifications.pop("webhook_test_status", None)


def build_notification_test_status_ui(tenant: Tenant | None) -> dict[str, dict[str, str]]:
    """Return ok/fail and tested_at per channel when fingerprint matches current config."""

    if tenant is None:
        return {}

    notifications = _studio_notifications_bucket(tenant)
    test_status = _notification_test_status_bucket(notifications)
    if not test_status:
        return {}

    current_values: dict[str, str] = {
        "slack": _resolve_webhook(tenant, channel="slack") or "",
        "discord": _resolve_webhook(tenant, channel="discord") or "",
        "teams": _resolve_webhook(tenant, channel="teams") or "",
        "telegram": _telegram_fingerprint(tenant),
        "email": ", ".join(_resolve_email_recipients(tenant)),
    }

    ui: dict[str, dict[str, str]] = {}
    for channel, row in test_status.items():
        if channel not in NOTIFICATION_TEST_CHANNELS or not isinstance(row, dict):
            continue
        stored_fp = str(row.get("fingerprint") or "")
        stored_status = str(row.get("status") or "")
        if stored_status not in {"ok", "fail"}:
            continue
        if stored_fp and stored_fp == notification_value_fingerprint(current_values.get(channel, "")):
            ui[channel] = {
                "status": stored_status,
                "tested_at": str(row.get("tested_at") or ""),
            }
    return ui


def _studio_notifications_bucket(tenant: Tenant | None) -> dict[str, Any]:
    if tenant is None:
        return {}
    root = dict(tenant.operator_settings or {})
    studio = root.get("execution_studio")
    if not isinstance(studio, dict):
        return {}
    notifications = studio.get("notifications")
    return dict(notifications) if isinstance(notifications, dict) else {}


def _resolve_webhook(tenant: Tenant | None, *, channel: str) -> str | None:
    """Resolve webhook URL from studio bucket, audit digest, or global settings."""

    studio = _studio_notifications_bucket(tenant)
    studio_key = f"{channel}_webhook_url"
    studio_url = studio.get(studio_key)
    if isinstance(studio_url, str) and studio_url.strip():
        return studio_url.strip()

    digest = get_tenant_audit_digest_config(tenant) if tenant is not None else {}
    digest_url = digest.get(f"{channel}_webhook_url")
    if isinstance(digest_url, str) and digest_url.strip():
        return digest_url.strip()

    if channel == "slack":
        global_url = settings.slack_webhook_url
        if isinstance(global_url, str) and global_url.strip():
            return global_url.strip()
    return None


def _resolve_telegram_credentials(tenant: Tenant | None) -> tuple[str, str]:
    """Resolve Telegram bot token + chat id from Execution Studio notification settings."""

    studio = _studio_notifications_bucket(tenant)
    token_raw = studio.get("telegram_bot_token")
    chat_raw = studio.get("telegram_chat_id")
    token = token_raw.strip() if isinstance(token_raw, str) else ""
    chat_id = str(chat_raw).strip() if chat_raw is not None else ""
    if token and ":" not in token:
        token = ""
    return token, chat_id


def _telegram_fingerprint(tenant: Tenant | None) -> str:
    token, chat_id = _resolve_telegram_credentials(tenant)
    if not token or not chat_id:
        return ""
    return f"{token}|{chat_id}"


def _resolve_email_recipients(tenant: Tenant | None) -> list[str]:
    """Resolve operator email recipients for Execution Studio digests."""

    recipients: list[str] = []
    studio = _studio_notifications_bucket(tenant)
    for key in ("email_recipients", "digest_emails"):
        raw = studio.get(key)
        if isinstance(raw, list):
            recipients.extend(normalize_extra_recipients(raw))

    if tenant is not None:
        digest_extra = get_tenant_audit_digest_config(tenant).get("extra_recipients")
        recipients.extend(normalize_extra_recipients(digest_extra))

    global_email = settings.notify_email
    if isinstance(global_email, str) and global_email.strip():
        recipients.extend(normalize_extra_recipients([global_email.strip()]))

    return sorted(set(recipients))


async def notify_execution_studio_email(
    *,
    tenant: Tenant | None,
    title: str,
    body: str,
) -> bool:
    """Send Execution Studio digest email to configured operator recipients."""

    recipients = _resolve_email_recipients(tenant)
    if not recipients:
        return False

    sent_any = False
    for recipient in recipients:
        ok = await notify_email(subject=title, body=body, to_email=recipient)
        sent_any = sent_any or ok
    if sent_any:
        logger.info(
            "execution_studio.email_digest_sent",
            agent_id="reporter_bee",
            swarm_id=str(tenant.id if tenant is not None else ""),
            task_id="email_digest",
            recipient_count=len(recipients),
        )
    return sent_any


async def notify_execution_studio_pending_approval(
    *,
    tenant: Tenant | None,
    title: str,
    message: str,
    supervisor_session_id: uuid.UUID | None = None,
    color: str = "#FF00AA",
    session: AsyncSession | None = None,
) -> dict[str, bool]:
    """Notify operator channels when Execution Studio action needs approval."""

    if not settings.execution_studio_enabled:
        return {"slack": False, "discord": False, "teams": False, "telegram": False}

    session_note = f"\nSession: `{supervisor_session_id}`" if supervisor_session_id else ""
    body = f"{message.strip()}{session_note}\n\nOpen Execution Studio → Confirm live step or approve proposal."

    slack_url = _resolve_webhook(tenant, channel="slack")
    discord_url = _resolve_webhook(tenant, channel="discord")
    teams_url = _resolve_webhook(tenant, channel="teams")
    tg_token, tg_chat = _resolve_telegram_credentials(tenant)

    results = {
        "slack": await notify_slack(body, color=color, title=title, webhook_url=slack_url),
        "discord": await notify_discord(body, webhook_url=discord_url),
        "teams": await notify_teams(body, title=title, theme_color=color.lstrip("#"), webhook_url=teams_url),
        "telegram": await notify_telegram(body, bot_token=tg_token, chat_id=tg_chat),
    }

    if any(results.values()):
        logger.info(
            "execution_studio.pending_approval_notified",
            agent_id="reporter_bee",
            swarm_id=str(tenant.id if tenant is not None else ""),
            task_id=str(supervisor_session_id or ""),
            channels=results,
        )

    await _maybe_send_pending_web_push(
        tenant=tenant,
        title=title,
        body=message.strip()[:240],
        supervisor_session_id=supervisor_session_id,
        session=session,
    )
    return results


async def _maybe_send_pending_web_push(
    *,
    tenant: Tenant | None,
    title: str,
    body: str,
    supervisor_session_id: uuid.UUID | None,
    session: AsyncSession | None = None,
) -> None:
    """Best-effort Web Push when pending approval is created."""

    from app.application.services.execution_studio_push import send_execution_studio_web_push

    url = "/integrations?tab=studio"
    if supervisor_session_id is not None:
        url = f"/ballroom?session={supervisor_session_id}"
    await send_execution_studio_web_push(
        tenant=tenant,
        title=title,
        body=body,
        url=url,
        session=session,
    )


async def ping_studio_notification_webhooks(
    *,
    tenant: Tenant | None,
    channels: list[str] | None = None,
) -> dict[str, bool | str]:
    """Ping configured Execution Studio Slack, Discord, Teams, and Telegram channels."""

    if not settings.execution_studio_enabled:
        return {"detail": "disabled", "slack": False, "discord": False, "teams": False, "telegram": False}

    allowed = {"slack", "discord", "teams", "telegram"}
    selected = [ch for ch in (channels or ["slack", "discord", "teams", "telegram"]) if ch in allowed]
    if not selected:
        return {"detail": "invalid_channels", "slack": False, "discord": False, "teams": False, "telegram": False}

    message = "Queenswarm Execution Studio webhook test — channel is reachable."
    results: dict[str, bool | str] = {"slack": False, "discord": False, "teams": False, "telegram": False}

    if "slack" in selected:
        results["slack"] = await notify_slack(
            message,
            color="#00FFFF",
            title="Execution Studio webhook test",
            webhook_url=_resolve_webhook(tenant, channel="slack"),
        )
    if "discord" in selected:
        results["discord"] = await notify_discord(
            message,
            webhook_url=_resolve_webhook(tenant, channel="discord"),
        )
    if "teams" in selected:
        results["teams"] = await notify_teams(
            message,
            title="Execution Studio webhook test",
            webhook_url=_resolve_webhook(tenant, channel="teams"),
        )
    if "telegram" in selected:
        tg_token, tg_chat = _resolve_telegram_credentials(tenant)
        results["telegram"] = await notify_telegram(message, bot_token=tg_token, chat_id=tg_chat)

    if not any(bool(results[ch]) for ch in selected):
        return {"detail": "no_webhooks_accepted", **results}
    return results


async def ping_studio_digest_email(*, tenant: Tenant | None) -> dict[str, bool | str]:
    """Send one test digest email to configured Execution Studio recipients."""

    if not settings.execution_studio_enabled:
        return {"detail": "disabled", "sent": False}

    recipients = _resolve_email_recipients(tenant)
    if not recipients:
        return {"detail": "no_recipients", "sent": False}

    smtp_user = (settings.smtp_user or "").strip()
    smtp_pass = (settings.smtp_pass or "").strip()
    if not smtp_user or not smtp_pass:
        return {"detail": "smtp_not_configured", "sent": False, "recipient_count": len(recipients)}

    sent = await notify_execution_studio_email(
        tenant=tenant,
        title="Execution Studio digest test",
        body="Queenswarm Execution Studio digest email test — delivery path is reachable.",
    )
    if not sent:
        return {"detail": "delivery_failed", "sent": False}
    return {"sent": True, "recipient_count": len(recipients)}


async def send_studio_weekly_rollup_preview(
    *,
    tenant: Tenant | None,
    channel_group: str | None = None,
    channels: list[str] | None = None,
    session: AsyncSession | None = None,
) -> dict[str, Any]:
    """Deliver the current weekly rollup preview to configured operator channels."""

    from app.application.services.execution_studio_activity import persist_execution_activity
    from app.application.services.execution_studio_telemetry_rollup import (
        build_weekly_execution_studio_rollup_preview,
    )

    if not settings.execution_studio_enabled:
        return {"detail": "disabled", "ok": False}

    if tenant is None:
        return {"detail": "tenant_missing", "ok": False}

    preview = build_weekly_execution_studio_rollup_preview(tenant=tenant)
    message = str(preview["message"])
    email_body = str(preview["email_body"])
    title = "Execution Studio weekly rollup (preview send)"
    email_title = f"Execution Studio weekly rollup · {tenant.name}"

    allowed = {"slack", "discord", "teams", "telegram", "email"}
    if channels:
        selected = {ch for ch in channels if ch in allowed}
    elif channel_group == "email":
        selected = {"email"}
    elif channel_group == "webhooks":
        selected = {"slack", "discord", "teams", "telegram"}
    else:
        selected = allowed

    results: dict[str, bool] = {"slack": False, "discord": False, "teams": False, "telegram": False, "email": False}

    if "slack" in selected:
        results["slack"] = await notify_slack(
            message,
            color="#FFB800",
            title=title,
            webhook_url=_resolve_webhook(tenant, channel="slack"),
        )
    if "discord" in selected:
        results["discord"] = await notify_discord(
            message,
            webhook_url=_resolve_webhook(tenant, channel="discord"),
        )
    if "teams" in selected:
        results["teams"] = await notify_teams(
            message,
            title=title,
            theme_color="FFB800",
            webhook_url=_resolve_webhook(tenant, channel="teams"),
        )
    if "telegram" in selected:
        tg_token, tg_chat = _resolve_telegram_credentials(tenant)
        results["telegram"] = await notify_telegram(message, bot_token=tg_token, chat_id=tg_chat)
    if "email" in selected:
        results["email"] = await notify_execution_studio_email(
            tenant=tenant,
            title=email_title,
            body=email_body,
        )

    sent = any(bool(value) for value in results.values())
    if not sent:
        return {
            "detail": "no_channels_delivered",
            "ok": False,
            "channels": results,
            "channel_group": channel_group,
            "selected": sorted(selected),
        }

    if session is not None:
        delivered = [name for name, ok in results.items() if ok]
        await persist_execution_activity(
            session,
            tenant,
            event_type="digest_preview_send",
            message=f"Manual weekly digest preview sent ({', '.join(delivered)})",
            payload={"channels": results, "channel_group": channel_group or "all", "selected": sorted(selected)},
        )
        await session.commit()

    logger.info(
        "execution_studio.digest_preview_sent",
        agent_id="reporter_bee",
        swarm_id=str(tenant.id),
        task_id="digest_preview_send",
        channels=results,
        channel_group=channel_group or "all",
        selected=sorted(selected),
    )
    return {
        "ok": True,
        "channels": results,
        "channel_group": channel_group or "all",
        "selected": sorted(selected),
    }


async def notify_browser_live_pending(
    *,
    tenant: Tenant | None,
    supervisor_session_id: uuid.UUID,
    goal_excerpt: str,
    start_url: str | None = None,
    session: AsyncSession | None = None,
) -> dict[str, bool]:
    """Slack/Discord/Teams ping when auto browser live step awaits operator confirmation."""

    url_note = f"\nURL: `{start_url}`" if start_url else ""
    message = (
        "Connector failure triggered auto browser simulate. "
        f"Live harness step requires operator confirmation.{url_note}\n"
        f"Goal: {goal_excerpt[:400]}"
    )
    return await notify_execution_studio_pending_approval(
        tenant=tenant,
        title="Browser live step pending",
        message=message,
        supervisor_session_id=supervisor_session_id,
        color="#FF00AA",
        session=session,
    )


async def notify_external_live_pending(
    *,
    tenant: Tenant | None,
    proposal_id: uuid.UUID,
    connector_slug: str,
    tool_name: str,
    goal_excerpt: str,
    session: AsyncSession | None = None,
) -> dict[str, bool]:
    """Notify when external proposal simulate succeeded but live connector needs approval."""

    message = (
        f"External proposal `{proposal_id}` auto-simulated `{connector_slug}/{tool_name}`. "
        "Live connector execution requires operator approval.\n"
        f"Goal: {goal_excerpt[:400]}"
    )
    return await notify_execution_studio_pending_approval(
        tenant=tenant,
        title="External live connector pending",
        message=message,
        color="#FFB800",
        session=session,
    )


__all__ = [
    "build_notification_test_status_ui",
    "clear_notification_test_status",
    "list_webhook_test_history",
    "notification_value_fingerprint",
    "notify_browser_live_pending",
    "notify_execution_studio_email",
    "notify_execution_studio_pending_approval",
    "notify_external_live_pending",
    "ping_studio_digest_email",
    "ping_studio_notification_webhooks",
    "record_notification_test_status",
    "send_studio_weekly_rollup_preview",
]
