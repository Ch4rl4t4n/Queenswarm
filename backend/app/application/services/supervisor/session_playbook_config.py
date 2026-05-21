"""Per-tenant supervisor session playbook settings on Tenant.operator_settings."""

from __future__ import annotations

from typing import Any

from app.core.config import settings
from app.infrastructure.persistence.models.tenant import Tenant

PLAYBOOK_CONFIG_KEY = "supervisor_session_playbook"


def _playbook_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    """Return nested supervisor session playbook config bucket."""

    root = dict(operator_settings or {})
    bucket = root.get(PLAYBOOK_CONFIG_KEY)
    return dict(bucket) if isinstance(bucket, dict) else {}


def get_tenant_session_playbook_config(tenant: Tenant) -> dict[str, Any]:
    """Return stored tenant playbook automation config."""

    bucket = _playbook_bucket(tenant.operator_settings)
    return {
        "auto_save_on_approve": bucket.get("auto_save_on_approve"),
        "mark_verified_on_auto_save": bucket.get("mark_verified_on_auto_save"),
    }


def auto_save_playbook_on_approve_enabled(tenant: Tenant) -> bool:
    """Return True when approved sessions should auto-save to Recipe Library."""

    stored = get_tenant_session_playbook_config(tenant).get("auto_save_on_approve")
    return stored is True


def auto_save_mark_verified_on_approve(tenant: Tenant) -> bool:
    """Return whether auto-saved playbooks receive verified stamp."""

    stored = get_tenant_session_playbook_config(tenant).get("mark_verified_on_auto_save")
    if stored is False:
        return False
    return True


def merge_tenant_session_playbook_patch(
    tenant: Tenant,
    *,
    auto_save_on_approve: bool | None = None,
    mark_verified_on_auto_save: bool | None = None,
) -> dict[str, Any]:
    """Apply partial playbook config patch and return updated operator_settings root."""

    root = dict(tenant.operator_settings or {})
    bucket = _playbook_bucket(root)
    if auto_save_on_approve is not None:
        bucket["auto_save_on_approve"] = auto_save_on_approve
    if mark_verified_on_auto_save is not None:
        bucket["mark_verified_on_auto_save"] = mark_verified_on_auto_save
    root[PLAYBOOK_CONFIG_KEY] = bucket
    return root


def serialize_session_playbook_config_view(tenant: Tenant) -> dict[str, Any]:
    """Build API view for tenant playbook automation settings."""

    stored = get_tenant_session_playbook_config(tenant)
    return {
        "auto_save_on_approve": auto_save_playbook_on_approve_enabled(tenant),
        "auto_save_on_approve_override": stored.get("auto_save_on_approve"),
        "mark_verified_on_auto_save": auto_save_mark_verified_on_approve(tenant),
        "mark_verified_on_auto_save_override": stored.get("mark_verified_on_auto_save"),
        "recipes_enabled": settings.recipes_enabled,
    }


__all__ = [
    "PLAYBOOK_CONFIG_KEY",
    "auto_save_mark_verified_on_approve",
    "auto_save_playbook_on_approve_enabled",
    "get_tenant_session_playbook_config",
    "merge_tenant_session_playbook_patch",
    "serialize_session_playbook_config_view",
]
