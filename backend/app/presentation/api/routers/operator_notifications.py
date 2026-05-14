"""Operator-friendly ``/notifications`` routes mirroring ``notification_prefs.delivery_channels``."""

from __future__ import annotations

import uuid
from typing import Any, Literal

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError

from app.presentation.api.deps import DashboardSession, DbSession
from app.presentation.api.routers import dashboard_session as dashboard_session_router
from app.core.jwt_tokens import parse_dashboard_user_subject
from app.core.logging import get_logger
from app.infrastructure.persistence.models.dashboard_user import DashboardUser

logger = get_logger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])

ChannelSlug = Literal["email", "sms", "discord", "telegram"]


class NotificationChannelPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    channel_type: ChannelSlug
    label: str | None = Field(default=None, max_length=120)
    enabled: bool = True
    settings: dict[str, Any] = Field(default_factory=dict)


def _uid(sess: dict[str, Any]) -> uuid.UUID:
    raw = sess.get("sub")
    if not isinstance(raw, str):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dashboard subject missing.")
    resolved = parse_dashboard_user_subject(raw.strip())
    if resolved is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Malformed dashboard identity.")
    return resolved


def _delivery_template(channel: ChannelSlug, raw: dict[str, Any], enabled: bool) -> Any:
    if channel == "email":
        return dashboard_session_router.EmailChannelConfig.model_validate(
            {"enabled": enabled, "address": raw.get("address")},
        )
    if channel == "sms":
        return dashboard_session_router.SmsChannelConfig.model_validate(
            {"enabled": enabled, "phone_e164": raw.get("phone_e164")},
        )
    if channel == "discord":
        return dashboard_session_router.DiscordChannelConfig.model_validate(
            {"enabled": enabled, "webhook_url": raw.get("webhook_url")},
        )
    return dashboard_session_router.TelegramChannelConfig.model_validate(
        {"enabled": enabled, "bot_token": raw.get("bot_token"), "chat_id": raw.get("chat_id")},
    )


def _flatten_channels(prefs: dict[str, Any]) -> list[dict[str, Any]]:
    dc = dashboard_session_router.normalize_delivery_channels_blob(prefs.get("delivery_channels"))
    titles = {
        "email": "Email",
        "sms": "SMS",
        "discord": "Discord",
        "telegram": "Telegram",
    }
    out: list[dict[str, Any]] = []
    for slug, title in titles.items():
        blob = dc.get(slug)
        if not isinstance(blob, dict):
            continue
        masked = dict(blob)
        for secret in ("bot_token", "webhook_url"):
            if isinstance(masked.get(secret), str):
                val = str(masked[secret])
                masked[secret] = "••••" + val[-4:] if len(val) >= 4 else "••••"
        lbl = blob.get("label") if isinstance(blob.get("label"), str) else title
        out.append(
            {
                "id": slug,
                "channel_type": slug,
                "label": lbl,
                "config_masked": masked,
                "is_active": bool(blob.get("enabled")),
            },
        )
    return out


@router.get("/", summary="List delivery channel configurations (masked)")
async def list_notification_channels(sess: DashboardSession, db: DbSession) -> dict[str, Any]:
    user = await db.get(DashboardUser, _uid(sess))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive operator.")
    prefs = dict(user.notification_prefs or {})
    return {"channels": _flatten_channels(prefs)}


async def _merge_user_channels(
    user: DashboardUser,
    db: DbSession,
    merge: dashboard_session_router.DeliveryChannelsMerge,
) -> DashboardUser:
    merged = dict(user.notification_prefs or {})
    merged["delivery_channels"] = dashboard_session_router._merge_delivery_buckets(
        merged.get("delivery_channels"),
        merge,
    )
    user.notification_prefs = merged
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/", summary="Merge a delivery channel bucket for the operator")
async def upsert_notification_channel(
    body: NotificationChannelPayload,
    sess: DashboardSession,
    db: DbSession,
) -> dict[str, Any]:
    user = await db.get(DashboardUser, _uid(sess))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive operator.")

    channel = body.channel_type
    raw = dict(body.settings)
    if body.label:
        raw.setdefault("label", body.label)
    try:
        tmpl = _delivery_template(channel, raw, body.enabled)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    merge_kwargs: dict[str, Any] = {channel: tmpl}
    merge = dashboard_session_router.DeliveryChannelsMerge.model_validate(merge_kwargs)

    try:
        await _merge_user_channels(user, db, merge)
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not persist notification channel.",
        ) from None

    return {"status": "merged", "channel": channel}


