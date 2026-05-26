"""Unit tests for Phase F publish audit trail."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

from app.application.services.execution_studio_activity import append_execution_activity
from app.application.services.publish_audit import build_publish_audit_snapshot


def test_build_publish_audit_snapshot_filters_publish_events() -> None:
    tenant = MagicMock()
    tenant.operator_settings = {}

    append_execution_activity(
        tenant,
        event_type="publish_queue_approved",
        message="Approved launch post",
        payload={
            "deliverable_id": str(uuid.uuid4()),
            "title": "Launch post",
            "channel": "instagram",
        },
    )
    append_execution_activity(
        tenant,
        event_type="tool_execute",
        message="Unrelated",
        payload={},
    )

    snapshot = build_publish_audit_snapshot(tenant, limit=10)
    assert snapshot.enabled is True
    assert snapshot.count == 1
    assert snapshot.entries[0].kind == "queue_approved"
    assert snapshot.entries[0].channel == "instagram"


def test_build_publish_audit_snapshot_includes_tiktok_status() -> None:
    tenant = MagicMock()
    tenant.operator_settings = {}

    append_execution_activity(
        tenant,
        event_type="publish_tiktok_status",
        message="TikTok publish complete",
        payload={
            "deliverable_id": str(uuid.uuid4()),
            "channel": "tiktok",
            "ok": True,
            "tiktok_status": "published",
        },
    )

    snapshot = build_publish_audit_snapshot(tenant, limit=10)
    assert snapshot.count == 1
    assert snapshot.entries[0].kind == "tiktok_publish_status"
