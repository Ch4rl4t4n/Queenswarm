"""Unit tests for TR1 injection guard coverage dashboard."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.application.services.injection_guard_coverage_service import (
    compose_injection_guard_coverage,
    derive_injection_guard_coverage,
)
from app.application.services.injection_guard_telemetry import (
    TELEMETRY_BUCKET,
    injection_guard_store,
    merge_telemetry_patch,
)
from app.application.services.prompt_injection_guard import InjectionCheckpoint


def test_derive_injection_guard_coverage_empty_bucket_is_healthy() -> None:
    coverage = derive_injection_guard_coverage({})
    assert coverage.enabled is True
    assert coverage.status == "healthy"
    assert coverage.total_scans == 0
    assert len(coverage.checkpoints) == 3
    assert len(coverage.tools) == 7
    assert "No guard scans recorded yet" in coverage.operator_hint


def test_derive_injection_guard_coverage_warn_on_recent_blocks() -> None:
    bucket = {
        "checkpoints": {
            InjectionCheckpoint.EXTERNAL_TOOL.value: {"scans": 5, "blocked": 1},
        },
        "tools": {"web_search": {"scans": 5, "blocked": 1}},
        "recent_hits": [
            {
                "at": "2026-06-05T12:00:00+00:00",
                "checkpoint": InjectionCheckpoint.EXTERNAL_TOOL.value,
                "tool_name": "web_search",
                "matched_pattern": r"ignore\s+previous",
            },
        ],
    }
    coverage = derive_injection_guard_coverage(bucket)
    assert coverage.status == "warn"
    assert coverage.total_scans == 5
    assert coverage.total_blocked == 1
    assert coverage.recent_hits[0].tool_name == "web_search"


def test_derive_injection_guard_coverage_critical_on_many_blocks() -> None:
    bucket = {
        "checkpoints": {
            InjectionCheckpoint.OPERATOR_INPUT.value: {"scans": 20, "blocked": 10},
        },
        "recent_hits": [{}, {}, {}],
    }
    coverage = derive_injection_guard_coverage(bucket)
    assert coverage.status == "critical"
    assert "Multiple injection markers blocked" in coverage.operator_hint


def test_merge_telemetry_patch_aggregates_checkpoints_and_tools() -> None:
    base = {TELEMETRY_BUCKET: {"checkpoints": {}, "tools": {}, "recent_hits": []}}
    merged = merge_telemetry_patch(
        base,
        {
            "checkpoints": {
                InjectionCheckpoint.EXTERNAL_TOOL.value: {"scans": 2, "blocked": 1},
            },
            "tools": {"scrape_url": {"scans": 2, "blocked": 1}},
            "recent_hits": [{"checkpoint": InjectionCheckpoint.EXTERNAL_TOOL.value}],
        },
    )
    bucket = merged[TELEMETRY_BUCKET]
    row = bucket["checkpoints"][InjectionCheckpoint.EXTERNAL_TOOL.value]
    assert row["scans"] == 2
    assert row["blocked"] == 1
    assert bucket["tools"]["scrape_url"]["blocked"] == 1
    assert len(bucket["recent_hits"]) == 1


def test_injection_guard_store_drain_patch_per_tenant() -> None:
    tenant_id = uuid.uuid4()
    injection_guard_store.record_scan(
        tenant_id=tenant_id,
        checkpoint=InjectionCheckpoint.EXTERNAL_TOOL,
        blocked=True,
        tool_name="web_search",
        matched_pattern="test-pattern",
    )
    patch = injection_guard_store.drain_patch(tenant_id)
    assert patch is not None
    assert patch["checkpoints"][InjectionCheckpoint.EXTERNAL_TOOL.value]["blocked"] == 1
    assert injection_guard_store.drain_patch(tenant_id) is None


@pytest.mark.asyncio
async def test_compose_injection_guard_coverage_disabled() -> None:
    session = AsyncMock()
    with patch(
        "app.application.services.injection_guard_coverage_service.settings",
    ) as mock_settings:
        mock_settings.injection_guard_coverage_enabled = False
        out = await compose_injection_guard_coverage(session, tenant_id=uuid.uuid4())
    assert out.enabled is False


@pytest.mark.asyncio
async def test_compose_injection_guard_coverage_flushes_pending_telemetry() -> None:
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    tenant = MagicMock()
    tenant.operator_settings = {}
    session.get = AsyncMock(return_value=tenant)

    injection_guard_store.record_scan(
        tenant_id=tenant_id,
        checkpoint=InjectionCheckpoint.AGENT_OUTPUT,
        blocked=False,
    )

    with patch(
        "app.application.services.injection_guard_coverage_service.settings",
    ) as mock_settings:
        mock_settings.injection_guard_coverage_enabled = True
        out = await compose_injection_guard_coverage(session, tenant_id=tenant_id)

    assert out.enabled is True
    assert out.total_scans >= 1
    session.flush.assert_awaited_once()
