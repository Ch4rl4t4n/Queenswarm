"""Slack harness trainer — append operator feedback to behavioral INSTRUCTIONS memory."""

from __future__ import annotations

import hashlib
import hmac
import re
import time
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.billing import ensure_tenant_subscription
from app.application.services.curated_memory_service import CuratedMemoryService
from app.application.services.platform_features import resolve_platform_features_for_subscription
from app.core.config import settings
from app.core.logging import get_logger
from app.core.notifications import notify_slack
from app.domain.memory.curated import CuratedFileKind
from app.infrastructure.persistence.models.tenant import Tenant

_logger = get_logger(__name__)

_SLACK_BLOCK_HEADER = re.compile(r"^## Slack feedback · ", re.MULTILINE)


class SlackHarnessTrainerDisabledError(RuntimeError):
    """Raised when the harness trainer feature flag is off."""


class SlackHarnessTrainerForbiddenError(PermissionError):
    """Raised when tenant lacks Pro tier or operator role."""


class SlackHarnessTrainerConfigError(RuntimeError):
    """Raised when Slack ingress is misconfigured."""


class SlackHarnessTrainerValidationError(ValueError):
    """Raised when feedback text fails safety or length checks."""


@dataclass(frozen=True, slots=True)
class SlackTrainerResult:
    """Outcome of one harness trainer append."""

    tenant_id: uuid.UUID
    kind: CuratedFileKind
    version: int
    char_count: int
    appended_chars: int
    source: str
    author: str | None


