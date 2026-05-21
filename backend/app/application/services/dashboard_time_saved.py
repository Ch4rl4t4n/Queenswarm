"""Time-saved ROI estimates from verified tasks and wizard templates."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.enums import TaskStatus
from app.infrastructure.persistence.models.recipe import Recipe
from app.infrastructure.persistence.models.swarm import SubSwarm
from app.infrastructure.persistence.models.task import Task

SourceKind = Literal["template", "recipe", "custom"]

DEFAULT_VERIFIED_TASK_MINUTES = 25.0
RECIPE_VERIFIED_TASK_MINUTES = 30.0

_TEMPLATE_MINUTES_SAVED: dict[str, tuple[str, float]] = {
    "exec-assistant": ("Exec Assistant", 35.0),
    "lead-waterfall": ("Lead Waterfall", 45.0),
    "content-flywheel": ("Content Flywheel", 40.0),
}


def _wizard_template_id(local_memory: dict[str, Any] | None) -> str | None:
    """Extract swarm wizard template id from colony local memory."""

    if not isinstance(local_memory, dict):
        return None
    raw = local_memory.get("wizard_template")
    if raw is None:
        return None
    text = str(raw).strip()
    return text or None


def estimate_minutes_saved(
    *,
    wizard_template: str | None,
    recipe_name: str | None,
) -> tuple[str, SourceKind, float]:
    """Return breakdown key, source kind, and minutes saved for one verified task.

    Args:
        wizard_template: Optional wizard template id from swarm local memory.
        recipe_name: Optional linked recipe catalog name.

    Returns:
        Tuple of ``(source_key, source_kind, minutes_saved)``.
    """

    if wizard_template and wizard_template in _TEMPLATE_MINUTES_SAVED:
        label, minutes = _TEMPLATE_MINUTES_SAVED[wizard_template]
        return wizard_template, "template", minutes
    if recipe_name:
        slug = recipe_name.strip().lower().replace(" ", "-")[:80] or "recipe"
        return slug, "recipe", RECIPE_VERIFIED_TASK_MINUTES
    return "custom", "custom", DEFAULT_VERIFIED_TASK_MINUTES


def _source_label(source_key: str, source_kind: SourceKind, recipe_name: str | None) -> str:
    """Human-readable label for breakdown rows."""

    if source_kind == "template" and source_key in _TEMPLATE_MINUTES_SAVED:
        return _TEMPLATE_MINUTES_SAVED[source_key][0]
    if source_kind == "recipe" and recipe_name:
        return recipe_name
    if source_kind == "recipe":
        return source_key.replace("-", " ").title()
    return "Custom verified workflows"


def aggregate_time_saved_rows(
    rows: list[tuple[str, SourceKind, str | None, float]],
) -> list[dict[str, Any]]:
    """Merge per-task attribution rows into sorted breakdown entries."""

    buckets: dict[tuple[str, SourceKind], dict[str, Any]] = {}
    for source_key, source_kind, recipe_name, minutes in rows:
        bucket_key = (source_key, source_kind)
        if bucket_key not in buckets:
            buckets[bucket_key] = {
                "source_key": source_key,
                "source_kind": source_kind,
                "source_label": _source_label(source_key, source_kind, recipe_name),
                "task_count": 0,
                "minutes_per_task": minutes,
                "hours_saved": 0.0,
            }
        entry = buckets[bucket_key]
        entry["task_count"] = int(entry["task_count"]) + 1

    breakdown = sorted(buckets.values(), key=lambda row: int(row["task_count"]), reverse=True)
    for entry in breakdown:
        entry["hours_saved"] = round(int(entry["task_count"]) * float(entry["minutes_per_task"]) / 60.0, 2)
    breakdown.sort(key=lambda row: float(row["hours_saved"]), reverse=True)
    return breakdown


async def build_time_saved_payload(
    db: AsyncSession,
    *,
    window_days: int = 30,
) -> dict[str, Any]:
    """Aggregate verified-task ROI for dashboard and costs analytics."""

    now = datetime.now(tz=UTC)
    days = max(1, min(window_days, 90))
    window_start = now - timedelta(days=days)

    result = await db.execute(
        select(Task, SubSwarm, Recipe)
        .outerjoin(SubSwarm, Task.swarm_id == SubSwarm.id)
        .outerjoin(Recipe, Task.recipe_used_id == Recipe.id)
        .where(
            Task.status == TaskStatus.COMPLETED,
            Task.completed_at.is_not(None),
            Task.completed_at >= window_start,
            Task.pollen_awarded > 0.0,
        ),
    )

    attributions: list[tuple[str, SourceKind, str | None, float]] = []
    for task, swarm, recipe in result.all():
        wizard_template = _wizard_template_id(swarm.local_memory if swarm is not None else None)
        recipe_name = recipe.name if recipe is not None else None
        source_key, source_kind, minutes = estimate_minutes_saved(
            wizard_template=wizard_template,
            recipe_name=recipe_name,
        )
        attributions.append((source_key, source_kind, recipe_name, minutes))

    breakdown = aggregate_time_saved_rows(attributions)
    hours_total = round(sum(float(row["hours_saved"]) for row in breakdown), 2)
    verified_count = len(attributions)
    projected_monthly = round(hours_total * (30.0 / float(days)), 2) if verified_count else 0.0

    return {
        "generated_at": now.isoformat(),
        "window_days": days,
        "verified_task_count": verified_count,
        "hours_saved_total": hours_total,
        "hours_saved_projected_monthly": projected_monthly,
        "minutes_per_task_default": DEFAULT_VERIFIED_TASK_MINUTES,
        "breakdown": breakdown,
        "disclaimer": (
            "Estimates from verified tasks (pollen awarded) and template ROI defaults — not payroll data."
        ),
    }


__all__ = [
    "aggregate_time_saved_rows",
    "build_time_saved_payload",
    "estimate_minutes_saved",
]
