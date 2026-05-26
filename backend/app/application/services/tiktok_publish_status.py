"""TikTok publish status polling — follow-up after video_publish_init."""

from __future__ import annotations

import asyncio
import json
import uuid
from typing import Any, Literal

import structlog
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.execution_studio import execute_studio_tool
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant

logger = structlog.get_logger(__name__)

TikTokPublishStatus = Literal["simulated", "processing", "published", "failed", "timeout", "skipped"]

_TERMINAL_STATUSES = frozenset(
    {
        "PUBLISH_COMPLETE",
        "PUBLISHED",
        "SUCCESS",
        "FAILED",
        "PUBLISH_FAILED",
    },
)
_SUCCESS_STATUSES = frozenset({"PUBLISH_COMPLETE", "PUBLISHED", "SUCCESS"})


class TikTokPublishStatusOut(BaseModel):
    """Result of optional publish_status_fetch polling."""

    model_config = ConfigDict(extra="ignore")

    enabled: bool = False
    publish_id: str | None = None
    status: TikTokPublishStatus = "skipped"
    attempts: int = 0
    raw_status: str | None = None
    message: str = ""


def extract_tiktok_publish_id(upstream: dict[str, Any] | None) -> str | None:
    """Parse publish_id from video_publish_init upstream payload."""

    if not upstream:
        return None
    simulated = upstream.get("simulated_result")
    if isinstance(simulated, dict):
        pid = simulated.get("publish_id") or simulated.get("data", {}).get("publish_id")
        if pid:
            return str(pid).strip() or None
    raw = upstream.get("result")
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        payload = json.loads(text) if text.startswith("{") else None
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        if isinstance(data, dict):
            pid = data.get("publish_id") or data.get("publishId")
            if pid:
                return str(pid).strip() or None
    if "publish_id" in text:
        for token in text.replace('"', " ").split():
            if len(token) > 8 and token.isalnum():
                return token
    return None


def _parse_status_text(raw: str) -> str | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        payload = json.loads(text) if text.startswith("{") else None
    except json.JSONDecodeError:
        payload = None
    if isinstance(payload, dict):
        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
        if isinstance(data, dict):
            status = data.get("status") or data.get("publish_status")
            if status:
                return str(status).strip().upper()
    upper = text.upper()
    for candidate in _TERMINAL_STATUSES | {"PROCESSING", "PROCESSING_UPLOAD"}:
        if candidate in upper:
            return candidate
    return None


async def poll_tiktok_publish_status(
    session: AsyncSession,
    *,
    dashboard_user_id: uuid.UUID,
    tenant: Tenant | None,
    publish_id: str,
    mode: str,
    operator_confirmed: bool,
) -> TikTokPublishStatusOut:
    """Poll TikTok publish_status_fetch until terminal state or timeout."""

    if not settings.tiktok_publish_status_poll_enabled:
        return TikTokPublishStatusOut(
            enabled=False,
            publish_id=publish_id,
            status="skipped",
            message="TikTok status poll disabled.",
        )

    if mode == "simulate":
        return TikTokPublishStatusOut(
            enabled=True,
            publish_id=publish_id,
            status="simulated",
            attempts=0,
            raw_status="SIMULATED",
            message="Simulate mode — status poll skipped (dry-run init).",
        )

    max_attempts = int(settings.tiktok_publish_status_poll_max_attempts)
    interval = float(settings.tiktok_publish_status_poll_interval_sec)
    last_raw: str | None = None

    for attempt in range(1, max_attempts + 1):
        upstream = await execute_studio_tool(
            session,
            dashboard_user_id=dashboard_user_id,
            tenant=tenant,
            connector_slug="tiktok_content",
            tool_name="publish_status_fetch",
            arguments={"publish_id": publish_id},
            mode="live",
            operator_confirmed=operator_confirmed,
        )
        if not upstream.get("ok"):
            logger.warning(
                "tiktok_publish.status_poll_error",
                agent_id="tiktok_publish",
                task_id=publish_id,
                attempt=attempt,
            )
            if attempt >= max_attempts:
                return TikTokPublishStatusOut(
                    enabled=True,
                    publish_id=publish_id,
                    status="failed",
                    attempts=attempt,
                    message="Status poll upstream error.",
                )
            await asyncio.sleep(interval)
            continue

        last_raw = str(upstream.get("result") or "")
        parsed = _parse_status_text(last_raw)
        if parsed in _SUCCESS_STATUSES:
            return TikTokPublishStatusOut(
                enabled=True,
                publish_id=publish_id,
                status="published",
                attempts=attempt,
                raw_status=parsed,
                message="TikTok video publish complete.",
            )
        if parsed in {"FAILED", "PUBLISH_FAILED"}:
            return TikTokPublishStatusOut(
                enabled=True,
                publish_id=publish_id,
                status="failed",
                attempts=attempt,
                raw_status=parsed,
                message="TikTok reported publish failure.",
            )
        if attempt >= max_attempts:
            break
        await asyncio.sleep(interval)

    return TikTokPublishStatusOut(
        enabled=True,
        publish_id=publish_id,
        status="timeout",
        attempts=max_attempts,
        raw_status=last_raw[:120] if last_raw else None,
        message=f"Status still processing after {max_attempts} poll(s).",
    )


__all__ = [
    "TikTokPublishStatusOut",
    "extract_tiktok_publish_id",
    "poll_tiktok_publish_status",
]
