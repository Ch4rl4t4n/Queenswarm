"""Tenant policy for publish queue operator approvals."""

from __future__ import annotations

from typing import Any

from app.infrastructure.persistence.models.tenant import Tenant


def _publish_queue_bucket(operator_settings: dict[str, Any] | None) -> dict[str, Any]:
    root = dict(operator_settings or {})
    bucket = root.get("publish_queue")
    return dict(bucket) if isinstance(bucket, dict) else {}


def publish_queue_policy(tenant: Tenant | None) -> dict[str, bool]:
    """Return tenant publish queue approval policy with safe defaults."""

    bucket = _publish_queue_bucket(tenant.operator_settings if tenant is not None else None)
    return {
        "auto_approve_enabled": bool(bucket.get("auto_approve_enabled", False)),
    }


def tenant_publish_queue_auto_approve_enabled(tenant: Tenant | None) -> bool:
    """Return True when tenant enables publish queue auto-approve."""

    return bool(publish_queue_policy(tenant).get("auto_approve_enabled"))


def merge_publish_queue_policy_patch(
    operator_settings: dict[str, Any] | None,
    patch: dict[str, Any],
) -> dict[str, Any]:
    """Apply partial publish queue policy patch into operator_settings."""

    root = dict(operator_settings or {})
    bucket = _publish_queue_bucket(root)
    if "auto_approve_enabled" in patch:
        bucket["auto_approve_enabled"] = bool(patch["auto_approve_enabled"])
    root["publish_queue"] = bucket
    return root


__all__ = [
    "merge_publish_queue_policy_patch",
    "publish_queue_policy",
    "tenant_publish_queue_auto_approve_enabled",
]
