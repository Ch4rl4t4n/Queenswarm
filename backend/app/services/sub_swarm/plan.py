"""Execution batching aligned with breaker ``parallelizable_groups`` semantics."""

from __future__ import annotations

from typing import Any

from app.models.workflow import WorkflowStep


def _normalize_parallel_groups(groups: Any) -> list[set[int]]:
    """Lift JSON groups into sanitized sets of integer step orders."""

    if not isinstance(groups, list):
        return []
    out: list[set[int]] = []
    for item in groups:
        if not isinstance(item, list):
            continue
        chunk: set[int] = set()
        for raw in item:
            try:
                chunk.add(int(raw))
            except (TypeError, ValueError):
                continue
        if chunk:
            out.append(chunk)
    return out


def plan_execution_batches(
    *,
    ordered_steps: list[WorkflowStep],
    parallel_groups: Any,
) -> list[list[WorkflowStep]]:
    """Partition ordered steps into batches honoring parallel equivalence classes.

    Dependencies follow numeric ``step_order``: a step waits until every lower-numbered
    workflow row completes. Parallel groups bundle only steps whose intermediate orders
    are either absent from the workflow or already cleared.

    Each batch drains fully before scheduling the next batch. Postgres ORM mutations use
    one request session per run, so steps inside a logical parallel batch execute
    sequentially (same transaction semantics) while still surfacing telemetry batching.

    Args:
        ordered_steps: Breaker rows sorted by ``step_order`` ascending.
        parallel_groups: JSON array of sibling step-order lists from ``Workflow.parallelizable_groups``.

    Returns:
        Non-empty batches covering every step exactly once.

    Raises:
        ValueError: Duplicate step orders, contradictory parallel constraints, or empty input.
    """

    if not ordered_steps:
        raise ValueError("workflow has no persisted steps.")

    by_order: dict[int, WorkflowStep] = {}
    for step in ordered_steps:
        key = int(step.step_order)
        if key in by_order:
            msg = f"duplicate workflow step_order {key} encountered during planning."
            raise ValueError(msg)
        by_order[key] = step

    grouped_sets = _normalize_parallel_groups(parallel_groups)

    batches: list[list[WorkflowStep]] = []
    consumed_orders: set[int] = set()

    while len(consumed_orders) < len(by_order):
        next_order = min(o for o in by_order if o not in consumed_orders)
        matched: set[int] | None = None
        for candidate in grouped_sets:
            if next_order in candidate:
                matched = candidate
                break
        if matched is None:
            batch_orders_int = [next_order]
        else:
            pooled = sorted(
                o for o in matched.intersection(by_order.keys()) if o not in consumed_orders
            )
            if not pooled or pooled[0] != next_order:
                msg = (
                    "parallel lane misaligned — expected next runnable order "
                    f"{next_order} to lead batch {sorted(matched)}, got pooled={pooled}."
                )
                raise ValueError(msg)

            def _interval_respects_prereqs(batch_ints: set[int]) -> bool:
                """Return False when a workflow row sits strictly inside the batch span but is excluded."""

                span_lo, span_hi = min(batch_ints), max(batch_ints)
                for mid in by_order:
                    if span_lo < mid < span_hi and mid not in consumed_orders and mid not in batch_ints:
                        return False
                return True

            batch_ints = {next_order}
            for cand in pooled[1:]:
                trial = set(batch_ints)
                trial.add(cand)
                if _interval_respects_prereqs(trial):
                    batch_ints = trial
            batch_orders_int = sorted(batch_ints)

        consumed_orders.update(batch_orders_int)
        batches.append([by_order[o] for o in batch_orders_int])

    return batches


__all__ = ["plan_execution_batches"]