@router.delete("/{channel_id}", summary="Disable and clear a delivery channel bucket")
async def delete_notification_channel(
    channel_id: ChannelSlug,
    sess: DashboardSession,
    db: DbSession,
) -> dict[str, str]:
    """Strip credentials by merging empty disabled configs."""

    user = await db.get(DashboardUser, _uid(sess))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive operator.")

    cleared = _delivery_template(channel_id, {}, enabled=False)
    merge = dashboard_session_router.DeliveryChannelsMerge.model_validate({channel_id: cleared})
    try:
        await _merge_user_channels(user, db, merge)
    except SQLAlchemyError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Could not update notification channel.",
        ) from None

    return {"status": "cleared", "channel": channel_id}


@router.post("/test/{channel_id}", summary="Send a test ping using stored delivery settings")
async def post_notification_test(
    channel_id: ChannelSlug,
    sess: DashboardSession,
    db: DbSession,
) -> dict[str, Any]:
    user = await db.get(DashboardUser, _uid(sess))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive operator.")

    dc = dashboard_session_router.normalize_delivery_channels_blob(
        (user.notification_prefs or {}).get("delivery_channels"),
    )
    if not dc:
        return {"status": "error", "detail": "delivery_channels not configured"}

    cfg_raw = dc.get(channel_id)
    if not isinstance(cfg_raw, dict):
        return {"status": "error", "detail": f"{channel_id} channel not saved — use Save channel before testing."}

    msg = "✅ Queenswarm notification test — delivery channel is reachable."

    try:
        if channel_id == "telegram":
            token = str(cfg_raw.get("bot_token") or "").strip()
            chat_id = str(cfg_raw.get("chat_id") or "").strip()
            if not token or not chat_id:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="telegram bot_token/chat_id missing.")
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(url, json={"chat_id": chat_id, "text": msg})
            if resp.status_code >= 400:
                raise RuntimeError(resp.text)
            return {"status": "ok", "detail": "telegram"}

        if channel_id == "discord":
            hook = str(cfg_raw.get("webhook_url") or "").strip()
            if not hook:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Discord webhook missing.")
            async with httpx.AsyncClient(timeout=12.0) as client:
                resp = await client.post(hook, json={"content": msg})
            if resp.status_code >= 400:
                raise RuntimeError(resp.text)
            return {"status": "ok", "detail": "discord"}

        if channel_id == "email":
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Email channel test uses global SMTP via PATCH /auth/me/notifications + system notify-test.",
            )

        if channel_id == "sms":
            sid = str(cfg_raw.get("account_sid") or "").strip()
            tok = str(cfg_raw.get("auth_token") or "").strip()
            sender = str(cfg_raw.get("from_number") or "").strip()
            dest = str(cfg_raw.get("to_number") or "").strip()
            if not (sid and tok and sender and dest):
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="SMS Twilio fields incomplete.")
            auth = (sid, tok)
            form = {"From": sender, "To": dest, "Body": msg}
            tw_url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(tw_url, data=form, auth=auth)
            if resp.status_code >= 400:
                raise RuntimeError(resp.text)
            return {"status": "ok", "detail": "sms"}

    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "notifications.operator_test_failed",
            agent_id=str(user.id),
            swarm_id="",
            task_id="",
            channel=channel_id,
            error=str(exc),
        )
        return {"status": "error", "detail": str(exc)}

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unhandled channel.")
