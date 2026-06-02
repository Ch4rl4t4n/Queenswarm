"""Per-tenant session guardrails stored on Tenant.operator_settings."""

from __future__ import annotations

import uuid
from typing import Any, Literal

from app.core.config import settings
from app.core.redis_client import get_json, set_json
from app.infrastructure.persistence.models.tenant import Tenant

SESSION_POLICY_KEY = "session_policy"
RATE_LIMIT_CACHE_PREFIX = "queenswarm:session_policy:rate:"
RATE_LIMIT_CACHE_TTL_SEC = 300
PolicySource = Literal["deployment", "tenant"]

ACCESS_MINUTES_MIN = 5
ACCESS_MINUTES_MAX = 480
REFRESH_DAYS_MIN = 1
REFRESH_DAYS_MAX = 365
RATE_REQUESTS_MIN = 10
RATE_REQUESTS_MAX = 10_000
OAUTH_TTL_MIN = 60
OAUTH_TTL_MAX = 7200
TWO_FA_SESSION_HOURS_MIN = 0
TWO_FA_SESSION_HOURS_MAX = 720


def _policy_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    bucket = root.get(SESSION_POLICY_KEY)
    return dict(bucket) if isinstance(bucket, dict) else {}


def _deployment_rate_limit() -> tuple[bool, int, float]:
    user_limits_active = settings.rate_limit_user_enabled or settings.production_security_mode
    if user_limits_active:
        return (
            bool(settings.rate_limit_enabled),
            int(settings.rate_limit_user_sustain_max),
            float(settings.rate_limit_user_sustain_window_sec),
        )
    return (
        bool(settings.rate_limit_enabled),
        int(settings.rate_limit_sustain_max),
        float(settings.rate_limit_sustain_window_sec),
    )


def _field_source(bucket: dict[str, Any], field: str) -> PolicySource:
    raw = bucket.get(f"{field}_source")
    return "tenant" if raw == "tenant" else "deployment"


def _clamp_int(value: int, *, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, int(value)))


def get_stored_session_policy_config(tenant: Tenant | None) -> dict[str, Any]:
    """Return raw tenant session policy bucket."""

    if tenant is None:
        return {}
    return _policy_bucket(tenant.operator_settings)


def resolve_effective_session_policy(tenant: Tenant | None) -> dict[str, Any]:
    """Merge deployment defaults with optional tenant overrides."""

    bucket = get_stored_session_policy_config(tenant)
    dep_rate_enabled, dep_rate_requests, dep_rate_window = _deployment_rate_limit()

    access_minutes = settings.access_token_expire_minutes
    if _field_source(bucket, "access_token") == "tenant" and bucket.get("access_token_minutes") is not None:
        access_minutes = _clamp_int(
            int(bucket["access_token_minutes"]),
            minimum=ACCESS_MINUTES_MIN,
            maximum=ACCESS_MINUTES_MAX,
        )

    refresh_days = settings.refresh_token_expire_days
    if _field_source(bucket, "refresh_token") == "tenant" and bucket.get("refresh_token_days") is not None:
        refresh_days = _clamp_int(
            int(bucket["refresh_token_days"]),
            minimum=REFRESH_DAYS_MIN,
            maximum=REFRESH_DAYS_MAX,
        )

    rate_enabled = dep_rate_enabled
    rate_requests = dep_rate_requests
    rate_window = dep_rate_window
    if _field_source(bucket, "rate_limit") == "tenant":
        if bucket.get("rate_limit_enabled") is not None:
            rate_enabled = bool(bucket["rate_limit_enabled"])
        if bucket.get("rate_limit_requests") is not None:
            rate_requests = _clamp_int(
                int(bucket["rate_limit_requests"]),
                minimum=RATE_REQUESTS_MIN,
                maximum=RATE_REQUESTS_MAX,
            )
        if bucket.get("rate_limit_window_sec") is not None:
            rate_window = max(1.0, float(bucket["rate_limit_window_sec"]))

    oauth_enabled = True
    oauth_ttl = settings.oauth_state_ttl_sec
    if _field_source(bucket, "oauth_pkce") == "tenant":
        if bucket.get("oauth_pkce_enabled") is not None:
            oauth_enabled = bool(bucket["oauth_pkce_enabled"])
        if bucket.get("oauth_state_ttl_sec") is not None:
            oauth_ttl = _clamp_int(
                int(bucket["oauth_state_ttl_sec"]),
                minimum=OAUTH_TTL_MIN,
                maximum=OAUTH_TTL_MAX,
            )

    two_fa_session_hours = settings.dashboard_2fa_session_max_hours
    if (
        _field_source(bucket, "dashboard_2fa_session") == "tenant"
        and bucket.get("dashboard_2fa_session_max_hours") is not None
    ):
        two_fa_session_hours = _clamp_int(
            int(bucket["dashboard_2fa_session_max_hours"]),
            minimum=TWO_FA_SESSION_HOURS_MIN,
            maximum=TWO_FA_SESSION_HOURS_MAX,
        )

    return {
        "access_token_expire_minutes": access_minutes,
        "refresh_token_expire_days": refresh_days,
        "dashboard_2fa_session_max_hours": two_fa_session_hours,
        "rate_limit_enabled": rate_enabled,
        "rate_limit_requests": rate_requests,
        "rate_limit_window_sec": rate_window,
        "oauth_pkce_enabled": oauth_enabled,
        "oauth_state_ttl_sec": oauth_ttl,
        "production_security_mode": settings.production_security_mode,
        "two_fa_enabled": bool(settings.enable_2fa or settings.security_2fa_advanced_enabled),
    }


