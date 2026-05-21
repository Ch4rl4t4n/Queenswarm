from __future__ import annotations

from app.application.services.dashboard_time_saved import (
    aggregate_time_saved_rows,
    estimate_minutes_saved,
)


def test_estimate_minutes_saved_when_template_then_uses_template_minutes() -> None:
    key, kind, minutes = estimate_minutes_saved(
        wizard_template="exec-assistant",
        recipe_name=None,
    )
    assert key == "exec-assistant"
    assert kind == "template"
    assert minutes == 35.0


def test_estimate_minutes_saved_when_recipe_then_recipe_minutes() -> None:
    key, kind, minutes = estimate_minutes_saved(
        wizard_template=None,
        recipe_name="Morning Briefing",
    )
    assert kind == "recipe"
    assert minutes == 30.0
    assert key == "morning-briefing"


def test_aggregate_time_saved_rows_groups_by_source() -> None:
    rows = [
        ("exec-assistant", "template", None, 35.0),
        ("exec-assistant", "template", None, 35.0),
        ("custom", "custom", None, 25.0),
    ]
    breakdown = aggregate_time_saved_rows(rows)
    assert len(breakdown) == 2
    exec_row = next(item for item in breakdown if item["source_key"] == "exec-assistant")
    assert exec_row["task_count"] == 2
    assert exec_row["hours_saved"] == round((70.0 / 60.0), 2)
