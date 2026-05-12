"""Slack webhook + SMTP alerts for operator-visible hive events (best-effort)."""

from __future__ import annotations

import asyncio
import time
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
from typing import Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


async def notify_slack(message: str, color: str = "#FFB800", title: str = "Queenswarm") -> bool:
    """Send Slack notification via incoming webhook. Returns ``True`` when accepted."""

    webhook_raw = (settings.slack_webhook_url or "").strip()
    if not webhook_raw:
        return False
    payload = {
        "attachments": [
            {
                "color": color,
                "title": f"🐝 {title}",
                "text": message,
                "footer": "Queenswarm",
                "ts": time.time(),
            },
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(webhook_raw, json=payload)
        accepted = response.status_code == 200
        if not accepted:
            logger.warning(
                "notifications.slack.reject",
                agent_id="reporter_bee",
                swarm_id="",
                task_id="",
                status=response.status_code,
            )
        return accepted
    except httpx.HTTPError as exc:
        logger.warning(
            "notifications.slack.http_error",
            agent_id="reporter_bee",
            swarm_id="",
            task_id="",
            error=str(exc),
        )
        return False


async def notify_task_complete(
    agent_name: str,
    task_title: str,
    output_preview: str,
    cost_usd: float = 0.0,
) -> bool:
    """Notify humans when an agent task completes (Slack-first)."""

    msg = f"*{agent_name}* completed: _{task_title}_\n"
    if output_preview:
        msg += f"```{output_preview[:300]}```\n"
    if cost_usd > 0.0:
        msg += f"Cost: ${cost_usd:.4f}"
    return await notify_slack(msg, color="#00FF88", title="Task Complete")


async def notify_agent_error(agent_name: str, error: str) -> bool:
    """Surface terminal executor failures."""

    clipped = error[:200].replace("`", "")
    return await notify_slack(
        f"*{agent_name}* failed: {clipped}",
        color="#FF3366",
        title="Agent Error",
    )


async def notify_budget_alert(spent_today: float, limit: float) -> bool:
    """Warn when today's spend consumes most of the daily envelope."""

    pct = (spent_today / limit * 100.0) if limit > 0 else 0.0
    return await notify_slack(
        f"⚠️ Budget alert: ${spent_today:.2f} / ${limit:.2f} ({pct:.0f}%)",
        color="#FFB800",
        title="Budget Warning",
    )


def _smtp_send_sync(
    *,
    recipient: str,
    subject: str,
    body: str,
    attachment_bytes: bytes | None,
    attachment_filename: str | None,
) -> None:
    """Blocking SMTP submission (runs in a worker thread)."""

    smtp_host = (settings.smtp_host or "").strip() or "smtp.gmail.com"
    smtp_port = int(settings.smtp_port or 587)
    smtp_user_raw = settings.smtp_user
    smtp_pass_raw = settings.smtp_pass
    smtp_user = smtp_user_raw.strip() if smtp_user_raw else ""
    smtp_pass = smtp_pass_raw.strip() if smtp_pass_raw else ""

    msg = MIMEMultipart()
    msg["From"] = smtp_user
    msg["To"] = recipient
    msg["Subject"] = f"🐝 Queenswarm: {subject}"
    msg.attach(MIMEText(body, "plain"))

    if attachment_bytes and attachment_filename:
        part = MIMEBase("application", "octet-stream")
        part.set_payload(attachment_bytes)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{attachment_filename}"')
        msg.attach(part)

    with smtplib.SMTP(smtp_host, smtp_port, timeout=45) as server:
        server.ehlo()
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)


async def notify_email(
    subject: str,
    body: str,
    *,
    to_email: Optional[str] = None,
    attachment_bytes: Optional[bytes] = None,
    attachment_filename: Optional[str] = None,
) -> bool:
    """Deliver email using ``settings`` SMTP fields; returns ``True`` on acceptance."""

    smtp_user_raw = settings.smtp_user
    smtp_pass_raw = settings.smtp_pass
    smtp_user = smtp_user_raw.strip() if smtp_user_raw else ""
    smtp_pass = smtp_pass_raw.strip() if smtp_pass_raw else ""

    recipient = (
        str(to_email or settings.notify_email or smtp_user or "").strip().split(",")[0].strip()
    )

    if not smtp_user or not smtp_pass or not recipient:
        logger.debug(
            "notifications.email.skipped_missing_config",
            agent_id="reporter_bee",
            swarm_id="",
            task_id="",
        )
        return False

    try:
        await asyncio.to_thread(
            _smtp_send_sync,
            recipient=recipient,
            subject=subject,
            body=body,
            attachment_bytes=attachment_bytes,
            attachment_filename=attachment_filename,
        )
        logger.info(
            "notifications.email.sent",
            agent_id="reporter_bee",
            swarm_id="",
            task_id="",
            recipient=recipient,
            subject_preview=subject[:120],
        )
        return True
    except Exception as exc:  # noqa: BLE001 — mail stack is heterogeneous
        logger.warning(
            "notifications.email.failed",
            agent_id="reporter_bee",
            swarm_id="",
            task_id="",
            error=str(exc),
        )
        return False


__all__ = [
    "notify_agent_error",
    "notify_budget_alert",
    "notify_email",
    "notify_slack",
    "notify_task_complete",
]