def merge_tenant_session_policy_patch(
    tenant: Tenant,
    *,
    access_token_source: PolicySource | None = None,
    access_token_minutes: int | None = None,
    refresh_token_source: PolicySource | None = None,
    refresh_token_days: int | None = None,
    rate_limit_source: PolicySource | None = None,
    rate_limit_enabled: bool | None = None,
    rate_limit_requests: int | None = None,
    rate_limit_window_sec: float | None = None,
    oauth_pkce_source: PolicySource | None = None,
    oauth_pkce_enabled: bool | None = None,
    oauth_state_ttl_sec: int | None = None,
    dashboard_2fa_session_source: PolicySource | None = None,
    dashboard_2fa_session_max_hours: int | None = None,
) -> dict[str, Any]:
    """Apply partial session policy patch and return updated operator_settings root."""

    root = dict(tenant.operator_settings or {})
    bucket = _policy_bucket(root)

    if access_token_source is not None:
        bucket["access_token_source"] = access_token_source
    if access_token_minutes is not None:
        bucket["access_token_minutes"] = _clamp_int(
            access_token_minutes,
            minimum=ACCESS_MINUTES_MIN,
            maximum=ACCESS_MINUTES_MAX,
        )
    if refresh_token_source is not None:
        bucket["refresh_token_source"] = refresh_token_source
    if refresh_token_days is not None:
        bucket["refresh_token_days"] = _clamp_int(
            refresh_token_days,
            minimum=REFRESH_DAYS_MIN,
            maximum=REFRESH_DAYS_MAX,
        )
    if rate_limit_source is not None:
        bucket["rate_limit_source"] = rate_limit_source
    if rate_limit_enabled is not None:
        bucket["rate_limit_enabled"] = rate_limit_enabled
    if rate_limit_requests is not None:
        bucket["rate_limit_requests"] = _clamp_int(
            rate_limit_requests,
            minimum=RATE_REQUESTS_MIN,
            maximum=RATE_REQUESTS_MAX,
        )
    if rate_limit_window_sec is not None:
        bucket["rate_limit_window_sec"] = max(1.0, float(rate_limit_window_sec))
    if oauth_pkce_source is not None:
        bucket["oauth_pkce_source"] = oauth_pkce_source
    if oauth_pkce_enabled is not None:
        bucket["oauth_pkce_enabled"] = oauth_pkce_enabled
    if oauth_state_ttl_sec is not None:
        bucket["oauth_state_ttl_sec"] = _clamp_int(
            oauth_state_ttl_sec,
            minimum=OAUTH_TTL_MIN,
            maximum=OAUTH_TTL_MAX,
        )
    if dashboard_2fa_session_source is not None:
        bucket["dashboard_2fa_session_source"] = dashboard_2fa_session_source
    if dashboard_2fa_session_max_hours is not None:
        bucket["dashboard_2fa_session_max_hours"] = _clamp_int(
            dashboard_2fa_session_max_hours,
            minimum=TWO_FA_SESSION_HOURS_MIN,
            maximum=TWO_FA_SESSION_HOURS_MAX,
        )

    root[SESSION_POLICY_KEY] = bucket
    return root


