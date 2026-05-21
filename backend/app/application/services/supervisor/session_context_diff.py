"""Helpers for comparing supervisor session context_summary snapshots."""

from __future__ import annotations

from typing import Any

_MAX_NESTED_DEPTH = 4


def _diff_lists(before: list[Any], after: list[Any]) -> dict[str, Any]:
    """Summarize list mutations for journal-style context fields."""

    if before == after:
        return {}
    if len(after) > len(before) and before == after[: len(before)]:
        return {
            "added_items": after[len(before) :],
            "before_len": len(before),
            "after_len": len(after),
        }
    if len(before) > len(after) and after == before[: len(after)]:
        return {
            "removed_items": before[len(after) :],
            "before_len": len(before),
            "after_len": len(after),
        }

    item_changes: list[dict[str, Any]] = []
    for index, (left, right) in enumerate(zip(before, after, strict=False)):
        if left != right:
            if isinstance(left, dict) and isinstance(right, dict):
                nested = compute_context_summary_diff(left, right, depth=1)
                item_changes.append({"index": index, **nested} if nested else {"index": index, "before": left, "after": right})
            else:
                item_changes.append({"index": index, "before": left, "after": right})
    if item_changes:
        return {"item_changes": item_changes, "before_len": len(before), "after_len": len(after)}
    return {"before": before, "after": after, "before_len": len(before), "after_len": len(after)}


def compute_context_summary_diff(
    before: dict[str, Any] | None,
    after: dict[str, Any] | None,
    *,
    depth: int = 0,
) -> dict[str, Any]:
    """Return added, removed, changed, and nested context_summary diffs."""

    if depth >= _MAX_NESTED_DEPTH:
        if before == after:
            return {}
        return {"before": before, "after": after}

    left = dict(before or {})
    right = dict(after or {})
    added = {key: right[key] for key in right if key not in left}
    removed = {key: left[key] for key in left if key not in right}
    changed: dict[str, Any] = {}
    nested: dict[str, Any] = {}

    for key in left:
        if key not in right:
            continue
        left_value = left[key]
        right_value = right[key]
        if left_value == right_value:
            continue
        if isinstance(left_value, dict) and isinstance(right_value, dict):
            sub = compute_context_summary_diff(left_value, right_value, depth=depth + 1)
            if sub:
                nested[key] = sub
            continue
        if isinstance(left_value, list) and isinstance(right_value, list):
            sub = _diff_lists(left_value, right_value)
            if sub:
                nested[key] = sub
            continue
        changed[key] = {"before": left_value, "after": right_value}

    result: dict[str, Any] = {}
    if added:
        result["added"] = added
    if removed:
        result["removed"] = removed
    if changed:
        result["changed"] = changed
    if nested:
        result["nested"] = nested
    return result


__all__ = ["compute_context_summary_diff"]
