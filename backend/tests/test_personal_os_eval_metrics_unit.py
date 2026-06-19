"""Unit tests for ST7 personal OS eval metrics."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.personal_os_eval_metrics_service import compose_personal_os_eval_metrics


@pytest.mark.asyncio
async def test_compose_personal_os_eval_metrics_counts_sessions() -> None:
    tenant_id = uuid.uuid4()
    row_done = MagicMock()
    row_done.status = "completed"
    row_done.context_summary = {"approval_state": "approve", "digest_promoted": True}
    row_done.created_at = datetime.now(tz=UTC)

    row_stop = MagicMock()
    row_stop.status = "stopped"
    row_stop.context_summary = {"discipline_halt_at": datetime.now(tz=UTC).isoformat()}
    row_stop.created_at = datetime.now(tz=UTC)

    async def _scalars(_stmt):  # noqa: ANN001
        result = MagicMock()
        result.all.return_value = [row_done, row_stop]
        return result

    db = AsyncMock()
    db.scalars = _scalars  # type: ignore[method-assign]

    metrics = await compose_personal_os_eval_metrics(db, tenant_id=tenant_id, window_days=7)

    assert metrics.sessions_completed == 1
    assert metrics.sessions_stopped_discipline == 1
    assert metrics.digest_promoted == 1
    assert metrics.approve_rate_pct == 100.0
