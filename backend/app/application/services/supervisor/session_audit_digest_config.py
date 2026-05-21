"""Per-tenant supervisor audit digest configuration stored on Tenant.operator_settings."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant

AUDIT_DIGEST_CONFIG_KEY = "supervisor_audit_digest"
DEFAULT_SCHEDULE_HOUR_UTC = 7
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _digest_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    """Return the nested supervisor audit digest config bucket."""

    root = dict(operator_settings or {})
    bucket = root.get(AUDIT_DIGEST_CONFIG_KEY)
    return dict(bucket) if isinstance(bucket, dict) else {}


def normalize_extra_recipients(raw: object) -> list[str]:
    """Normalize and dedupe extra digest recipient emails."""

    if not isinstance(raw, list):
        return []
    cleaned: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        email = item.strip().lower()
        if not email or not _EMAIL_RE.match(email):
            continue
        if email not in cleaned:
            cleaned.append(email)
    return cleaned


def get_tenant_audit_digest_config(tenant: Tenant) -> dict[str, Any]:
    """Return stored tenant digest config with normalized fields."""

    bucket = _digest_bucket(tenant.operator_settings)
    return {
        "enabled": bucket.get("enabled"),
        "window_hours": bucket.get("window_hours"),
        "schedule_hour_utc": bucket.get("schedule_hour_utc"),
        "extra_recipients": normalize_extra_recipients(bucket.get("extra_recipients")),
        "slack_webhook_url": (
            bucket.get("slack_webhook_url").strip()
            if isinstance(bucket.get("slack_webhook_url"), str) and bucket.get("slack_webhook_url").strip()
            else None
        ),
        "discord_webhook_url": (
            bucket.get("discord_webhook_url").strip()
            if isinstance(bucket.get("discord_webhook_url"), str) and bucket.get("discord_webhook_url").strip()
            else None
        ),
        "teams_webhook_url": (
            bucket.get("teams_webhook_url").strip()
            if isinstance(bucket.get("teams_webhook_url"), str) and bucket.get("teams_webhook_url").strip()
            else None
        ),
        "last_sent_at": bucket.get("last_sent_at"),
    }


def effective_digest_enabled(*, tenant: Tenant, global_enabled: bool | None = None) -> bool:
    """Resolve whether scheduled digests are enabled for one tenant."""

    enabled_global = settings.supervisor_audit_digest_enabled if global_enabled is None else global_enabled
    stored = get_tenant_audit_digest_config(tenant).get("enabled")
    if stored is False:
        return False
    if stored is True:
        return enabled_global
    return enabled_global


def effective_digest_window_hours(tenant: Tenant) -> int:
    """Resolve digest window hours with tenant override."""

    stored = get_tenant_audit_digest_config(tenant).get("window_hours")
    if isinstance(stored, int) and 1 <= stored <= 168:
        return stored
    return settings.supervisor_audit_digest_window_hours


def effective_digest_schedule_hour_utc(tenant: Tenant) -> int:
    """Resolve UTC hour when scheduled digests should fire for one tenant."""

    stored = get_tenant_audit_digest_config(tenant).get("schedule_hour_utc")
    if isinstance(stored, int) and 0 <= stored <= 23:
        return stored
    return DEFAULT_SCHEDULE_HOUR_UTC


def _parse_last_sent_at(raw: object) -> datetime | None:
    """Parse ISO timestamp stored in tenant digest config."""

    if not isinstance(raw, str) or not raw.strip():
        return None
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def is_tenant_digest_due(*, tenant: Tenant, now: datetime) -> bool:
    """Return True when a tenant is due for its scheduled digest at ``now``."""

    if not effective_digest_enabled(tenant=tenant):
        return False
    if now.astimezone(UTC).hour != effective_digest_schedule_hour_utc(tenant):
        return False
    last_sent = _parse_last_sent_at(get_tenant_audit_digest_config(tenant).get("last_sent_at"))
    if last_sent is not None and last_sent.date() == now.astimezone(UTC).date():
        return False
    return True


def merge_tenant_audit_digest_patch(
    tenant: Tenant,
    *,
    enabled: bool | None = None,
    window_hours: int | None = None,
    schedule_hour_utc: int | None = None,
    extra_recipients: list[str] | None = None,
    slack_webhook_url: str | None = None,
    clear_slack_webhook: bool = False,
    discord_webhook_url: str | None = None,
    clear_discord_webhook: bool = False,
    teams_webhook_url: str | None = None,
    clear_teams_webhook: bool = False,
) -> dict[str, Any]:
    """Apply a partial patch to tenant.operator_settings and return updated root."""

    root = dict(tenant.operator_settings or {})
    bucket = _digest_bucket(root)

    if enabled is not None:
        bucket["enabled"] = enabled
    if window_hours is not None:
        bucket["window_hours"] = window_hours
    if schedule_hour_utc is not None:
        bucket["schedule_hour_utc"] = schedule_hour_utc
    if extra_recipients is not None:
        bucket["extra_recipients"] = normalize_extra_recipients(extra_recipients)
    if clear_slack_webhook:
        bucket.pop("slack_webhook_url", None)
    elif slack_webhook_url is not None:
        trimmed = slack_webhook_url.strip()
        if trimmed:
            bucket["slack_webhook_url"] = trimmed
        else:
            bucket.pop("slack_webhook_url", None)
    if clear_discord_webhook:
        bucket.pop("discord_webhook_url", None)
    elif discord_webhook_url is not None:
        trimmed = discord_webhook_url.strip()
        if trimmed:
            bucket["discord_webhook_url"] = trimmed
        else:
            bucket.pop("discord_webhook_url", None)
    if clear_teams_webhook:
        bucket.pop("teams_webhook_url", None)
    elif teams_webhook_url is not None:
        trimmed = teams_webhook_url.strip()
        if trimmed:
            bucket["teams_webhook_url"] = trimmed
        else:
            bucket.pop("teams_webhook_url", None)

    root[AUDIT_DIGEST_CONFIG_KEY] = bucket
    return root


def classify_tenant_digest_health(
    *,
    tenant: Tenant,
    digest_enabled: bool,
    now: datetime | None = None,
) -> str:
    """Classify tenant digest delivery health for operator rollup dashboards.

    Returns one of: ``healthy``, ``stale``, ``never_sent``, ``disabled``.
    """

    if not digest_enabled:
        return "disabled"
    last_sent = _parse_last_sent_at(get_tenant_audit_digest_config(tenant).get("last_sent_at"))
    if last_sent is None:
        return "never_sent"
    moment = now or datetime.now(tz=UTC)
    window = effective_digest_window_hours(tenant)
    stale_after_hours = min(max(window + 24, 48), 168)
    age_hours = (moment - last_sent).total_seconds() / 3600
    if age_hours > stale_after_hours:
        return "stale"
    return "healthy"


async def mark_tenant_digest_sent(db: AsyncSession, *, tenant: Tenant, sent_at: datetime) -> None:
    """Persist last_sent_at for scheduled digest deduplication."""

    root = dict(tenant.operator_settings or {})
    bucket = _digest_bucket(root)
    bucket["last_sent_at"] = sent_at.astimezone(UTC).isoformat()
    root[AUDIT_DIGEST_CONFIG_KEY] = bucket
    tenant.operator_settings = root
    await db.flush()


def serialize_audit_digest_config_view(tenant: Tenant) -> dict[str, Any]:
    """Build API view with effective values and stored overrides."""

    stored = get_tenant_audit_digest_config(tenant)
    slack_webhook = stored.get("slack_webhook_url")
    discord_webhook = stored.get("discord_webhook_url")
    teams_webhook = stored.get("teams_webhook_url")
    return {
        "enabled": effective_digest_enabled(tenant=tenant),
        "enabled_override": stored.get("enabled"),
        "window_hours": effective_digest_window_hours(tenant),
        "window_hours_override": stored.get("window_hours"),
        "schedule_hour_utc": effective_digest_schedule_hour_utc(tenant),
        "schedule_hour_override": stored.get("schedule_hour_utc"),
        "extra_recipients": list(stored.get("extra_recipients") or []),
        "slack_webhook_configured": bool(slack_webhook),
        "slack_webhook_preview": _mask_webhook(slack_webhook) if slack_webhook else None,
        "discord_webhook_configured": bool(discord_webhook),
        "discord_webhook_preview": _mask_webhook(discord_webhook) if discord_webhook else None,
        "teams_webhook_configured": bool(teams_webhook),
        "teams_webhook_preview": _mask_webhook(teams_webhook) if teams_webhook else None,
        "last_sent_at": stored.get("last_sent_at"),
        "global_enabled": settings.supervisor_audit_digest_enabled,
        "global_window_hours": settings.supervisor_audit_digest_window_hours,
        "global_schedule_hour_utc": DEFAULT_SCHEDULE_HOUR_UTC,
    }


def _mask_webhook(url: str) -> str:
    """Return a masked webhook URL safe for API responses."""

    if len(url) <= 24:
        return "…"
    return f"{url[:20]}…{url[-4:]}"


__all__ = [
    "AUDIT_DIGEST_CONFIG_KEY",
    "DEFAULT_SCHEDULE_HOUR_UTC",
    "classify_tenant_digest_health",
    "effective_digest_enabled",
    "effective_digest_schedule_hour_utc",
    "effective_digest_window_hours",
    "get_tenant_audit_digest_config",
    "is_tenant_digest_due",
    "mark_tenant_digest_sent",
    "merge_tenant_audit_digest_patch",
    "normalize_extra_recipients",
    "serialize_audit_digest_config_view",
]
