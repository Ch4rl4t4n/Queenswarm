"""Unit tests for DG5 forager export lane."""

from __future__ import annotations

import uuid

import pytest

from app.application.services.forager_export_lane_service import (
    _notion_page_payload,
    _rows_to_csv,
    compose_export_lane_snapshot,
    preview_forager_export,
)
from app.core import config


def test_compose_export_lane_snapshot_enabled() -> None:
    snap = compose_export_lane_snapshot()
    assert snap.enabled is True
    assert "csv" in snap.destinations
    assert snap.default_mode == "simulate"


def test_rows_to_csv_includes_headers() -> None:
    rows = [
        {"knowledge_id": "a", "title": "Job A", "employer": "Acme"},
        {"knowledge_id": "b", "title": "Job B", "employer": "Beta"},
    ]
    columns = ["knowledge_id", "title", "employer"]
    csv_text = _rows_to_csv(rows, columns)
    assert "Job A" in csv_text
    assert "employer" in csv_text.splitlines()[0]


def test_notion_page_payload_builds_title_property() -> None:
    payload = _notion_page_payload(
        "db-123",
        {"title": "Senior Python", "employer": "Acme", "knowledge_id": "kid"},
    )
    assert payload["parent"]["database_id"] == "db-123"
    assert payload["properties"]["Name"]["title"][0]["text"]["content"] == "Senior Python"


@pytest.mark.asyncio
async def test_preview_export_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config.settings, "forager_export_lane_enabled", False)

    class _Session:
        pass

    with pytest.raises(ValueError, match="forager_export_lane_disabled"):
        await preview_forager_export(
            _Session(),  # type: ignore[arg-type]
            tenant_id=uuid.uuid4(),
            forager_id=uuid.uuid4(),
            destination="csv",
        )