def verify_slack_request_signature(
    *,
    signing_secret: str,
    timestamp: str,
    body: bytes,
    signature: str,
) -> bool:
    """Validate Slack ``X-Slack-Signature`` per official signing protocol."""

    secret = signing_secret.strip()
    if not secret or not timestamp or not signature:
        return False
    try:
        ts = int(timestamp)
    except ValueError:
        return False
    if abs(time.time() - ts) > 60 * 5:
        return False
    basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
    digest = hmac.new(secret.encode("utf-8"), basestring.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(f"v0={digest}", signature)


def format_slack_feedback_block(*, feedback: str, author: str | None, source: str) -> str:
    """Render one append-only markdown block for INSTRUCTIONS curated memory."""

    stamp = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    who = author.strip() if author and author.strip() else "operator"
    lines = [f"## Slack feedback · {stamp} · {who} ({source})", ""]
    for line in feedback.strip().splitlines():
        stripped = line.strip()
        if stripped:
            lines.append(f"- {stripped}")
        else:
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def merge_instructions_append(existing: str, block: str, *, max_chars: int = 8000) -> str:
    """Append a feedback block and trim oldest Slack sections when over budget."""

    base = (existing or "").rstrip()
    merged = f"{base}\n\n{block}".strip() if base else block.strip()
    if len(merged) <= max_chars:
        return merged
    sections = _SLACK_BLOCK_HEADER.split(merged)
    if len(sections) <= 1:
        msg = f"Behavioral instructions would exceed {max_chars} characters — edit in Settings harness."
        raise SlackHarnessTrainerValidationError(msg)
    # Keep preamble (sections[0]) and drop oldest Slack blocks from the tail until within budget.
    preamble = sections[0].rstrip()
    slack_chunks = sections[1:]
    while slack_chunks and len(_rejoin_slack_sections(preamble, slack_chunks)) > max_chars:
        slack_chunks.pop(0)
    trimmed = _rejoin_slack_sections(preamble, slack_chunks)
    if len(trimmed) > max_chars:
        msg = f"Behavioral instructions would exceed {max_chars} characters — edit in Settings harness."
        raise SlackHarnessTrainerValidationError(msg)
    return trimmed


def _rejoin_slack_sections(preamble: str, slack_chunks: list[str]) -> str:
    if not slack_chunks:
        return preamble.strip()
    body = "## Slack feedback · ".join(slack_chunks)
    if preamble.strip():
        return f"{preamble.strip()}\n\n## Slack feedback · {body}".strip()
    return f"## Slack feedback · {body}".strip()


async def assert_slack_trainer_allowed(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    is_admin: bool,
) -> None:
    """Ensure deployment flag + Pro tier (or internal admin) permit trainer writes."""

    if not settings.slack_harness_trainer_enabled:
        msg = "slack_harness_trainer_enabled=false — trainer is disabled"
        raise SlackHarnessTrainerDisabledError(msg)
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        msg = f"unknown tenant_id={tenant_id}"
        raise SlackHarnessTrainerForbiddenError(msg)
    subscription = await ensure_tenant_subscription(db, tenant_id=tenant_id)
    features = resolve_platform_features_for_subscription(
        platform_mode=str(tenant.platform_mode or "internal"),
        is_admin=is_admin,
        subscription=subscription,
    )
    if not features.get("slack_harness_trainer"):
        msg = "Slack harness trainer requires Pro tier or internal operator mode."
        raise SlackHarnessTrainerForbiddenError(msg)


async def append_behavioral_feedback(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    feedback: str,
    source: str,
    author: str | None = None,
    user_id: uuid.UUID | None = None,
    is_admin: bool = False,
) -> SlackTrainerResult:
    """Append sanitized operator feedback to tenant INSTRUCTIONS curated memory."""

    await assert_slack_trainer_allowed(db, tenant_id=tenant_id, is_admin=is_admin)
    text = feedback.strip()
    if len(text) < 4:
        msg = "Feedback must be at least 4 characters."
        raise SlackHarnessTrainerValidationError(msg)
    if len(text) > 4000:
        msg = "Feedback must be at most 4000 characters."
        raise SlackHarnessTrainerValidationError(msg)

    service = CuratedMemoryService(db=db)
    current = await service.get(tenant_id, CuratedFileKind.INSTRUCTIONS)
    existing = current.content_md if current is not None else ""
    block = format_slack_feedback_block(feedback=text, author=author, source=source)
    merged = merge_instructions_append(existing, block)
    out = await service.upsert(
        tenant_id=tenant_id,
        kind=CuratedFileKind.INSTRUCTIONS,
        content_md=merged,
        user_id=user_id,
    )
    _logger.info(
        "slack_harness_trainer.appended",
        agent_id="slack_harness_trainer",
        swarm_id=str(tenant_id),
        task_id=source,
        char_count=out.char_count,
        version=out.version,
    )
    return SlackTrainerResult(
        tenant_id=tenant_id,
        kind=CuratedFileKind.INSTRUCTIONS,
        version=out.version,
        char_count=out.char_count,
        appended_chars=len(block),
        source=source,
        author=author,
    )


async def resolve_slack_trainer_tenant_id(db: AsyncSession) -> uuid.UUID:
    """Load configured tenant anchor for unsigned Slack slash commands."""

    raw = settings.slack_harness_trainer_tenant_id
    if raw is None or not str(raw).strip():
        msg = "SLACK_HARNESS_TRAINER_TENANT_ID is not configured."
        raise SlackHarnessTrainerConfigError(msg)
    try:
        tenant_uuid = uuid.UUID(str(raw).strip())
    except ValueError as exc:
        msg = "SLACK_HARNESS_TRAINER_TENANT_ID is not a valid UUID."
        raise SlackHarnessTrainerConfigError(msg) from exc
    tenant = await db.get(Tenant, tenant_uuid)
    if tenant is None:
        msg = f"SLACK_HARNESS_TRAINER_TENANT_ID={tenant_uuid} does not match a tenant row."
        raise SlackHarnessTrainerConfigError(msg)
    return tenant_uuid


def slack_trainer_status() -> dict[str, Any]:
    """Non-secret deployment status for harness dashboard."""

    signing = (settings.slack_harness_trainer_signing_secret or "").strip()
    tenant_raw = settings.slack_harness_trainer_tenant_id
    tenant_configured = bool(tenant_raw and str(tenant_raw).strip())
    return {
        "enabled": settings.slack_harness_trainer_enabled,
        "signing_secret_configured": bool(signing),
        "tenant_id_configured": tenant_configured,
        "tenant_id": str(tenant_raw).strip() if tenant_configured else None,
        "slash_command_path": "/api/v1/harness/slack-trainer/slack-command",
        "dashboard_feedback_path": "/api/v1/harness/slack-trainer/feedback",
    }


async def notify_trainer_confirmation(*, feedback_preview: str, author: str | None) -> bool:
    """Best-effort Slack confirmation via outgoing webhook."""

    who = author or "operator"
    preview = feedback_preview.strip().replace("\n", " ")[:240]
    return await notify_slack(
        message=f"Harness trainer saved feedback from *{who}*:\n>{preview}",
        color="#00FF88",
        title="Behavioral memory updated",
    )


__all__ = [
    "SlackHarnessTrainerConfigError",
    "SlackHarnessTrainerDisabledError",
    "SlackHarnessTrainerForbiddenError",
    "SlackHarnessTrainerValidationError",
    "SlackTrainerResult",
    "append_behavioral_feedback",
    "format_slack_feedback_block",
    "merge_instructions_append",
    "notify_trainer_confirmation",
    "resolve_slack_trainer_tenant_id",
    "slack_trainer_status",
    "verify_slack_request_signature",
]
