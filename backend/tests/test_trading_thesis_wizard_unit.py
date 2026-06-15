"""Unit tests for NP5 Trading thesis wizard."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.application.services.trading_thesis_wizard import (
    _validate_answers,
    compose_trading_thesis_brief_markdown,
    compose_trading_thesis_wizard_snapshot,
    submit_trading_thesis_wizard,
    TradingThesisSubmitIn,
)


def _full_answers() -> dict[str, str]:
    return {
        "market": "Polymarket — BTC above $120k by Dec 2026.",
        "implied_probability": "Market mid 42% from order book snapshot today.",
        "your_edge": "On-chain flows suggest 48% — model from funding rates.",
        "position_size_cap": "Max $500 or 2% portfolio — whichever is lower.",
        "kill_criteria": "Exit if implied crosses 55% or resolution within 7 days without catalyst.",
        "paper_preflight": "Paper session #abc123 — 3 simulated entries, no live stake yet.",
    }


def test_compose_trading_thesis_wizard_snapshot_has_six_questions() -> None:
    snap = compose_trading_thesis_wizard_snapshot()
    assert snap.enabled is True
    assert len(snap.questions) == 6
    assert snap.live_gate_skill == "real-money-risk-gate"


def test_compose_trading_thesis_brief_markdown_includes_gates() -> None:
    answers = _full_answers()
    title, md = compose_trading_thesis_brief_markdown(answers, title="BTC thesis")
    assert title == "BTC thesis"
    assert "## Market / event" in md
    assert "## Risk preflight gates" in md
    assert "real-money-risk-gate" in md


def test_validate_answers_rejects_short_entries() -> None:
    with pytest.raises(ValueError, match="too short"):
        _validate_answers({"market": "short"}, min_chars=10)


@pytest.mark.asyncio
async def test_submit_trading_thesis_wizard_creates_task_and_deliverable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "trading_thesis_wizard_enabled", True)
    monkeypatch.setattr(config.settings, "supervisor_durable_mode_enabled", False)

    task_id = uuid.uuid4()
    deliverable_id = uuid.uuid4()
    fake_snap = SimpleNamespace(id=task_id, title="Brief")

    session = AsyncMock()
    session.flush = AsyncMock()

    with (
        patch(
            "app.application.services.trading_thesis_wizard.create_mission_triage_task",
            AsyncMock(return_value=SimpleNamespace(task=fake_snap)),
        ),
        patch(
            "app.application.services.trading_thesis_wizard.OutputEngine.create_final_deliverable",
            AsyncMock(return_value=SimpleNamespace(id=deliverable_id)),
        ),
    ):
        result = await submit_trading_thesis_wizard(
            session,
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            created_by_subject="op@test.com",
            body=TradingThesisSubmitIn(answers=_full_answers(), dispatch_session=False),
        )

    assert result.ok is True
    assert result.task_id == str(task_id)
    assert result.deliverable_id == str(deliverable_id)
    assert result.supervisor_session_id is None


@pytest.mark.asyncio
async def test_submit_trading_thesis_wizard_dispatches_session_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core import config

    monkeypatch.setattr(config.settings, "trading_thesis_wizard_enabled", True)
    monkeypatch.setattr(config.settings, "supervisor_durable_mode_enabled", True)

    task_id = uuid.uuid4()
    session_id = uuid.uuid4()
    fake_snap = SimpleNamespace(id=task_id, title="Brief")

    session = AsyncMock()
    session.flush = AsyncMock()

    with (
        patch(
            "app.application.services.trading_thesis_wizard.create_mission_triage_task",
            AsyncMock(return_value=SimpleNamespace(task=fake_snap)),
        ),
        patch(
            "app.application.services.trading_thesis_wizard.OutputEngine.create_final_deliverable",
            AsyncMock(return_value=SimpleNamespace(id=uuid.uuid4())),
        ),
        patch(
            "app.application.services.trading_thesis_wizard.create_supervisor_session",
            AsyncMock(return_value=SimpleNamespace(id=session_id)),
        ),
    ):
        result = await submit_trading_thesis_wizard(
            session,
            tenant_id=uuid.uuid4(),
            dashboard_user_id=uuid.uuid4(),
            created_by_subject="op@test.com",
            body=TradingThesisSubmitIn(answers=_full_answers(), dispatch_session=True),
        )

    assert result.supervisor_session_id == str(session_id)
    assert result.session_href is not None
