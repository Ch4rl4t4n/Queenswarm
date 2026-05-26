"""Unit tests for Execution Studio activity ring buffer."""

from __future__ import annotations

from types import SimpleNamespace

from app.application.services.execution_studio_activity import (
    append_execution_activity,
    clear_execution_activity,
    list_execution_activity,
)


def test_clear_execution_activity_empties_bucket() -> None:
    """Clear removes all rows and returns prior count."""

    tenant = SimpleNamespace(
        id="tenant-1",
        operator_settings={
            "execution_studio": {
                "recent_activity": [
                    {
                        "event_type": "tool_execute",
                        "message": "Simulated: notion/search",
                        "payload": {},
                        "at": "2026-05-21T12:00:00+00:00",
                    },
                    {
                        "event_type": "proposal_created",
                        "message": "Codebase proposal queued",
                        "payload": {"proposal_id": "abc"},
                        "at": "2026-05-21T12:05:00+00:00",
                    },
                ],
            },
        },
    )

    cleared = clear_execution_activity(tenant)  # type: ignore[arg-type]

    assert cleared == 2
    assert list_execution_activity(tenant) == []  # type: ignore[arg-type]
    assert tenant.operator_settings["execution_studio"]["recent_activity"] == []


def test_append_after_clear_starts_fresh() -> None:
    """New events append after clear without resurrecting old rows."""

    tenant = SimpleNamespace(id="tenant-2", operator_settings={"execution_studio": {"recent_activity": []}})
    clear_execution_activity(tenant)  # type: ignore[arg-type]
    append_execution_activity(
        tenant,  # type: ignore[arg-type]
        event_type="approval_cleared",
        message="Operator confirmed live browser",
    )

    rows = list_execution_activity(tenant)  # type: ignore[arg-type]
    assert len(rows) == 1
    assert rows[0]["event_type"] == "approval_cleared"
