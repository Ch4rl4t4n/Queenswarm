"""Gate operator-visible workflow traces behind simulator verification signals."""

from __future__ import annotations

import copy
from typing import Any

_REDACTION: dict[str, Any] = {
    "hive_visibility": "redacted",
    "message": (
        "Raw step payloads stay in-hive until a simulator emits a passing, "
        "threshold-backed verification signal."
    ),
}


def _normalized_confidence(blob: dict[str, Any]) -> float | None:
    """Map heterogeneous confidence hints into ``0..1``."""

    for key in ("confidence", "confidence_pct", "simulation_confidence", "verification_score"):
        raw = blob.get(key)
        if isinstance(raw, (int, float)):
            val = float(raw)
            # Treat values > 1 as percent scales (e.g. 85 meaning 85%).
            if val > 1.0:
                val = val / 100.0
            return val
    return None


def assess_internal_step_outputs(
    internal_summaries: list[dict[str, Any]],
    *,
    threshold: float,
) -> tuple[bool, list[str]]:
    """Return whether the swarm run cleared the hive simulation bar.

    A run verifies when some **completed simulator** step reports
    ``verification_passed`` and confidence ≥ ``threshold``.
    """

    notes: list[str] = []
    saw_simulator = False
    for summary in internal_summaries:
        if summary.get("status") != "completed":
            continue
        if summary.get("agent_role") != "simulator":
            continue
        saw_simulator = True
        result = summary.get("result")
        if not isinstance(result, dict):
            notes.append(
                f"simulator_step_order={summary.get('order')} missing structured result envelope.",
            )
            continue
        if result.get("verification_passed") is not True:
            notes.append(f"simulator_step_order={summary.get('order')} did not acknowledge verification.")
            continue
        conf = _normalized_confidence(result)
        if conf is None:
            notes.append(f"simulator_step_order={summary.get('order')} lacks numeric confidence hints.")
            continue
        if conf + 1e-9 < threshold:
            notes.append(
                f"simulator_step_order={summary.get('order')} confidence={conf:.4f} < threshold={threshold:.4f}.",
            )
            continue
        notes.append(f"verification_ok simulator_order={summary.get('order')} confidence={conf:.4f}.")
        return True, notes

    if not saw_simulator:
        notes.append("workflow_completed_without_verifying_simulator_step.")
    elif not notes:
        notes.append("simulator_present_but_signal_incomplete.")

    return False, notes


def max_simulator_confidence_fraction(internal_summaries: list[dict[str, Any]]) -> float | None:
    """Return strongest numeric confidence hinted by completed simulator bees (``0..1``)."""

    best: float | None = None
    for summary in internal_summaries:
        if summary.get("status") != "completed":
            continue
        if summary.get("agent_role") != "simulator":
            continue
        result = summary.get("result")
        if not isinstance(result, dict):
            continue
        conf = _normalized_confidence(result)
        if conf is None:
            continue
        if best is None or conf > best:
            best = conf
    return best


def build_operator_step_summaries(
    internal_summaries: list[dict[str, Any]],
    *,
    verified: bool,
    expose_raw: bool,
) -> list[dict[str, Any]]:
    """Project internal traces into dashboards the doctrine allows."""

    projected: list[dict[str, Any]] = []
    for row in internal_summaries:
        if expose_raw:
            projected.append(copy.deepcopy(row))
            continue
        if verified:
            projected.append(copy.deepcopy(row))
            continue
        sanitized = {k: v for k, v in row.items() if k != "result"}
        sanitized["result"] = copy.deepcopy(_REDACTION)
        projected.append(sanitized)
    return projected


def maybe_attach_internal_echo(
    internal_summaries: list[dict[str, Any]],
    *,
    expose_raw: bool,
) -> list[dict[str, Any]]:
    """Return internal summaries for privileged operators when enabled."""

    if not expose_raw:
        return []
    return copy.deepcopy(internal_summaries)


__all__ = [
    "assess_internal_step_outputs",
    "build_operator_step_summaries",
    "max_simulator_confidence_fraction",
    "maybe_attach_internal_echo",
]