def serialize_session_policy_view(tenant: Tenant | None, *, editable: bool) -> dict[str, Any]:
    """Build API view with effective values and per-field source controls."""

    bucket = get_stored_session_policy_config(tenant)
    effective = resolve_effective_session_policy(tenant)
    dep_rate_enabled, dep_rate_requests, dep_rate_window = _deployment_rate_limit()

    return {
        **effective,
        "access_token_source": _field_source(bucket, "access_token"),
        "access_token_minutes_custom": bucket.get("access_token_minutes"),
        "access_token_minutes_deployment": settings.access_token_expire_minutes,
        "refresh_token_source": _field_source(bucket, "refresh_token"),
        "refresh_token_days_custom": bucket.get("refresh_token_days"),
        "refresh_token_days_deployment": settings.refresh_token_expire_days,
        "rate_limit_source": _field_source(bucket, "rate_limit"),
        "rate_limit_enabled_custom": bucket.get("rate_limit_enabled"),
        "rate_limit_requests_custom": bucket.get("rate_limit_requests"),
        "rate_limit_window_sec_custom": bucket.get("rate_limit_window_sec"),
        "rate_limit_enabled_deployment": dep_rate_enabled,
        "rate_limit_requests_deployment": dep_rate_requests,
        "rate_limit_window_sec_deployment": dep_rate_window,
        "oauth_pkce_source": _field_source(bucket, "oauth_pkce"),
        "oauth_pkce_enabled_custom": bucket.get("oauth_pkce_enabled"),
        "oauth_state_ttl_sec_custom": bucket.get("oauth_state_ttl_sec"),
        "oauth_pkce_enabled_deployment": True,
        "oauth_state_ttl_sec_deployment": settings.oauth_state_ttl_sec,
        "dashboard_2fa_session_source": _field_source(bucket, "dashboard_2fa_session"),
        "dashboard_2fa_session_max_hours_custom": bucket.get("dashboard_2fa_session_max_hours"),
        "dashboard_2fa_session_max_hours_deployment": settings.dashboard_2fa_session_max_hours,
        "editable": editable,
    }


async def cache_tenant_rate_limits(tenant_id: uuid.UUID, *, tenant: Tenant | None = None) -> None:
    """Write effective tenant rate limits to Redis for middleware fast-path."""

    subject = tenant
    if subject is None:
        return
    effective = resolve_effective_session_policy(subject)
    await set_json(
        f"{RATE_LIMIT_CACHE_PREFIX}{tenant_id}",
        {
            "enabled": bool(effective["rate_limit_enabled"]),
            "requests": int(effective["rate_limit_requests"]),
            "window_sec": float(effective["rate_limit_window_sec"]),
        },
        ttl=RATE_LIMIT_CACHE_TTL_SEC,
    )


async def read_cached_tenant_rate_limits(tenant_id: str) -> tuple[bool, int, float] | None:
    """Return cached tenant rate limits when present."""

    try:
        parsed = uuid.UUID(tenant_id.strip())
    except ValueError:
        return None
    blob = await get_json(f"{RATE_LIMIT_CACHE_PREFIX}{parsed}")
    if not isinstance(blob, dict):
        return None
    try:
        return (
            bool(blob.get("enabled")),
            int(blob["requests"]),
            float(blob["window_sec"]),
        )
    except (KeyError, TypeError, ValueError):
        return None


__all__ = [
    "SESSION_POLICY_KEY",
    "RATE_LIMIT_CACHE_PREFIX",
    "cache_tenant_rate_limits",
    "merge_tenant_session_policy_patch",
    "read_cached_tenant_rate_limits",
    "resolve_effective_session_policy",
    "serialize_session_policy_view",
]
