"""White-label branding and enterprise compliance workspace on Tenant.operator_settings."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.dr_drill_evidence import load_latest_dr_drill_evidence
from app.application.services.ha_chaos_evidence import load_latest_ha_chaos_evidence
from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant, TenantAuditLog

WHITE_LABEL_KEY = "white_label"
COMPLIANCE_KEY = "enterprise_compliance"
_DEFAULT_ACCENT = "#FFB800"
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def enterprise_workspace_enabled() -> bool:
    """Return whether enterprise workspace surfaces are active."""

    return bool(settings.enterprise_workspace_enabled)


def _bucket(operator_settings: dict[str, Any] | None, key: str) -> dict[str, Any]:
    root = dict(operator_settings or {})
    nested = root.get(key)
    return dict(nested) if isinstance(nested, dict) else {}


def _normalize_https_url(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    value = raw.strip()
    if not value:
        return None
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        return None
    return value


def _normalize_email(raw: object) -> str | None:
    if not isinstance(raw, str):
        return None
    email = raw.strip().lower()
    if not email or not _EMAIL_RE.match(email):
        return None
    return email


def get_white_label_config(tenant: Tenant) -> dict[str, Any]:
    """Return stored white-label bucket with defaults."""

    bucket = _bucket(tenant.operator_settings, WHITE_LABEL_KEY)
    accent = bucket.get("accent_hex")
    accent_hex = accent if isinstance(accent, str) and re.fullmatch(r"#[0-9A-Fa-f]{6}", accent) else _DEFAULT_ACCENT
    domain = bucket.get("custom_domain")
    custom_domain = domain.strip().lower() if isinstance(domain, str) and domain.strip() else None
    return {
        "brand_name": bucket.get("brand_name") if isinstance(bucket.get("brand_name"), str) else None,
        "logo_url": _normalize_https_url(bucket.get("logo_url")),
        "accent_hex": accent_hex,
        "hide_platform_branding": bucket.get("hide_platform_branding") is True,
        "custom_domain": custom_domain,
        "custom_domain_status": "verified" if bucket.get("custom_domain_verified") is True else "pending",
    }


def get_compliance_config(tenant: Tenant) -> dict[str, Any]:
    """Return stored enterprise compliance bucket with defaults."""

    bucket = _bucket(tenant.operator_settings, COMPLIANCE_KEY)
    retention = bucket.get("data_retention_days")
    try:
        days = int(retention) if retention is not None else 365
    except (TypeError, ValueError):
        days = 365
    days = max(30, min(2555, days))
    note = bucket.get("dedicated_hive_note")
    return {
        "data_retention_days": days,
        "compliance_contact_email": _normalize_email(bucket.get("compliance_contact_email")),
        "soc2_attestation_url": _normalize_https_url(bucket.get("soc2_attestation_url")),
        "monthly_audit_export": bucket.get("monthly_audit_export") is True,
        "dedicated_hive_note": note.strip() if isinstance(note, str) and note.strip() else None,
    }


def build_ha_profile_status() -> dict[str, Any]:
    """Derive HA readiness from deployment settings (read-only)."""

    redis_urls = settings.redis_failover_urls
    if isinstance(redis_urls, str):
        redis_urls = [part.strip() for part in redis_urls.split(",") if part.strip()]
    pg_urls = settings.postgres_replica_urls
    if isinstance(pg_urls, str):
        pg_urls = [part.strip() for part in pg_urls.split(",") if part.strip()]

    redis_ok = bool(redis_urls)
    pg_ok = bool(pg_urls)
    ha_on = bool(settings.ha_mode_enabled)
    score = sum([25 if ha_on else 0, 25 if redis_ok else 0, 25 if pg_ok else 0, 25])
    drill = load_latest_dr_drill_evidence()
    chaos = load_latest_ha_chaos_evidence()
    if drill.get("report_available"):
        score = min(100, score + 10)
    if chaos.get("report_available") and chaos.get("passed") is True:
        score = min(100, score + 5)
    if score >= 100:
        label = "Production HA"
    elif score >= 50:
        label = "Partial HA"
    else:
        label = "Standard single-node"
    return {
        "ha_mode_enabled": ha_on,
        "redis_failover_configured": redis_ok,
        "postgres_replica_configured": pg_ok,
        "backup_drill_script_available": True,
        "profile_label": label,
        "readiness_pct": score,
        "dr_drill": drill,
        "ha_chaos": chaos,
    }


def merge_enterprise_workspace_patch(
    tenant: Tenant,
    *,
    white_label: dict[str, Any] | None = None,
    compliance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply partial white-label / compliance patch and return operator_settings root."""

    root = dict(tenant.operator_settings or {})

    if white_label:
        bucket = _bucket(root, WHITE_LABEL_KEY)
        if "brand_name" in white_label:
            name = white_label["brand_name"]
            bucket["brand_name"] = name.strip() if isinstance(name, str) and name.strip() else None
        if "logo_url" in white_label:
            bucket["logo_url"] = _normalize_https_url(white_label.get("logo_url"))
        if "accent_hex" in white_label and isinstance(white_label["accent_hex"], str):
            if re.fullmatch(r"#[0-9A-Fa-f]{6}", white_label["accent_hex"]):
                bucket["accent_hex"] = white_label["accent_hex"]
        if "hide_platform_branding" in white_label:
            bucket["hide_platform_branding"] = white_label["hide_platform_branding"] is True
        if "custom_domain" in white_label:
            domain = white_label["custom_domain"]
            bucket["custom_domain"] = domain.strip().lower() if isinstance(domain, str) and domain.strip() else None
            bucket["custom_domain_verified"] = False
        root[WHITE_LABEL_KEY] = bucket

    if compliance:
        bucket = _bucket(root, COMPLIANCE_KEY)
        if "data_retention_days" in compliance and compliance["data_retention_days"] is not None:
            bucket["data_retention_days"] = int(compliance["data_retention_days"])
        if "compliance_contact_email" in compliance:
            bucket["compliance_contact_email"] = _normalize_email(compliance.get("compliance_contact_email"))
        if "soc2_attestation_url" in compliance:
            bucket["soc2_attestation_url"] = _normalize_https_url(compliance.get("soc2_attestation_url"))
        if "monthly_audit_export" in compliance:
            bucket["monthly_audit_export"] = compliance["monthly_audit_export"] is True
        if "dedicated_hive_note" in compliance:
            note = compliance["dedicated_hive_note"]
            bucket["dedicated_hive_note"] = note.strip() if isinstance(note, str) and note.strip() else None
        root[COMPLIANCE_KEY] = bucket

    return root


