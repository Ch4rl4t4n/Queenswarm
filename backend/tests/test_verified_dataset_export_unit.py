"""Unit tests for Track M LOC5 verified dataset export."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.application.services.verified_dataset_export_service import (
    build_verified_dataset_jsonl_bytes,
    collect_verified_dataset_rows,
    compose_verified_dataset_preview,
    compose_verified_dataset_snapshot,
    deliverable_to_alpaca_row,
    export_verified_dataset_jsonl_bytes,
    recipe_to_alpaca_row,
    redact_secrets,
)
from app.core.config import settings
from app.infrastructure.persistence.models.recipe import Recipe
from app.infrastructure.persistence.models.task_final_deliverable import TaskFinalDeliverable


def _deliverable(
    *,
    user_id: uuid.UUID,
    score: float | None = 0.85,
    body: str = "# Report\nVerified KPI narrative.",
) -> TaskFinalDeliverable:
    structured: dict = {"format": "queenswarm.analytics_report.v1", "business_question": "Why did WAU drop?"}
    if score is not None:
        structured["critic_rubric_score"] = score
    return TaskFinalDeliverable(
        id=uuid.uuid4(),
        lineage_id=uuid.uuid4(),
        version=1,
        dashboard_user_id=user_id,
        slug="analytics-report",
        title="Weekly analytics report",
        markdown_body=body,
        structured_json=structured,
        tags=["analytics"],
        created_at=datetime.now(tz=UTC),
    )


def _recipe() -> Recipe:
    return Recipe(
        id=uuid.uuid4(),
        name="Business analytics report",
        description="Codex-style decision report with lineage.",
        workflow_template={
            "steps": [
                {"agent_role": "researcher", "description": "Pull GA4 metrics"},
                {"agent_role": "critic", "description": "Score narrative ≥4/5"},
            ],
        },
        success_count=6,
        fail_count=1,
        avg_pollen_earned=12.5,
        verified_at=datetime.now(tz=UTC),
        is_deprecated=False,
    )


def test_redact_secrets_strips_api_key() -> None:
    raw = "Use api_key=sk-abcdefghijklmnopqrstuvwxyz1234567890 for access."
    out = redact_secrets(raw)
    assert "sk-" not in out
    assert "[REDACTED]" in out


def test_deliverable_to_alpaca_row_shape() -> None:
    row = _deliverable(user_id=uuid.uuid4())
    alpaca = deliverable_to_alpaca_row(row=row, goal="Why did WAU drop?", critic_score=0.85)
    assert alpaca.source_type == "deliverable"
    assert "Why did WAU drop?" in alpaca.input
    assert "Verified KPI" in alpaca.output


def test_recipe_to_alpaca_row_includes_steps() -> None:
    recipe = _recipe()
    alpaca = recipe_to_alpaca_row(recipe)
    assert alpaca.source_type == "recipe"
    assert "researcher" in alpaca.input
    assert "Business analytics report" in alpaca.output


def test_build_verified_dataset_jsonl_bytes_alpaca_only_keys() -> None:
    row = deliverable_to_alpaca_row(
        row=_deliverable(user_id=uuid.uuid4()),
        goal="Goal",
        critic_score=0.9,
    )
    blob = build_verified_dataset_jsonl_bytes([row])
    parsed = json.loads(blob.decode("utf-8").strip())
    assert set(parsed.keys()) == {"instruction", "input", "output"}


@pytest.mark.asyncio
async def test_collect_verified_dataset_rows_filters_low_score(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = uuid.uuid4()
    good = _deliverable(user_id=user_id, score=0.9)
    bad = _deliverable(user_id=user_id, score=0.5, body="Low score body")
    recipe = _recipe()

    session = AsyncMock()
    deliverable_result = MagicMock()
    deliverable_result.all.return_value = [good, bad]
    recipe_result = MagicMock()
    recipe_result.all.return_value = [recipe]

    session.scalars = AsyncMock(side_effect=[deliverable_result, recipe_result])

    rows = await collect_verified_dataset_rows(session, dashboard_user_id=user_id, min_score=0.8)
    assert len(rows) == 2
    assert {r.source_type for r in rows} == {"deliverable", "recipe"}


@pytest.mark.asyncio
async def test_compose_verified_dataset_snapshot_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_llm_enabled", True)
    monkeypatch.setattr(settings, "verified_dataset_export_enabled", True)
    user_id = uuid.uuid4()
    good = _deliverable(user_id=user_id)

    session = AsyncMock()
    deliverable_result = MagicMock()
    deliverable_result.all.return_value = [good]
    session.scalars = AsyncMock(return_value=deliverable_result)
    session.scalar = AsyncMock(return_value=1)

    snap = await compose_verified_dataset_snapshot(session, dashboard_user_id=user_id)
    assert snap.enabled is True
    assert snap.deliverable_candidates == 1
    assert snap.recipe_candidates == 1


@pytest.mark.asyncio
async def test_compose_verified_dataset_preview_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "local_llm_enabled", True)
    monkeypatch.setattr(settings, "verified_dataset_export_enabled", True)
    user_id = uuid.uuid4()

    session = AsyncMock()
    deliverable_result = MagicMock()
    deliverable_result.all.return_value = []
    recipe_result = MagicMock()
    recipe_result.all.return_value = []
    session.scalars = AsyncMock(side_effect=[deliverable_result, recipe_result])

    preview = await compose_verified_dataset_preview(session, dashboard_user_id=user_id)
    assert preview.ok is True
    assert preview.total_rows == 0


@pytest.mark.asyncio
async def test_export_verified_dataset_jsonl_bytes(monkeypatch: pytest.MonkeyPatch) -> None:
    user_id = uuid.uuid4()
    good = _deliverable(user_id=user_id)

    session = AsyncMock()
    deliverable_result = MagicMock()
    deliverable_result.all.return_value = [good]
    recipe_result = MagicMock()
    recipe_result.all.return_value = []
    session.scalars = AsyncMock(side_effect=[deliverable_result, recipe_result])

    blob, count = await export_verified_dataset_jsonl_bytes(session, dashboard_user_id=user_id)
    assert count == 1
    assert b'"instruction"' in blob
