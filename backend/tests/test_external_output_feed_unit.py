"""Unit helpers for generic external orchestrator pull feed."""

from __future__ import annotations

from datetime import UTC, datetime

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.external_output_feed import (
    list_external_results,
    normalize_tag_filter,
    parse_since_iso,
    record_orchestrator_delivery,
)


def test_parse_since_iso_accepts_z_suffix() -> None:
    dt = parse_since_iso("2026-05-12T14:22:01Z")
    assert dt is not None
    assert dt.year == 2026
    assert dt.tzinfo is not None


def test_parse_since_iso_none_for_empty() -> None:
    assert parse_since_iso(None) is None
    assert parse_since_iso("   ") is None


def test_parse_since_iso_naive_assumes_utc() -> None:
    dt = parse_since_iso("2026-01-01T00:00:00")
    assert dt is not None
    assert dt.tzinfo == UTC


def test_parse_since_iso_bad_raises() -> None:
    with pytest.raises(ValueError, match="ISO"):
        parse_since_iso("not-a-date")


def test_normalize_tag_filter_splits() -> None:
    assert normalize_tag_filter("a, b ,") == ["a", "b"]
    assert normalize_tag_filter("") == []


@pytest.mark.asyncio
async def test_record_orchestrator_delivery_merges_default_tags() -> None:
    user_id = uuid.uuid4()
    mission_id = uuid.uuid4()
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()

    row = await record_orchestrator_delivery(
        session,
        dashboard_user_id=user_id,
        mission_id=mission_id,
        session_id=None,
        text_report="  report  ",
        voice_script=None,
        output_metadata={"k": 1},
        simulation_outcome=None,
        tags=["custom"],
    )

    assert row.text_report == "report"
    assert "hive.mission" in row.tags
    assert "custom" in row.tags
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_external_results_returns_scalars() -> None:
    user_id = uuid.uuid4()
    item = object()
    session = AsyncMock()
    session.scalars = AsyncMock(return_value=MagicMock(all=MagicMock(return_value=[item])))

    rows = await list_external_results(
        session,
        dashboard_user_id=user_id,
        since=None,
        limit=10,
        tag_filter=["hive.mission"],
    )

    assert rows == [item]
