"""Tenant policy for agent initiative suggestion approvals."""

from __future__ import annotations

from typing import Any

from app.infrastructure.persistence.models.tenant import Tenant


def _initiative_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    bucket = root.get("agent_initiative")
    return dict(bucket) if isinstance(bucket, dict) else {}


def agent_initiative_policy(tenant: Tenant | None) -> dict[str, bool]:
    """Return tenant agent initiative approval policy with safe defaults."""

    bucket = _initiative_bucket(tenant.operator_settings if tenant is not None else None)
    return {
        "auto_approve_enabled": bool(bucket.get("auto_approve_enabled", False)),
        "include_high_risk": bool(bucket.get("include_high_risk", False)),
    }


def tenant_agent_initiative_auto_approve_enabled(tenant: Tenant | None) -> bool:
    """Return True when tenant enables initiative auto-approve."""

    return bool(agent_initiative_policy(tenant).get("auto_approve_enabled"))


def merge_agent_initiative_policy_patch(operator_settings: dict[str, Any] | None, patch: dict[str, Any]) -> dict[str, Any]:
    """Apply partial agent initiative policy patch into operator_settings."""

    root = dict(operator_settings or {})
    bucket = _initiative_bucket(root)
    if "auto_approve_enabled" in patch:
        bucket["auto_approve_enabled"] = bool(patch["auto_approve_enabled"])
    if "include_high_risk" in patch:
        bucket["include_high_risk"] = bool(patch["include_high_risk"])
    root["agent_initiative"] = bucket
    return root


__all__ = [
    "agent_initiative_policy",
    "merge_agent_initiative_policy_patch",
    "tenant_agent_initiative_auto_approve_enabled",
]