def serialize_enterprise_workspace_view(
    tenant: Tenant,
    *,
    custom_branding_allowed: bool,
) -> dict[str, Any]:
    """Build API view for enterprise workspace settings."""

    return {
        "tenant_id": str(tenant.id),
        "tenant_name": tenant.name,
        "white_label": get_white_label_config(tenant),
        "compliance": get_compliance_config(tenant),
        "ha_profile": build_ha_profile_status(),
        "custom_branding_allowed": custom_branding_allowed,
    }


async def build_compliance_export_bundle(
    session: AsyncSession,
    tenant: Tenant,
    *,
    audit_limit: int = 200,
) -> dict[str, Any]:
    """Assemble compliance export JSON for auditors."""

    rows = list(
        (
            await session.scalars(
                select(TenantAuditLog)
                .where(TenantAuditLog.tenant_id == tenant.id)
                .order_by(TenantAuditLog.created_at.desc())
                .limit(audit_limit),
            )
        ).all(),
    )
    audit_logs = [
        {
            "id": str(row.id),
            "action": row.action,
            "target_type": row.target_type,
            "target_ref": row.target_ref,
            "actor_user_id": str(row.actor_user_id) if row.actor_user_id else None,
            "payload": dict(row.payload or {}),
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]
    count_result = await session.scalar(
        select(func.count(TenantAuditLog.id)).where(TenantAuditLog.tenant_id == tenant.id),
    )
    return {
        "exported_at": datetime.now(tz=UTC).isoformat(),
        "tenant_id": str(tenant.id),
        "tenant_name": tenant.name,
        "white_label": get_white_label_config(tenant),
        "compliance": get_compliance_config(tenant),
        "ha_profile": build_ha_profile_status(),
        "audit_log_count": int(count_result or 0),
        "audit_logs": audit_logs,
    }


def serialize_tenant_branding_brief(tenant: Tenant) -> dict[str, Any] | None:
    """Return active tenant branding for shell chrome when overrides exist."""

    if not enterprise_workspace_enabled():
        return None
    cfg = get_white_label_config(tenant)
    has_override = bool(
        cfg.get("brand_name")
        or cfg.get("logo_url")
        or cfg.get("hide_platform_branding")
        or cfg.get("custom_domain"),
    )
    if not has_override:
        return None
    hide = cfg.get("hide_platform_branding") is True
    return {
        "brand_name": (cfg.get("brand_name") or tenant.name or "Hive").strip(),
        "logo_url": cfg.get("logo_url"),
        "accent_hex": cfg.get("accent_hex") or _DEFAULT_ACCENT,
        "hide_platform_branding": hide,
        "tagline": "HIVE CONTROL" if hide else "HIVE CONTROL · V4",
    }


__all__ = [
    "COMPLIANCE_KEY",
    "WHITE_LABEL_KEY",
    "build_compliance_export_bundle",
    "build_ha_profile_status",
    "enterprise_workspace_enabled",
    "get_compliance_config",
    "get_white_label_config",
    "merge_enterprise_workspace_patch",
    "serialize_tenant_branding_brief",
    "serialize_enterprise_workspace_view",
]
