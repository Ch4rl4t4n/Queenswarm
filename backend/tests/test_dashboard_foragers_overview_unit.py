"""Unit tests for forager overview progress computation."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from app.application.services.dashboard_foragers_overview import (
    _session_sub_agent_progress_pct,
    resolve_forager_progress_meta,
    resolve_forager_run_progress_pct,
)
from app.infrastructure.persistence.models.forager import ForagerORM


def test_session_sub_agent_progress_pct_when_half_done() -> None:
    session = MagicMock()
    session.sub_agents = [
        MagicMock(status="completed"),
        MagicMock(status="running"),
    ]
    assert _session_sub_agent_progress_pct(session) == 50


def test_resolve_forager_run_progress_uses_higher_of_live_or_backfill() -> None:
    forager = MagicMock(spec=ForagerORM)
    forager.id = uuid.uuid4()
    pct = resolve_forager_run_progress_pct(
        forager=forager,
        routine=None,
        status="ok",
        now=datetime.now(tz=UTC),
        running_progress=62,
        cursor_progress=100,
    )
    assert pct == 100
    pct_live_ahead = resolve_forager_run_progress_pct(
        forager=forager,
        routine=None,
        status="ok",
        now=datetime.now(tz=UTC),
        running_progress=80,
        cursor_progress=35,
    )
    assert pct_live_ahead == 80


def test_resolve_forager_progress_meta_live_run_includes_session_href() -> None:
    forager = MagicMock(spec=ForagerORM)
    forager.id = uuid.uuid4()
    forager.name = "X Intel"
    meta = resolve_forager_progress_meta(
        forager=forager,
        routine=None,
        status="ok",
        now=datetime.now(tz=UTC),
        running_progress=62,
        running_session_id="sess-123",
        cursor_progress=None,
    )
    assert meta["pct"] == 62
    assert meta["kind"] == "live_run"
    assert meta["href"] == "/agents?session=sess-123"


def test_live_run_does_not_drop_below_backfill_progress() -> None:
    """Fresh evaluator sessions must not reset bar below channel backfill pct."""

    forager = MagicMock(spec=ForagerORM)
    forager.id = uuid.uuid4()
    forager.name = "YouTube Intel"
    meta = resolve_forager_progress_meta(
        forager=forager,
        routine=None,
        status="ok",
        now=datetime.now(tz=UTC),
        running_progress=5,
        running_session_id="sess-new",
        cursor_progress=35,
    )
    assert meta["pct"] == 35
    assert meta["kind"] == "live_run"
    assert "35%" in meta["detail"]
    assert "5%" in meta["detail"]


def test_resolve_forager_run_progress_ok_without_signals_is_complete() -> None:
    forager = MagicMock(spec=ForagerORM)
    forager.id = uuid.uuid4()
    pct = resolve_forager_run_progress_pct(
        forager=forager,
        routine=None,
        status="ok",
        now=datetime.now(tz=UTC),
        running_progress=None,
        cursor_progress=None,
    )
    assert pct == 100


def test_resolve_forager_run_progress_warn_decays_with_stale_schedule() -> None:
    forager = MagicMock(spec=ForagerORM)
    forager.id = uuid.uuid4()
    routine = MagicMock()
    routine.last_run_at = datetime.now(tz=UTC) - timedelta(hours=6)
    routine.interval_seconds = 3600
    pct = resolve_forager_run_progress_pct(
        forager=forager,
        routine=routine,
        status="warn",
        now=datetime.now(tz=UTC),
        running_progress=None,
        cursor_progress=None,
    )
    assert 15 <= pct < 100
