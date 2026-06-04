"""Shared factory policy caps — Skill + Content Pack factories."""

from __future__ import annotations

FACTORY_MAX_BUILDS_PER_WEEK_CAP = 50
FACTORY_MAX_BUILDS_PER_WEEK_DEFAULT = 10


def clamp_max_builds_per_week(raw: object) -> int:
    """Clamp operator weekly build cap to supported range."""

    try:
        value = int(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        value = FACTORY_MAX_BUILDS_PER_WEEK_DEFAULT
    return max(1, min(value, FACTORY_MAX_BUILDS_PER_WEEK_CAP))


__all__ = [
    "FACTORY_MAX_BUILDS_PER_WEEK_CAP",
    "FACTORY_MAX_BUILDS_PER_WEEK_DEFAULT",
    "clamp_max_builds_per_week",
]
