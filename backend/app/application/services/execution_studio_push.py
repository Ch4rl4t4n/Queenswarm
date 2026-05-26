"""Web Push delivery for Execution Studio pending operator approvals."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from pywebpush import WebPushException, webpush
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.infrastructure.persistence.models.dashboard_user import DashboardUser
from app.infrastructure.persistence.models.tenant import Tenant

logger = get_logger(__name__)


def _studio_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    studio = root.get("execution_studio")
    return dict(studio) if isinstance(studio, dict) else {}


def _push_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    studio = _studio_bucket(operator_settings)
    push = studio.get("push")
    return dict(push) if isinstance(push, dict) else {}


def web_push_configured() -> bool:
    """Return True when VAPID keys are present for Web Push."""

    return bool(settings.execution_studio_vapid_public_key and settings.execution_studio_vapid_private_key)


def get_vapid_public_key() -> str | None:
    """Public VAPID key for browser PushManager.subscribe."""

    key = (settings.execution_studio_vapid_public_key or "").strip()
    return key or None


def upsert_push_subscription(
    operator_settings: dict[str, Any] | None,
    *,
    user_id: uuid.UUID,
    subscription: dict[str, Any],
) -> dict[str, Any]:
    """Persist dashboard user push subscription under tenant execution_studio.push."""

    root = dict(operator_settings or {})
    studio = _studio_bucket(root)
    push = _push_bucket(root)
    subscriptions = list(push.get("subscriptions") or [])
    cleaned = [row for row in subscriptions if str(row.get("user_id")) != str(user_id)]
    cleaned.append(
        {
            "user_id": str(user_id),
            "subscription": subscription,
            "updated_at": datetime.now(tz=UTC).isoformat(),
        },
    )
    push["subscriptions"] = cleaned[-20:]
    studio["push"] = push
    root["execution_studio"] = studio
    return root


def clear_push_subscription(operator_settings: dict[str, Any] | None, *, user_id: uuid.UUID) -> dict[str, Any]:
    """Remove one dashboard user push subscription."""

    root = dict(operator_settings or {})
    studio = _studio_bucket(root)
    push = _push_bucket(root)
    subscriptions = [
        row for row in list(push.get("subscriptions") or []) if str(row.get("user_id")) != str(user_id)
    ]
    push["subscriptions"] = subscriptions
    studio["push"] = push
    root["execution_studio"] = studio
    return root


def user_has_push_subscription(tenant: Tenant | None, *, user_id: uuid.UUID) -> bool:
    """Return True when tenant stores a push subscription for the user."""

    if tenant is None:
        return False
    for row in list(_push_bucket(tenant.operator_settings).get("subscriptions") or []):
        if str(row.get("user_id")) == str(user_id) and isinstance(row.get("subscription"), dict):
            return True
    return False


def _webpush_subscription_gone(exc: WebPushException) -> bool:
    """Return True when push endpoint is permanently invalid (410/404)."""

    response = exc.response
    if response is None:
        return False
    status = getattr(response, "status_code", None)
    return status in {404, 410}


def remove_push_subscription_by_user_id(
    operator_settings: dict[str, Any] | None,
    *,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    """Remove one push subscription row by dashboard user id."""

    return clear_push_subscription(operator_settings, user_id=user_id)


async def send_execution_studio_web_push(
    *,
    tenant: Tenant | None,
    title: str,
    body: str,
    url: str,
    session: AsyncSession | None = None,
) -> dict[str, int]:
    """Fan out Web Push notifications to tenant operator subscriptions."""

    if tenant is None or not web_push_configured():
        return {"sent": 0, "failed": 0, "removed": 0}

    subscriptions = list(_push_bucket(tenant.operator_settings).get("subscriptions") or [])
    if not subscriptions:
        return {"sent": 0, "failed": 0, "removed": 0}

    payload = json.dumps({"title": title, "body": body, "url": url})
    sent = 0
    failed = 0
    removed = 0
    kept: list[dict[str, Any]] = []
    for row in subscriptions:
        subscription = row.get("subscription")
        if not isinstance(subscription, dict):
            failed += 1
            continue
        try:
            webpush(
                subscription_info=subscription,
                data=payload,
                vapid_private_key=settings.execution_studio_vapid_private_key,
                vapid_claims={"sub": f"mailto:{settings.execution_studio_vapid_contact_email}"},
            )
            sent += 1
            kept.append(row)
        except WebPushException as exc:
            failed += 1
            if _webpush_subscription_gone(exc):
                removed += 1
                logger.info(
                    "execution_studio.web_push_subscription_removed",
                    agent_id="reporter_bee",
                    swarm_id=str(tenant.id),
                    task_id=str(row.get("user_id") or ""),
                    reason="gone",
                )
                continue
            kept.append(row)
            logger.warning(
                "execution_studio.web_push_failed",
                agent_id="reporter_bee",
                swarm_id=str(tenant.id),
                task_id=str(row.get("user_id") or ""),
                error=str(exc)[:200],
            )

    if removed:
        push = _push_bucket(tenant.operator_settings)
        push["subscriptions"] = kept
        studio = _studio_bucket(tenant.operator_settings)
        studio["push"] = push
        root = dict(tenant.operator_settings or {})
        root["execution_studio"] = studio
        tenant.operator_settings = root
        if session is not None:
            await session.flush()

    if sent or removed:
        logger.info(
            "execution_studio.web_push_sent",
            agent_id="reporter_bee",
            swarm_id=str(tenant.id),
            task_id="pending_push",
            sent=sent,
            failed=failed,
            removed=removed,
        )
    return {"sent": sent, "failed": failed, "removed": removed}


async def mark_user_push_enabled(
    session: AsyncSession,
    *,
    user: DashboardUser,
    enabled: bool,
) -> None:
    """Track per-user push opt-in on dashboard notification prefs."""

    prefs = dict(user.notification_prefs or {})
    prefs["execution_studio_push_enabled"] = enabled
    user.notification_prefs = prefs
    await session.flush()


__all__ = [
    "clear_push_subscription",
    "get_vapid_public_key",
    "remove_push_subscription_by_user_id",
    "send_execution_studio_web_push",
    "upsert_push_subscription",
    "user_has_push_subscription",
    "web_push_configured",
]
