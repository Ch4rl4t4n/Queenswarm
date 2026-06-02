"""HMAC/token webhook ingress for event-driven supervisor routines (Automation Ladder L4)."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.persistence.models.supervisor_routine import SupervisorRoutine

logger = structlog.get_logger(__name__)

WEBHOOK_CONTEXT_KEY = "webhook_ingress"


def _hash_token(token: str) -> str:
    """Return stable SHA-256 hex digest for webhook bearer tokens."""

    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def build_routine_webhook_url(*, routine_id: uuid.UUID) -> str:
    """Public webhook URL for one routine (domain from settings)."""

    domain = (settings.domain or "queenswarm.love").strip().rstrip("/")
    return f"https://{domain}/api/v1/agents/routines/{routine_id}/webhook"


def webhook_config_from_payload(context_payload: dict[str, Any] | None) -> dict[str, Any]:
    """Extract webhook ingress metadata from routine context_payload."""

    raw = dict(context_payload or {}).get(WEBHOOK_CONTEXT_KEY)
    return dict(raw) if isinstance(raw, dict) else {}


def enable_routine_webhook(*, context_payload: dict[str, Any] | None) -> tuple[str, dict[str, Any]]:
    """Generate a new webhook token and persist hash in context_payload."""

    token = secrets.token_urlsafe(32)
    payload = dict(context_payload or {})
    payload[WEBHOOK_CONTEXT_KEY] = {
        "enabled": True,
        "token_hash": _hash_token(token),
        "created_at": datetime.now(tz=UTC).isoformat(),
        "last_received_at": None,
        "trigger_count": int(webhook_config_from_payload(payload).get("trigger_count") or 0),
    }
    return token, payload


def disable_routine_webhook(*, context_payload: dict[str, Any] | None) -> dict[str, Any]:
    """Remove webhook ingress configuration from routine payload."""

    payload = dict(context_payload or {})
    payload.pop(WEBHOOK_CONTEXT_KEY, None)
    return payload


def verify_routine_webhook_token(*, context_payload: dict[str, Any] | None, token: str) -> bool:
    """Constant-time compare of bearer token against stored hash."""

    cfg = webhook_config_from_payload(context_payload)
    if not cfg.get("enabled"):
        return False
    expected = str(cfg.get("token_hash") or "")
    if not expected or not token:
        return False
    return hmac.compare_digest(_hash_token(token.strip()), expected)


def extract_webhook_event_text(body: dict[str, Any]) -> str:
    """Normalize inbound webhook JSON to operator event text (Claude routines shape)."""

    if not body:
        return ""
    text = body.get("text")
    if isinstance(text, str) and text.strip():
        return text.strip()[:8000]
    message = body.get("message")
    if isinstance(message, str) and message.strip():
        return message.strip()[:8000]
    payload = body.get("payload")
    if isinstance(payload, str) and payload.strip():
        return payload.strip()[:8000]
    if isinstance(payload, dict) and payload:
        return json.dumps(payload, ensure_ascii=False)[:8000]
    return json.dumps(body, ensure_ascii=False)[:8000]


def record_webhook_received(*, context_payload: dict[str, Any], source: str) -> dict[str, Any]:
    """Bump webhook telemetry after successful ingress."""

    payload = dict(context_payload or {})
    cfg = dict(webhook_config_from_payload(payload))
    cfg["last_received_at"] = datetime.now(tz=UTC).isoformat()
    cfg["last_source"] = source[:120]
    cfg["trigger_count"] = int(cfg.get("trigger_count") or 0) + 1
    payload[WEBHOOK_CONTEXT_KEY] = cfg
    return payload


async def handle_routine_webhook(
    db: AsyncSession,
    *,
    routine: SupervisorRoutine,
    body: dict[str, Any],
    source_header: str | None,
) -> uuid.UUID:
    """Validate webhook-enabled routine and spawn session with event context."""

    from app.application.services.supervisor.routine_service import trigger_supervisor_routine_now

    cfg = webhook_config_from_payload(dict(routine.context_payload or {}))
    if not cfg.get("enabled"):
        msg = "Webhook ingress is not enabled for this routine."
        raise ValueError(msg)

    event_text = extract_webhook_event_text(body)
    source = (source_header or str(body.get("source") or "webhook")).strip()[:120]
    session_id = await trigger_supervisor_routine_now(
        db,
        routine=routine,
        event_text=event_text,
        trigger_source=f"webhook:{source}",
    )
    routine.context_payload = record_webhook_received(
        context_payload=dict(routine.context_payload or {}),
        source=source,
    )
    await db.flush()
    logger.info(
        "routine_webhook.triggered",
        agent_id="routine_webhook_bee",
        swarm_id=str(routine.tenant_id or ""),
        task_id=str(routine.id),
        session_id=str(session_id),
        source=source,
    )
    return session_id


__all__ = [
    "WEBHOOK_CONTEXT_KEY",
    "build_routine_webhook_url",
    "disable_routine_webhook",
    "enable_routine_webhook",
    "extract_webhook_event_text",
    "handle_routine_webhook",
    "verify_routine_webhook_token",
    "webhook_config_from_payload",
]
