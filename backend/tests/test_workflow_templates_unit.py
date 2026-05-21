"""Unit coverage for bundled workflow seed templates."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.workflows.templates import SEED_WORKFLOWS, load_seed_workflows


def test_seed_workflows_have_guardrails_and_steps() -> None:
    for key, blob in SEED_WORKFLOWS.items():
        assert blob["name"] == key
        steps = blob["steps"]
        assert len(steps) >= 3
        for step in steps:
            assert step["guardrails"]["risks"]
            assert step["evaluation_criteria"]["must_satisfy"]


@pytest.mark.asyncio
async def test_load_seed_workflows_inserts_when_missing() -> None:
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=0)
    session.add = MagicMock()
    session.flush = AsyncMock()

    inserted = await load_seed_workflows(session)

    assert inserted == len(SEED_WORKFLOWS)
    assert session.add.call_count == len(SEED_WORKFLOWS)
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_load_seed_workflows_skips_existing() -> None:
    session = AsyncMock()
    session.scalar = AsyncMock(return_value=1)
    session.add = MagicMock()
    session.flush = AsyncMock()

    inserted = await load_seed_workflows(session)

    assert inserted == 0
    session.add.assert_not_called()
    session.flush.assert_not_awaited()
